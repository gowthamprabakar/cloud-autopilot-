"""
Tenant isolation tests — verifies workspace_id boundary enforcement.

Strategy:
- Register two separate tenants with distinct slugs.
- Each creates resources (AWS accounts, findings).
- Verify Tenant A gets 404 when accessing Tenant B's resources.
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

# ── Registration payloads ────────────────────────────────────────────────────

TENANT_A = {
    "tenant_name": "Tenant Alpha",
    "tenant_slug": "tenant-alpha",
    "workspace_name": "Alpha Workspace",
    "email": "admin@alpha.example.com",
    "password": "alphapw123",
    "full_name": "Alpha Admin",
    "plan": "baseline",
}

TENANT_B = {
    "tenant_name": "Tenant Beta",
    "tenant_slug": "tenant-beta",
    "workspace_name": "Beta Workspace",
    "email": "admin@beta.example.com",
    "password": "betapw123",
    "full_name": "Beta Admin",
    "plan": "baseline",
}

_VALID_ACCOUNT_A = {
    "account_id": "100000000001",
    "account_alias": "alpha-aws",
    "role_arn": "arn:aws:iam::100000000001:role/CloudPosture",
    "external_id": None,
}

_VALID_ACCOUNT_B = {
    "account_id": "200000000002",
    "account_alias": "beta-aws",
    "role_arn": "arn:aws:iam::200000000002:role/CloudPosture",
    "external_id": None,
}


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _register(client: AsyncClient, payload: dict) -> str:
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _get_workspace_id(client: AsyncClient, token: str) -> uuid.UUID:
    res = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert res.status_code == 200
    return uuid.UUID(res.json()["workspace_id"])


async def _create_account_in_db(db_session, workspace_id: uuid.UUID, account_id: str) -> AwsAccount:
    """Directly insert an AwsAccount to avoid STS calls."""
    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id=account_id,
        role_arn=f"arn:aws:iam::{account_id}:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db_session.add(acct)
    await db_session.flush()
    await db_session.commit()
    return acct


async def _create_finding_in_db(
    db_session,
    workspace_id: uuid.UUID,
    aws_account_id: uuid.UUID,
) -> CanonicalFinding:
    import hashlib
    fingerprint = hashlib.sha256(
        f"{workspace_id}:{aws_account_id}:isolation-test:{uuid.uuid4()}".encode()
    ).hexdigest()[:16]

    finding = CanonicalFinding(
        workspace_id=workspace_id,
        aws_account_id=aws_account_id,
        fingerprint=fingerprint,
        primary_source=FindingSource.SECURITY_HUB,
        severity=FindingSeverity.HIGH,
        status=FindingStatus.OPEN,
        risk_score=6.5,
        title="Isolation Test Finding",
        description=None,
        remediation=None,
        resource_arn="arn:aws:s3:::test-bucket",
        resource_type="AwsS3Bucket",
        region="us-east-1",
        compliance_frameworks=[],
        tags={},
        first_seen_at="2024-01-01T00:00:00Z",
        last_seen_at="2024-01-02T00:00:00Z",
    )
    db_session.add(finding)
    await db_session.flush()
    await db_session.commit()
    return finding


# ── Tests ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_cannot_access_other_tenant_accounts(
    client: AsyncClient, db_session
):
    """User A cannot list or access User B's AWS accounts."""
    token_a = await _register(client, TENANT_A)
    token_b = await _register(client, TENANT_B)

    ws_b = await _get_workspace_id(client, token_b)
    acct_b = await _create_account_in_db(db_session, ws_b, "200000000099")

    # Token A should NOT see account that belongs to workspace B
    res = await client.get(
        f"/api/v1/aws-accounts/{acct_b.id}", headers=_auth(token_a)
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_access_other_workspace_findings(
    client: AsyncClient, db_session
):
    """User A cannot list findings that belong to workspace B."""
    token_a = await _register(client, TENANT_A)
    token_b = await _register(client, TENANT_B)

    ws_b = await _get_workspace_id(client, token_b)
    acct_b = await _create_account_in_db(db_session, ws_b, "300000000099")
    finding_b = await _create_finding_in_db(db_session, ws_b, acct_b.id)

    # User A lists findings — should see zero (their own workspace is empty)
    res = await client.get("/api/v1/findings", headers=_auth(token_a))
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 0
    # Ensure finding_b.id is not in the items
    item_ids = [item["id"] for item in body["items"]]
    assert str(finding_b.id) not in item_ids


@pytest.mark.asyncio
async def test_user_cannot_get_other_workspace_account(
    client: AsyncClient, db_session
):
    """GET /aws-accounts/{id} returns 404 when account belongs to different workspace."""
    token_a = await _register(client, TENANT_A)
    token_b = await _register(client, TENANT_B)

    ws_b = await _get_workspace_id(client, token_b)
    acct_b = await _create_account_in_db(db_session, ws_b, "400000000099")

    # User A tries to GET B's specific account — should 404
    res = await client.get(
        f"/api/v1/aws-accounts/{acct_b.id}", headers=_auth(token_a)
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_user_cannot_delete_other_workspace_account(
    client: AsyncClient, db_session
):
    """DELETE /aws-accounts/{id} returns 404 when account belongs to different workspace."""
    token_a = await _register(client, TENANT_A)
    token_b = await _register(client, TENANT_B)

    ws_b = await _get_workspace_id(client, token_b)
    acct_b = await _create_account_in_db(db_session, ws_b, "500000000099")

    # User A tries to DELETE B's account — should 404
    res = await client.delete(
        f"/api/v1/aws-accounts/{acct_b.id}", headers=_auth(token_a)
    )
    assert res.status_code == 404

    # Verify the account still exists for user B
    res_b = await client.get(
        f"/api/v1/aws-accounts/{acct_b.id}", headers=_auth(token_b)
    )
    assert res_b.status_code == 200
