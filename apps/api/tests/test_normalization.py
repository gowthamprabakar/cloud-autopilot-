"""
Tests for NormalizationService — uses SQLite in-memory DB.

Validates:
- Fingerprint uniqueness and determinism
- Source finding → canonical finding linking
- Idempotency (re-running normalization doesn't duplicate canonical findings)
- Risk score computation by severity + resource type
- Compliance framework extraction from ASFF Types[]
"""

import uuid

import pytest

from app.models.aws_account import AwsAccount
from app.models.enums import (
    AwsAccountStatus,
    FindingSeverity,
    FindingSource,
    FindingStatus,
)
from app.models.source_finding import SourceFinding
from app.models.workspace import Workspace
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.source_finding_repository import SourceFindingRepository
from app.services.normalization_service import (
    NormalizationService,
    _compute_fingerprint,
    _compute_risk_score,
    _map_compliance_frameworks,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _seed_workspace_and_account(db) -> tuple[uuid.UUID, uuid.UUID]:
    """Insert minimal Workspace + AwsAccount rows, return (workspace_id, aws_account_id)."""
    from app.models.tenant import Tenant
    from app.models.enums import TenantPlan, TenantStatus, WorkspaceStatus

    tenant = Tenant(name="Test Tenant", slug="test-tenant", plan=TenantPlan.BASELINE, status=TenantStatus.ACTIVE)
    db.add(tenant)
    await db.flush()

    ws = Workspace(tenant_id=tenant.id, name="Default", slug="default", status=WorkspaceStatus.ACTIVE)
    db.add(ws)
    await db.flush()

    acct = AwsAccount(
        workspace_id=ws.id,
        account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()

    return ws.id, acct.id


async def _seed_source_finding(
    db,
    aws_account_id: uuid.UUID,
    workspace_id: uuid.UUID,
    native_id: str = "finding-001",
    severity: FindingSeverity = FindingSeverity.HIGH,
    resource_arn: str = "arn:aws:s3:::my-bucket",
    resource_type: str = "AwsS3Bucket",
    compliance_types: list[str] | None = None,
) -> SourceFinding:
    raw_payload = {}
    if compliance_types:
        raw_payload["Types"] = compliance_types

    sf = SourceFinding(
        aws_account_id=aws_account_id,
        workspace_id=workspace_id,
        source=FindingSource.SECURITY_HUB,
        native_finding_id=native_id,
        severity=severity,
        title=f"Test finding {native_id}",
        description="Test description",
        raw_payload=raw_payload,
        region="us-east-1",
        resource_arn=resource_arn,
        resource_type=resource_type,
        first_observed_at="2024-01-01T00:00:00Z",
        last_observed_at="2024-01-02T00:00:00Z",
    )
    db.add(sf)
    await db.flush()
    await db.refresh(sf)
    return sf


# ── Unit tests (no DB) ─────────────────────────────────────────────────────────

def test_compute_fingerprint_is_deterministic():
    ws = uuid.uuid4()
    acct = uuid.uuid4()
    fp1 = _compute_fingerprint(ws, acct, "arn:aws:s3:::bucket", "S3 Public", FindingSource.SECURITY_HUB)
    fp2 = _compute_fingerprint(ws, acct, "arn:aws:s3:::bucket", "S3 Public", FindingSource.SECURITY_HUB)
    assert fp1 == fp2
    assert len(fp1) == 16


def test_compute_fingerprint_different_resources_produce_different_fp():
    ws = uuid.uuid4()
    acct = uuid.uuid4()
    fp1 = _compute_fingerprint(ws, acct, "arn:aws:s3:::bucket-a", "title", FindingSource.SECURITY_HUB)
    fp2 = _compute_fingerprint(ws, acct, "arn:aws:s3:::bucket-b", "title", FindingSource.SECURITY_HUB)
    assert fp1 != fp2


@pytest.mark.parametrize("severity,resource_type,expected_range", [
    (FindingSeverity.CRITICAL, "AwsS3Bucket", (9.0, 10.0)),     # public
    (FindingSeverity.CRITICAL, "AwsLambdaFunction", (8.0, 9.0)),  # not public
    (FindingSeverity.HIGH, "AwsS3Bucket", (7.0, 8.0)),
    (FindingSeverity.MEDIUM, None, (3.0, 5.0)),
    (FindingSeverity.INFO, None, (0.0, 1.0)),
])
def test_compute_risk_score(severity, resource_type, expected_range):
    score = _compute_risk_score(severity, resource_type)
    low, high = expected_range
    assert low <= score <= high, f"score={score} not in [{low}, {high}] for {severity}/{resource_type}"


def test_map_compliance_frameworks_cis():
    raw = {
        "Types": [
            "Software and Configuration Checks/Industry and Regulatory Standards/CIS AWS Foundations Benchmark/v/1.2.0/1.1"
        ]
    }
    frameworks = _map_compliance_frameworks(raw)
    assert "CIS_AWS_1.4" in frameworks


def test_map_compliance_frameworks_empty():
    assert _map_compliance_frameworks({}) == []
    assert _map_compliance_frameworks({"Types": []}) == []


# ── Integration tests (with SQLite DB) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_normalize_creates_canonical_finding(db_session):
    ws_id, acct_id = await _seed_workspace_and_account(db_session)
    await _seed_source_finding(db_session, acct_id, ws_id)
    await db_session.commit()

    source_repo = SourceFindingRepository(db_session)
    canonical_repo = CanonicalFindingRepository(db_session)
    svc = NormalizationService(source_repo, canonical_repo)

    stats = await svc.normalize_account(aws_account_id=acct_id, workspace_id=ws_id)
    await db_session.commit()

    assert stats["created"] == 1
    assert stats["updated"] == 0
    assert stats["total_processed"] == 1


@pytest.mark.asyncio
async def test_normalize_is_idempotent(db_session):
    """Re-running normalization on same findings updates (not duplicates) canonical."""
    ws_id, acct_id = await _seed_workspace_and_account(db_session)
    await _seed_source_finding(db_session, acct_id, ws_id, native_id="idem-001")
    await db_session.commit()

    source_repo = SourceFindingRepository(db_session)
    canonical_repo = CanonicalFindingRepository(db_session)
    svc = NormalizationService(source_repo, canonical_repo)

    # First run — creates canonical finding + links source finding
    stats1 = await svc.normalize_account(aws_account_id=acct_id, workspace_id=ws_id)
    await db_session.commit()
    assert stats1["created"] == 1

    # Second run — source finding already linked, nothing to process
    stats2 = await svc.normalize_account(aws_account_id=acct_id, workspace_id=ws_id)
    await db_session.commit()
    assert stats2["total_processed"] == 0


@pytest.mark.asyncio
async def test_normalize_links_source_to_canonical(db_session):
    """Source finding gets canonical_finding_id populated after normalization."""
    from sqlalchemy import select

    ws_id, acct_id = await _seed_workspace_and_account(db_session)
    sf = await _seed_source_finding(db_session, acct_id, ws_id, native_id="link-001")
    await db_session.commit()

    source_repo = SourceFindingRepository(db_session)
    canonical_repo = CanonicalFindingRepository(db_session)
    svc = NormalizationService(source_repo, canonical_repo)

    await svc.normalize_account(aws_account_id=acct_id, workspace_id=ws_id)
    await db_session.commit()

    # Re-fetch the source finding to confirm the link
    await db_session.refresh(sf)
    assert sf.canonical_finding_id is not None


@pytest.mark.asyncio
async def test_normalize_different_resources_different_canonicals(db_session):
    """Two different resource ARNs produce two separate canonical findings."""
    ws_id, acct_id = await _seed_workspace_and_account(db_session)
    await _seed_source_finding(db_session, acct_id, ws_id, native_id="f-001", resource_arn="arn:aws:s3:::bucket-a")
    await _seed_source_finding(db_session, acct_id, ws_id, native_id="f-002", resource_arn="arn:aws:s3:::bucket-b")
    await db_session.commit()

    source_repo = SourceFindingRepository(db_session)
    canonical_repo = CanonicalFindingRepository(db_session)
    svc = NormalizationService(source_repo, canonical_repo)

    stats = await svc.normalize_account(aws_account_id=acct_id, workspace_id=ws_id)
    await db_session.commit()

    assert stats["created"] == 2


@pytest.mark.asyncio
async def test_canonical_finding_risk_score_is_set(db_session):
    """Risk score is set by normalization service (never zero for HIGH+public)."""
    ws_id, acct_id = await _seed_workspace_and_account(db_session)
    await _seed_source_finding(
        db_session, acct_id, ws_id,
        native_id="risk-001",
        severity=FindingSeverity.HIGH,
        resource_type="AwsS3Bucket",
    )
    await db_session.commit()

    source_repo = SourceFindingRepository(db_session)
    canonical_repo = CanonicalFindingRepository(db_session)
    svc = NormalizationService(source_repo, canonical_repo)

    await svc.normalize_account(aws_account_id=acct_id, workspace_id=ws_id)
    await db_session.commit()

    canonicals = await canonical_repo.list_by_workspace(ws_id)
    assert len(canonicals) == 1
    assert canonicals[0].risk_score is not None
    # HIGH + AwsS3Bucket (internet-facing) base = 7.5.
    # _seed_source_finding uses first_observed_at="2024-01-01" which is >90 days
    # from test run time → age_weight=0.7 → expected = 7.5×0.7 = 5.25.
    # Minimum acceptable for HIGH+public at any age weight is 7.5×0.7 = 5.25.
    assert canonicals[0].risk_score >= 5.0  # HIGH + internet-facing (age-weighted)


@pytest.mark.asyncio
async def test_count_by_severity(db_session):
    """count_by_severity returns correct severity breakdown."""
    ws_id, acct_id = await _seed_workspace_and_account(db_session)
    await _seed_source_finding(db_session, acct_id, ws_id, native_id="c-001", severity=FindingSeverity.CRITICAL, resource_arn="arn:aws:s3:::bucket-alpha")
    await _seed_source_finding(db_session, acct_id, ws_id, native_id="c-002", severity=FindingSeverity.HIGH, resource_arn="arn:aws:s3:::bucket-beta")
    await _seed_source_finding(db_session, acct_id, ws_id, native_id="c-003", severity=FindingSeverity.HIGH, resource_arn="arn:aws:s3:::bucket-gamma")
    await db_session.commit()

    source_repo = SourceFindingRepository(db_session)
    canonical_repo = CanonicalFindingRepository(db_session)
    svc = NormalizationService(source_repo, canonical_repo)

    await svc.normalize_account(aws_account_id=acct_id, workspace_id=ws_id)
    await db_session.commit()

    counts = await canonical_repo.count_by_severity(ws_id)
    assert counts["critical"] == 1
    assert counts["high"] == 2
    assert counts["medium"] == 0
