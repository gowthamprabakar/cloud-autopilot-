"""
Bulk update findings API tests — Sprint 9.

Strategy:
- HTTP-level tests with SQLite in-memory DB.
- Canonical findings are inserted directly via db_session fixture.
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
)

# ── Shared payloads ──────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Bulk Update Corp",
    "tenant_slug": "bulk-update-corp",
    "workspace_name": "Production",
    "email": "admin@bulk.example.com",
    "password": "securepw123!",
    "full_name": "Bulk Admin",
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


async def _seed_aws_account(
    db, workspace_id: uuid.UUID, account_id: str = "111122223333"
) -> AwsAccount:
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
    db,
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
    *,
    title: str = "Test Finding",
    severity: FindingSeverity = FindingSeverity.HIGH,
    status: FindingStatus = FindingStatus.OPEN,
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
        risk_score=6.5,
        title=title,
        description="Test description",
        remediation="Fix it",
        resource_arn="arn:aws:s3:::test-bucket",
        resource_type="AwsS3Bucket",
        region="us-east-1",
        compliance_frameworks=[],
        tags={},
        first_seen_at="2024-01-01T00:00:00Z",
        last_seen_at="2024-01-02T00:00:00Z",
    )
    db.add(finding)
    await db.flush()
    await db.refresh(finding)
    return finding


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_bulk_update_status_resolved(client: AsyncClient, db_session):
    """Bulk mark 3 findings as resolved — all 3 updated, resolved_at is set."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "300400500600")
    findings = []
    for i in range(3):
        f = await _seed_finding(
            db_session, workspace_id, acct.id, title=f"Bulk Finding {i}"
        )
        findings.append(f)
    await db_session.commit()

    finding_ids = [str(f.id) for f in findings]
    res = await client.patch(
        "/api/v1/findings/bulk",
        json={"finding_ids": finding_ids, "status": "resolved"},
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["updated"] == 3
    assert body["failed"] == 0
    assert body["errors"] == []

    # Verify each finding is resolved
    for f in findings:
        get_res = await client.get(
            f"/api/v1/findings/{f.id}", headers=_auth(token)
        )
        assert get_res.status_code == 200
        data = get_res.json()
        assert data["status"] == "resolved"
        assert data["resolved_at"] is not None


@pytest.mark.asyncio
async def test_bulk_update_empty_list_422(client: AsyncClient):
    """Sending an empty finding_ids list returns 422."""
    token = await _get_token(client)
    res = await client.patch(
        "/api/v1/findings/bulk",
        json={"finding_ids": [], "status": "resolved"},
        headers=_auth(token),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_bulk_update_too_many_422(client: AsyncClient):
    """Sending 101 finding IDs returns 422 (exceeds maximum of 100)."""
    token = await _get_token(client)
    finding_ids = [str(uuid.uuid4()) for _ in range(101)]
    res = await client.patch(
        "/api/v1/findings/bulk",
        json={"finding_ids": finding_ids, "status": "in_progress"},
        headers=_auth(token),
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_bulk_update_wrong_workspace_not_updated(client: AsyncClient, db_session):
    """Finding IDs from another workspace are counted in failed, not updated."""
    # Register two users in separate workspaces
    token_a = await _get_token(
        client,
        {
            "tenant_name": "Bulk A Corp",
            "tenant_slug": "bulk-a-corp",
            "workspace_name": "Workspace A",
            "email": "admin@bulk-a.example.com",
            "password": "passwordA123!",
            "full_name": "Admin A",
            "plan": "baseline",
        },
    )
    token_b = await _get_token(
        client,
        {
            "tenant_name": "Bulk B Corp",
            "tenant_slug": "bulk-b-corp",
            "workspace_name": "Workspace B",
            "email": "admin@bulk-b.example.com",
            "password": "passwordB123!",
            "full_name": "Admin B",
            "plan": "baseline",
        },
    )

    # Get workspace IDs
    me_b = await client.get("/api/v1/auth/me", headers=_auth(token_b))
    workspace_id_b = uuid.UUID(me_b.json()["workspace_id"])

    # Seed a finding in workspace B
    acct_b = await _seed_aws_account(db_session, workspace_id_b, "700800900100")
    finding_b = await _seed_finding(db_session, workspace_id_b, acct_b.id, title="B Finding")
    await db_session.commit()

    # User A tries to bulk-update workspace B's finding
    res = await client.patch(
        "/api/v1/findings/bulk",
        json={"finding_ids": [str(finding_b.id)], "status": "resolved"},
        headers=_auth(token_a),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["updated"] == 0
    assert body["failed"] == 1
    assert len(body["errors"]) == 1


@pytest.mark.asyncio
async def test_bulk_update_requires_auth(client: AsyncClient):
    """PATCH /findings/bulk without a token returns 401."""
    res = await client.patch(
        "/api/v1/findings/bulk",
        json={"finding_ids": [str(uuid.uuid4())], "status": "resolved"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_bulk_update_partial_success(client: AsyncClient, db_session):
    """Mix of valid and invalid IDs — valid ones updated, invalid ones in failed."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "500600700800")
    valid_finding = await _seed_finding(
        db_session, workspace_id, acct.id, title="Valid Finding"
    )
    await db_session.commit()

    fake_id = str(uuid.uuid4())
    valid_id = str(valid_finding.id)

    res = await client.patch(
        "/api/v1/findings/bulk",
        json={"finding_ids": [valid_id, fake_id], "status": "in_progress"},
        headers=_auth(token),
    )
    assert res.status_code == 200
    body = res.json()
    assert body["updated"] == 1
    assert body["failed"] == 1
    assert len(body["errors"]) == 1

    # Verify valid finding is updated
    get_res = await client.get(f"/api/v1/findings/{valid_id}", headers=_auth(token))
    assert get_res.json()["status"] == "in_progress"
