"""
Findings API tests — Phase 3.

Strategy:
- HTTP-level tests with SQLite in-memory DB.
- canonical findings are inserted directly via db_session fixture.
- No mock AWS calls needed (no sync triggered).
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
    "tenant_name": "Findings Corp",
    "tenant_slug": "findings-corp",
    "workspace_name": "Production",
    "email": "admin@findings.example.com",
    "password": "securepw123",
    "full_name": "Findings Admin",
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


async def _seed_infra(db) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Insert Tenant → Workspace → AwsAccount. Returns (tenant_id, workspace_id, aws_account_id)."""
    tenant = Tenant(
        name="FindTest Tenant",
        slug="find-tenant",
        plan=TenantPlan.BASELINE,
        status=TenantStatus.ACTIVE,
    )
    db.add(tenant)
    await db.flush()

    ws = Workspace(
        tenant_id=tenant.id,
        name="Default",
        slug="default",
        status=WorkspaceStatus.ACTIVE,
    )
    db.add(ws)
    await db.flush()

    acct = AwsAccount(
        workspace_id=ws.id,
        account_id="111122223333",
        role_arn="arn:aws:iam::111122223333:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()

    return tenant.id, ws.id, acct.id


async def _seed_canonical_finding(
    db,
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
    *,
    severity: FindingSeverity = FindingSeverity.HIGH,
    status: FindingStatus = FindingStatus.OPEN,
    title: str = "Test Finding",
    compliance_frameworks: list[str] | None = None,
    tags: dict | None = None,
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
        risk_score=7.5,
        title=title,
        description="Test description",
        remediation="Fix it",
        resource_arn="arn:aws:s3:::test-bucket",
        resource_type="AwsS3Bucket",
        region="us-east-1",
        compliance_frameworks=compliance_frameworks or [],
        tags=tags or {},
        first_seen_at="2024-01-01T00:00:00Z",
        last_seen_at="2024-01-02T00:00:00Z",
    )
    db.add(finding)
    await db.flush()
    await db.refresh(finding)
    return finding


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_findings_no_auth_returns_401(client: AsyncClient):
    res = await client.get("/api/v1/findings")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_findings_empty(client: AsyncClient):
    token = await _get_token(client)
    res = await client.get("/api/v1/findings", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["page"] == 1


@pytest.mark.asyncio
async def test_list_findings_returns_paginated(client: AsyncClient, db_session):
    """Insert 3 findings via register → seed infra → seed findings → list."""
    token = await _get_token(client)

    # Get workspace_id from /me
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert me_res.status_code == 200
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    # Seed infrastructure using same workspace from registration
    # We need to reuse the registered workspace — find the aws_account for it
    # by seeding infra with a fresh tenant/workspace in db (db_session may differ)
    # Instead: create an AWS account via HTTP for simplicity (no STS needed for listing findings)
    # Actually we need an aws_account row in DB; use db_session to insert directly
    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id="222233334444",
        role_arn="arn:aws:iam::222233334444:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()
    aws_account_id = acct.id

    for i in range(3):
        await _seed_canonical_finding(
            db_session,
            workspace_id,
            aws_account_id,
            title=f"Finding {i}",
            severity=FindingSeverity.HIGH,
        )
    await db_session.commit()

    res = await client.get("/api/v1/findings", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 3
    assert len(body["items"]) == 3
    assert body["pages"] == 1


@pytest.mark.asyncio
async def test_list_findings_filter_by_severity(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id="333344445555",
        role_arn="arn:aws:iam::333344445555:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()
    aws_account_id = acct.id

    await _seed_canonical_finding(
        db_session, workspace_id, aws_account_id,
        title="Critical Finding", severity=FindingSeverity.CRITICAL,
    )
    await _seed_canonical_finding(
        db_session, workspace_id, aws_account_id,
        title="High Finding", severity=FindingSeverity.HIGH,
    )
    await db_session.commit()

    res = await client.get(
        "/api/v1/findings?severity=critical", headers=_auth(token)
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["severity"] == "critical"


@pytest.mark.asyncio
async def test_list_findings_filter_by_status(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id="444455556666",
        role_arn="arn:aws:iam::444455556666:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()
    aws_account_id = acct.id

    await _seed_canonical_finding(
        db_session, workspace_id, aws_account_id,
        title="Open Finding", status=FindingStatus.OPEN,
    )
    await _seed_canonical_finding(
        db_session, workspace_id, aws_account_id,
        title="Resolved Finding", status=FindingStatus.RESOLVED,
    )
    await db_session.commit()

    res = await client.get(
        "/api/v1/findings?status=open", headers=_auth(token)
    )
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "open"


@pytest.mark.asyncio
async def test_get_finding(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id="555566667777",
        role_arn="arn:aws:iam::555566667777:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()

    finding = await _seed_canonical_finding(
        db_session, workspace_id, acct.id, title="Get Me"
    )
    await db_session.commit()

    res = await client.get(
        f"/api/v1/findings/{finding.id}", headers=_auth(token)
    )
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == str(finding.id)
    assert body["title"] == "Get Me"


@pytest.mark.asyncio
async def test_get_finding_not_found_returns_404(client: AsyncClient):
    token = await _get_token(client)
    fake_id = uuid.uuid4()
    res = await client.get(f"/api/v1/findings/{fake_id}", headers=_auth(token))
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_update_finding_status(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id="666677778888",
        role_arn="arn:aws:iam::666677778888:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()

    finding = await _seed_canonical_finding(
        db_session, workspace_id, acct.id, title="Status Update"
    )
    await db_session.commit()

    res = await client.patch(
        f"/api/v1/findings/{finding.id}",
        json={"status": "in_progress"},
        headers=_auth(token),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_update_finding_status_resolved_sets_resolved_at(
    client: AsyncClient, db_session
):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id="777788889999",
        role_arn="arn:aws:iam::777788889999:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()

    finding = await _seed_canonical_finding(
        db_session, workspace_id, acct.id, title="Resolve Me"
    )
    await db_session.commit()

    res = await client.patch(
        f"/api/v1/findings/{finding.id}",
        json={"status": "resolved"},
        headers=_auth(token),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "resolved"
    assert body["resolved_at"] is not None


@pytest.mark.asyncio
async def test_update_finding_tags(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id="888899990000",
        role_arn="arn:aws:iam::888899990000:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()

    finding = await _seed_canonical_finding(
        db_session, workspace_id, acct.id, title="Tag Me"
    )
    await db_session.commit()

    res = await client.patch(
        f"/api/v1/findings/{finding.id}",
        json={"tags": {"owner": "security-team", "ticket": "SEC-123"}},
        headers=_auth(token),
    )
    assert res.status_code == 200
    tags = res.json()["tags"]
    assert tags["owner"] == "security-team"
    assert tags["ticket"] == "SEC-123"


@pytest.mark.asyncio
async def test_get_finding_stats(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id="999900001111",
        role_arn="arn:aws:iam::999900001111:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()

    await _seed_canonical_finding(
        db_session, workspace_id, acct.id,
        title="Critical One", severity=FindingSeverity.CRITICAL,
    )
    await _seed_canonical_finding(
        db_session, workspace_id, acct.id,
        title="High One", severity=FindingSeverity.HIGH,
    )
    await _seed_canonical_finding(
        db_session, workspace_id, acct.id,
        title="High Two", severity=FindingSeverity.HIGH,
    )
    await db_session.commit()

    res = await client.get("/api/v1/findings/stats", headers=_auth(token))
    assert res.status_code == 200
    body = res.json()
    assert "by_severity" in body
    assert "by_status" in body
    assert body["total"] == 3
    assert body["by_severity"]["critical"] == 1
    assert body["by_severity"]["high"] == 2
    assert isinstance(body["breakdown"], list)
