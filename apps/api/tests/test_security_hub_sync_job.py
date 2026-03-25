"""
End-to-end tests for SecurityHubSyncJob — mocks STS + SecurityHub with AsyncMock,
SQLite in-memory DB (via conftest fixtures) for finding persistence.

Tests verify:
- Full pipeline: assume_role → iter_findings → upsert source_findings → normalize
- Empty account completes with zero ingested
- Upsert idempotency: same finding twice = 1 row
- Missing role_arn → immediate FAILED result
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.aws.security_hub_client import SecurityHubFinding
from app.integrations.aws.sts_client import AssumedRoleCredentials
from app.jobs.base import JobContext, JobStatus
from app.jobs.security_hub_sync_job import SecurityHubSyncJob
from app.models.aws_account import AwsAccount
from app.models.enums import AwsAccountStatus, FindingSeverity, TenantPlan, TenantStatus, WorkspaceStatus
from app.models.tenant import Tenant
from app.models.workspace import Workspace
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.source_finding_repository import SourceFindingRepository


# ── Helpers ────────────────────────────────────────────────────────────────────

_MOCK_CREDS = AssumedRoleCredentials(
    access_key_id="ASIATESTING",
    secret_access_key="fakesecret",
    session_token="faketoken",
    assumed_role_arn="arn:aws:sts::123456789012:assumed-role/R/s",
    expiration="2099-01-01",
)


def _make_finding(native_id: str, severity: str = "HIGH", resource_arn: str | None = None) -> SecurityHubFinding:
    return SecurityHubFinding(
        native_id=native_id,
        title=f"Test finding {native_id}",
        description="Test description",
        severity=FindingSeverity(severity.lower()),
        resource_arn=resource_arn or f"arn:aws:s3:::bucket-{native_id}",
        resource_type="AwsS3Bucket",
        region="us-east-1",
        first_observed_at="2024-01-01T00:00:00Z",
        last_observed_at="2024-01-02T00:00:00Z",
        raw_payload={"Id": native_id, "Types": []},
    )


async def _setup_db(db) -> tuple[uuid.UUID, uuid.UUID, AwsAccount]:
    tenant = Tenant(name="Acme", slug="acme", plan=TenantPlan.BASELINE, status=TenantStatus.ACTIVE)
    db.add(tenant)
    await db.flush()

    ws = Workspace(tenant_id=tenant.id, name="Prod", slug="prod", status=WorkspaceStatus.ACTIVE)
    db.add(ws)
    await db.flush()

    acct = AwsAccount(
        workspace_id=ws.id,
        account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/CopilotRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()
    await db.refresh(acct)
    return tenant.id, ws.id, acct


def _make_mock_sts():
    inst = MagicMock()
    inst.assume_role = AsyncMock(return_value=_MOCK_CREDS)
    return patch("app.jobs.security_hub_sync_job.StsClient.from_settings", return_value=inst)


def _make_mock_hub_findings(findings: list[SecurityHubFinding]):
    """Patch SecurityHubClient.iter_active_findings to yield the given findings."""
    async def _gen(self, *args, **kwargs):
        for f in findings:
            yield f

    return patch(
        "app.jobs.security_hub_sync_job.SecurityHubClient.iter_active_findings",
        _gen,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_full_pipeline_ingests_and_normalizes(db_session):
    """3 findings ingested → 3 source_findings + 3 canonical_findings created."""
    findings = [_make_finding(f"f-{i:03d}") for i in range(3)]
    tenant_id, ws_id, acct = await _setup_db(db_session)
    await db_session.commit()

    source_repo = SourceFindingRepository(db_session)
    canonical_repo = CanonicalFindingRepository(db_session)
    ctx = JobContext(
        tenant_id=tenant_id, workspace_id=ws_id,
        payload={"aws_account_id": str(acct.id), "account_id": acct.account_id,
                 "role_arn": acct.role_arn, "region": "us-east-1"},
    )

    with _make_mock_sts(), _make_mock_hub_findings(findings):
        job = SecurityHubSyncJob(ctx=ctx, source_finding_repo=source_repo, canonical_finding_repo=canonical_repo)
        result = await job.execute()
        await db_session.commit()

    assert result.status == JobStatus.COMPLETED
    assert result.output["findings_ingested"] == 3
    assert result.output["findings_skipped"] == 0
    assert result.output["normalization"]["created"] == 3

    count = await source_repo.count_by_account(acct.id)
    assert count == 3

    canonicals = await canonical_repo.list_by_workspace(ws_id)
    assert len(canonicals) == 3
    assert all(c.risk_score is not None for c in canonicals)


@pytest.mark.asyncio
async def test_empty_account_completes_with_zero(db_session):
    """No findings → job completes, zero ingested."""
    tenant_id, ws_id, acct = await _setup_db(db_session)
    await db_session.commit()

    ctx = JobContext(
        tenant_id=tenant_id, workspace_id=ws_id,
        payload={"aws_account_id": str(acct.id), "account_id": acct.account_id,
                 "role_arn": acct.role_arn, "region": "us-east-1"},
    )

    with _make_mock_sts(), _make_mock_hub_findings([]):
        job = SecurityHubSyncJob(
            ctx=ctx,
            source_finding_repo=SourceFindingRepository(db_session),
            canonical_finding_repo=CanonicalFindingRepository(db_session),
        )
        result = await job.execute()
        await db_session.commit()

    assert result.status == JobStatus.COMPLETED
    assert result.output["findings_ingested"] == 0
    assert await SourceFindingRepository(db_session).count_by_account(acct.id) == 0


@pytest.mark.asyncio
async def test_upsert_is_idempotent(db_session):
    """Syncing the same finding twice produces exactly 1 source_finding row."""
    finding = _make_finding("idem-001", severity="CRITICAL")
    tenant_id, ws_id, acct = await _setup_db(db_session)
    await db_session.commit()

    def _make_job():
        return SecurityHubSyncJob(
            ctx=JobContext(
                tenant_id=tenant_id, workspace_id=ws_id,
                payload={"aws_account_id": str(acct.id), "account_id": acct.account_id,
                         "role_arn": acct.role_arn, "region": "us-east-1"},
            ),
            source_finding_repo=SourceFindingRepository(db_session),
            canonical_finding_repo=CanonicalFindingRepository(db_session),
        )

    with _make_mock_sts(), _make_mock_hub_findings([finding]):
        r1 = await _make_job().execute()
        await db_session.commit()
        r2 = await _make_job().execute()
        await db_session.commit()

    assert r1.status == JobStatus.COMPLETED
    assert r2.status == JobStatus.COMPLETED
    assert await SourceFindingRepository(db_session).count_by_account(acct.id) == 1


@pytest.mark.asyncio
async def test_missing_role_arn_returns_failed():
    """Job returns FAILED immediately if role_arn is missing from payload."""
    ctx = JobContext(
        tenant_id=uuid.uuid4(), workspace_id=uuid.uuid4(),
        payload={"aws_account_id": str(uuid.uuid4())},  # no role_arn
    )
    job = SecurityHubSyncJob(
        ctx=ctx,
        source_finding_repo=MagicMock(),
        canonical_finding_repo=MagicMock(),
    )
    result = await job.execute()
    assert result.status == JobStatus.FAILED
    assert "role_arn" in result.error


@pytest.mark.asyncio
async def test_sts_failure_returns_failed(db_session):
    """AssumeRole failure returns FAILED with STS error in output."""
    from app.integrations.aws.sts_client import StsAssumeRoleError

    tenant_id, ws_id, acct = await _setup_db(db_session)
    await db_session.commit()

    mock_sts = MagicMock()
    mock_sts.assume_role = AsyncMock(side_effect=StsAssumeRoleError("Access denied", "AccessDenied"))

    ctx = JobContext(
        tenant_id=tenant_id, workspace_id=ws_id,
        payload={"aws_account_id": str(acct.id), "account_id": acct.account_id,
                 "role_arn": acct.role_arn, "region": "us-east-1"},
    )

    with patch("app.jobs.security_hub_sync_job.StsClient.from_settings", return_value=mock_sts):
        job = SecurityHubSyncJob(
            ctx=ctx,
            source_finding_repo=SourceFindingRepository(db_session),
            canonical_finding_repo=CanonicalFindingRepository(db_session),
        )
        result = await job.execute()

    assert result.status == JobStatus.FAILED
    assert "AssumeRole" in result.error
