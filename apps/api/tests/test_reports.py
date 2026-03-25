"""
Executive Summary Report tests — GET /api/v1/reports/executive-summary

Strategy:
- HTTP-level tests with SQLite in-memory DB.
- Findings inserted directly via db_session fixture.
"""

import uuid

import pytest
from httpx import AsyncClient

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
    "tenant_name": "Reports Corp",
    "tenant_slug": "reports-corp",
    "workspace_name": "Production",
    "email": "admin@reports.example.com",
    "password": "securepw123",
    "full_name": "Reports Admin",
    "plan": "baseline",
}

REGISTER_PAYLOAD_B = {
    "tenant_name": "Reports Corp B",
    "tenant_slug": "reports-corp-b",
    "workspace_name": "Production B",
    "email": "adminb@reports.example.com",
    "password": "securepw123",
    "full_name": "Reports Admin B",
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


async def _get_workspace_and_account(
    client, db, token, account_id: str
) -> tuple[uuid.UUID, uuid.UUID]:
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert me_res.status_code == 200
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id=account_id,
        role_arn=f"arn:aws:iam::{account_id}:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()
    return workspace_id, acct.id


async def _seed_finding(
    db,
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
    *,
    severity: FindingSeverity = FindingSeverity.HIGH,
    status: FindingStatus = FindingStatus.OPEN,
    title: str = "Report Test Finding",
    risk_score: float = 5.0,
    compliance_frameworks: list[str] | None = None,
    first_seen_at: str = "2024-01-01T00:00:00Z",
    resolved_at: str | None = None,
) -> CanonicalFinding:
    import hashlib
    fingerprint = hashlib.sha256(
        f"{workspace_id}:{aws_account_id}:{title}:{uuid.uuid4()}".encode()
    ).hexdigest()[:16]

    finding = CanonicalFinding(
        workspace_id=workspace_id,
        aws_account_id=aws_account_id,
        fingerprint=fingerprint,
        primary_source=FindingSource.SECURITY_HUB,
        severity=severity,
        status=status,
        risk_score=risk_score,
        title=title,
        description="Test description",
        remediation="Fix it",
        resource_arn="arn:aws:s3:::test-bucket",
        resource_type="AwsS3Bucket",
        region="us-east-1",
        compliance_frameworks=compliance_frameworks or [],
        tags={},
        first_seen_at=first_seen_at,
        last_seen_at="2024-01-02T00:00:00Z",
        resolved_at=resolved_at,
    )
    db.add(finding)
    await db.flush()
    await db.refresh(finding)
    return finding


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_executive_summary_empty_workspace(client: AsyncClient):
    """Empty workspace returns summary with zeros."""
    token = await _get_token(client)
    res = await client.get("/api/v1/reports/executive-summary", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()

    assert body["total_findings"] == 0
    assert body["open_findings"] == 0
    assert body["critical_open"] == 0
    assert body["high_open"] == 0
    assert body["new_last_7_days"] == 0
    assert body["resolved_last_7_days"] == 0
    assert body["avg_risk_score"] is None
    assert body["mttr_days"] is None
    assert body["top_findings"] == []
    assert body["accounts"] == []
    assert body["compliance"] == []
    assert "generated_at" in body
    assert body["period_days"] == 30


@pytest.mark.asyncio
async def test_executive_summary_with_findings(client: AsyncClient, db_session):
    """Create findings with various severities/statuses, check counts match."""
    token = await _get_token(client)
    workspace_id, aws_account_id = await _get_workspace_and_account(
        client, db_session, token, "300400500600"
    )

    # 1 critical open, 1 high open, 1 medium resolved
    await _seed_finding(
        db_session, workspace_id, aws_account_id,
        severity=FindingSeverity.CRITICAL, status=FindingStatus.OPEN,
        title="Critical Open",
    )
    await _seed_finding(
        db_session, workspace_id, aws_account_id,
        severity=FindingSeverity.HIGH, status=FindingStatus.OPEN,
        title="High Open",
    )
    await _seed_finding(
        db_session, workspace_id, aws_account_id,
        severity=FindingSeverity.MEDIUM, status=FindingStatus.RESOLVED,
        title="Medium Resolved",
        resolved_at="2024-01-10T00:00:00Z",
    )
    await db_session.commit()

    res = await client.get("/api/v1/reports/executive-summary", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()

    assert body["total_findings"] == 3
    assert body["open_findings"] == 2
    assert body["critical_open"] == 1
    assert body["high_open"] == 1
    assert body["avg_risk_score"] is not None


@pytest.mark.asyncio
async def test_executive_summary_top_findings_ordered_by_risk(client: AsyncClient, db_session):
    """Top findings should be ordered by risk_score descending."""
    token = await _get_token(client)
    workspace_id, aws_account_id = await _get_workspace_and_account(
        client, db_session, token, "300400500601"
    )

    # Create 3 open findings with different risk scores
    await _seed_finding(
        db_session, workspace_id, aws_account_id,
        title="Low Risk", risk_score=2.0, status=FindingStatus.OPEN,
    )
    await _seed_finding(
        db_session, workspace_id, aws_account_id,
        title="High Risk", risk_score=9.5, status=FindingStatus.OPEN,
    )
    await _seed_finding(
        db_session, workspace_id, aws_account_id,
        title="Medium Risk", risk_score=5.0, status=FindingStatus.OPEN,
    )
    await db_session.commit()

    res = await client.get("/api/v1/reports/executive-summary", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()

    top = body["top_findings"]
    assert len(top) == 3
    # First should be highest risk score
    assert top[0]["title"] == "High Risk"
    assert top[0]["risk_score"] == 9.5
    # Last should be lowest risk score
    assert top[-1]["title"] == "Low Risk"
    assert top[-1]["risk_score"] == 2.0


@pytest.mark.asyncio
async def test_executive_summary_requires_auth(client: AsyncClient):
    """GET /reports/executive-summary without token returns 401."""
    res = await client.get("/api/v1/reports/executive-summary")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_executive_summary_workspace_isolation(client: AsyncClient, db_session):
    """User A's summary does not include User B's findings."""
    token_a = await _get_token(client, REGISTER_PAYLOAD)
    token_b = await _get_token(client, REGISTER_PAYLOAD_B)

    workspace_a, acct_a = await _get_workspace_and_account(
        client, db_session, token_a, "400500600700"
    )
    workspace_b, acct_b = await _get_workspace_and_account(
        client, db_session, token_b, "400500600701"
    )

    # Seed 2 findings for A, 5 for B
    for i in range(2):
        await _seed_finding(
            db_session, workspace_a, acct_a,
            title=f"User A Finding {i}", severity=FindingSeverity.CRITICAL,
        )
    for i in range(5):
        await _seed_finding(
            db_session, workspace_b, acct_b,
            title=f"User B Finding {i}", severity=FindingSeverity.HIGH,
        )
    await db_session.commit()

    res_a = await client.get("/api/v1/reports/executive-summary", headers=_auth(token_a))
    assert res_a.status_code == 200
    body_a = res_a.json()
    assert body_a["total_findings"] == 2
    assert body_a["critical_open"] == 2

    res_b = await client.get("/api/v1/reports/executive-summary", headers=_auth(token_b))
    assert res_b.status_code == 200
    body_b = res_b.json()
    assert body_b["total_findings"] == 5
    assert body_b["high_open"] == 5
    # B has no critical findings
    assert body_b["critical_open"] == 0


# ── Report Schedule tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_schedule_defaults(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/reports/schedule", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["frequency"] == "weekly"
    assert data["day_of_week"] == 1
    assert data["recipients"] == []


@pytest.mark.asyncio
async def test_get_schedule_idempotent(client: AsyncClient, admin_headers: dict):
    resp1 = await client.get("/api/v1/reports/schedule", headers=admin_headers)
    resp2 = await client.get("/api/v1/reports/schedule", headers=admin_headers)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]


@pytest.mark.asyncio
async def test_update_schedule(client: AsyncClient, admin_headers: dict):
    resp = await client.put(
        "/api/v1/reports/schedule",
        json={"enabled": True, "frequency": "weekly", "day_of_week": 5, "recipients": ["exec@example.com"]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["day_of_week"] == 5
    assert "exec@example.com" in data["recipients"]


@pytest.mark.asyncio
async def test_update_schedule_invalid_frequency(client: AsyncClient, admin_headers: dict):
    resp = await client.put(
        "/api/v1/reports/schedule",
        json={"frequency": "daily"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_schedule_invalid_day(client: AsyncClient, admin_headers: dict):
    resp = await client.put(
        "/api/v1/reports/schedule",
        json={"day_of_week": 8},
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_send_now_returns_zero_no_recipients(client: AsyncClient, admin_headers: dict):
    resp = await client.post("/api/v1/reports/send-now", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] == 0
    assert data["recipients"] == []
