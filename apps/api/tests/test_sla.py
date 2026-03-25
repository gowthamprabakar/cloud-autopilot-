"""
SLA Tracking tests — Sprint 12.
"""

import hashlib
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aws_account import AwsAccount
from app.models.canonical_finding import CanonicalFinding
from app.models.enums import (
    AwsAccountStatus,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    TenantPlan,
    TenantStatus,
    WorkspaceStatus,
)
from app.models.tenant import Tenant
from app.models.workspace import Workspace

# ── Shared payloads ──────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "SLA Corp",
    "tenant_slug": "sla-corp",
    "workspace_name": "Production",
    "email": "admin@sla.example.com",
    "password": "securepw123",
    "full_name": "SLA Admin",
    "plan": "baseline",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_token(client: AsyncClient, payload: dict | None = None) -> str:
    p = payload or REGISTER_PAYLOAD
    res = await client.post("/api/v1/auth/register", json=p)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _seed_aws_account(db: AsyncSession, workspace_id: uuid.UUID, account_id: str = "111122223333") -> AwsAccount:
    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id=account_id,
        role_arn=f"arn:aws:iam::{account_id}:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()
    return acct


async def _seed_finding(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
    *,
    severity: FindingSeverity = FindingSeverity.HIGH,
    status: FindingStatus = FindingStatus.OPEN,
    title: str = "Test Finding",
    first_seen_at: str = "2024-01-01T00:00:00Z",
) -> CanonicalFinding:
    fp = hashlib.sha256(
        f"{workspace_id}:{aws_account_id}:{title}:{uuid.uuid4()}".encode()
    ).hexdigest()[:16]

    finding = CanonicalFinding(
        workspace_id=workspace_id,
        aws_account_id=aws_account_id,
        fingerprint=fp,
        primary_source=FindingSource.SECURITY_HUB,
        severity=severity,
        status=status,
        risk_score=7.5,
        title=title,
        description="Test description",
        remediation="Fix it",
        resource_arn="arn:aws:s3:::test-bucket",
        resource_type="AwsS3Bucket",
        region="us-east-1",
        compliance_frameworks=[],
        tags={},
        first_seen_at=first_seen_at,
        last_seen_at=first_seen_at,
    )
    db.add(finding)
    await db.flush()
    await db.refresh(finding)
    return finding


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sla_summary_empty_workspace(client: AsyncClient):
    """GET /sla/summary on workspace with no findings returns all zero counts."""
    token = await _get_token(client)
    res = await client.get("/api/v1/sla/summary", headers=_auth(token))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total_open"] == 0
    assert body["breached"] == 0
    assert body["at_risk"] == 0
    assert body["on_track"] == 0


@pytest.mark.asyncio
async def test_sla_summary_with_open_findings(client: AsyncClient, db_session: AsyncSession):
    """Seed old findings; summary shows breached > 0."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "222233334444")
    # first_seen_at far in the past → all severity thresholds breached
    await _seed_finding(
        db_session, workspace_id, acct.id,
        severity=FindingSeverity.LOW,
        first_seen_at="2020-01-01T00:00:00Z",
    )
    await db_session.commit()

    res = await client.get("/api/v1/sla/summary", headers=_auth(token))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["total_open"] == 1
    assert body["breached"] > 0


@pytest.mark.asyncio
async def test_sla_list_all_findings(client: AsyncClient, db_session: AsyncSession):
    """Seed findings; GET /sla returns list with sla_status field."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "333344445555")
    await _seed_finding(
        db_session, workspace_id, acct.id,
        first_seen_at="2020-01-01T00:00:00Z",
    )
    await db_session.commit()

    res = await client.get("/api/v1/sla", headers=_auth(token))
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) >= 1
    for item in items:
        assert "sla_status" in item
        assert "sla_days_remaining" in item
        assert "sla_due_date" in item
        assert "id" in item
        assert "title" in item


@pytest.mark.asyncio
async def test_sla_filter_by_status(client: AsyncClient, db_session: AsyncSession):
    """Seed old findings; GET /sla?status=breached returns only breached."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "444455556666")
    await _seed_finding(
        db_session, workspace_id, acct.id,
        severity=FindingSeverity.CRITICAL,
        first_seen_at="2020-01-01T00:00:00Z",
        title="Old Critical Finding",
    )
    await db_session.commit()

    res = await client.get("/api/v1/sla?status=breached", headers=_auth(token))
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) >= 1
    for item in items:
        assert item["sla_status"] == "breached"


@pytest.mark.asyncio
async def test_sla_resolved_finding_excluded(client: AsyncClient, db_session: AsyncSession):
    """Resolved findings are NOT returned in GET /sla (only open)."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "555566667777")
    await _seed_finding(
        db_session, workspace_id, acct.id,
        status=FindingStatus.RESOLVED,
        title="Resolved Finding",
        first_seen_at="2020-01-01T00:00:00Z",
    )
    await db_session.commit()

    res = await client.get("/api/v1/sla", headers=_auth(token))
    assert res.status_code == 200, res.text
    items = res.json()
    # Resolved finding should not appear
    titles = [item["title"] for item in items]
    assert "Resolved Finding" not in titles


@pytest.mark.asyncio
async def test_sla_respects_workspace_settings(client: AsyncClient, db_session: AsyncSession):
    """Custom SLA: set sla_days_critical=1, seed 2-day-old critical → breached."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    # Update settings: critical SLA = 1 day
    patch_res = await client.patch(
        "/api/v1/workspace/settings",
        json={"sla_days_critical": 1},
        headers=_auth(token),
    )
    assert patch_res.status_code == 200, patch_res.text

    acct = await _seed_aws_account(db_session, workspace_id, "666677778888")
    # 2 days ago — with default 3d SLA would be on_track, with 1d SLA is breached
    await _seed_finding(
        db_session, workspace_id, acct.id,
        severity=FindingSeverity.CRITICAL,
        title="Near-breach Critical",
        first_seen_at="2026-03-13T00:00:00Z",  # 2 days before 2026-03-15
    )
    await db_session.commit()

    res = await client.get("/api/v1/sla", headers=_auth(token))
    assert res.status_code == 200, res.text
    items = res.json()
    critical_items = [i for i in items if i["title"] == "Near-breach Critical"]
    assert len(critical_items) == 1
    assert critical_items[0]["sla_status"] == "breached"
