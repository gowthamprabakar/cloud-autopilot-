"""
Finding Comments tests — Sprint 11.
"""

import hashlib
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
    "tenant_name": "Comments Corp",
    "tenant_slug": "comments-corp",
    "workspace_name": "Production",
    "email": "admin@comments.example.com",
    "password": "securepw123",
    "full_name": "Comments Admin",
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


async def _seed_finding(db, workspace_id: uuid.UUID, aws_account_id: uuid.UUID, title: str = "Test Finding") -> CanonicalFinding:
    fp = hashlib.sha256(
        f"{workspace_id}:{aws_account_id}:{title}:{uuid.uuid4()}".encode()
    ).hexdigest()[:16]

    finding = CanonicalFinding(
        workspace_id=workspace_id,
        aws_account_id=aws_account_id,
        fingerprint=fp,
        primary_source=FindingSource.SECURITY_HUB,
        severity=FindingSeverity.HIGH,
        status=FindingStatus.OPEN,
        risk_score=7.5,
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


async def _seed_aws_account(db, workspace_id: uuid.UUID, account_id: str = "111122223333") -> AwsAccount:
    acct = AwsAccount(
        workspace_id=workspace_id,
        account_id=account_id,
        role_arn=f"arn:aws:iam::{account_id}:role/TestRole",
        status=AwsAccountStatus.ACTIVE,
    )
    db.add(acct)
    await db.flush()
    return acct


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_comment_returns_201(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "111122223333")
    finding = await _seed_finding(db_session, workspace_id, acct.id)
    await db_session.commit()

    res = await client.post(
        f"/api/v1/findings/{finding.id}/comments",
        json={"body": "This is a comment"},
        headers=_auth(token),
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["body"] == "This is a comment"
    assert body["finding_id"] == str(finding.id)
    assert "id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_list_comments_returns_200(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "111122223344")
    finding = await _seed_finding(db_session, workspace_id, acct.id)
    await db_session.commit()

    # Add a comment
    await client.post(
        f"/api/v1/findings/{finding.id}/comments",
        json={"body": "Listed comment"},
        headers=_auth(token),
    )

    res = await client.get(
        f"/api/v1/findings/{finding.id}/comments",
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    comments = res.json()
    assert len(comments) == 1
    assert comments[0]["body"] == "Listed comment"


@pytest.mark.asyncio
async def test_add_comment_empty_body_422(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "111122223355")
    finding = await _seed_finding(db_session, workspace_id, acct.id)
    await db_session.commit()

    res = await client.post(
        f"/api/v1/findings/{finding.id}/comments",
        json={"body": ""},
        headers=_auth(token),
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_delete_own_comment(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "111122223366")
    finding = await _seed_finding(db_session, workspace_id, acct.id)
    await db_session.commit()

    # Add comment
    add_res = await client.post(
        f"/api/v1/findings/{finding.id}/comments",
        json={"body": "To be deleted"},
        headers=_auth(token),
    )
    assert add_res.status_code == 201
    comment_id = add_res.json()["id"]

    # Delete comment
    del_res = await client.delete(
        f"/api/v1/findings/{finding.id}/comments/{comment_id}",
        headers=_auth(token),
    )
    assert del_res.status_code == 204, del_res.text

    # Verify empty
    list_res = await client.get(
        f"/api/v1/findings/{finding.id}/comments",
        headers=_auth(token),
    )
    assert list_res.json() == []


@pytest.mark.asyncio
async def test_comment_requires_auth(client: AsyncClient, db_session):
    # We need a real finding id, but the auth check happens before finding lookup
    fake_id = uuid.uuid4()
    res = await client.post(
        f"/api/v1/findings/{fake_id}/comments",
        json={"body": "No auth"},
    )
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_cross_workspace_comment_rejected(client: AsyncClient, db_session):
    """User from workspace B tries GET on workspace A finding → 404."""
    token_a = await _get_token(client, REGISTER_PAYLOAD)
    token_b = await _get_token(
        client,
        {
            "tenant_name": "Cross WS Corp",
            "tenant_slug": "cross-ws-corp",
            "workspace_name": "WS B",
            "email": "admin@cross-ws.example.com",
            "password": "securepw456",
            "full_name": "Admin B",
            "plan": "baseline",
        },
    )

    me_res = await client.get("/api/v1/auth/me", headers=_auth(token_a))
    workspace_a_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_a_id, "222233334444")
    finding = await _seed_finding(db_session, workspace_a_id, acct.id)
    await db_session.commit()

    # User B tries to list comments on workspace A's finding
    res = await client.get(
        f"/api/v1/findings/{finding.id}/comments",
        headers=_auth(token_b),
    )
    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_list_comments_empty(client: AsyncClient, db_session):
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "333344445555")
    finding = await _seed_finding(db_session, workspace_id, acct.id)
    await db_session.commit()

    res = await client.get(
        f"/api/v1/findings/{finding.id}/comments",
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    assert res.json() == []


@pytest.mark.asyncio
async def test_multiple_comments_ordered(client: AsyncClient, db_session):
    """Add 2 comments, verify both returned in created_at ascending order."""
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    acct = await _seed_aws_account(db_session, workspace_id, "444455556666")
    finding = await _seed_finding(db_session, workspace_id, acct.id)
    await db_session.commit()

    await client.post(
        f"/api/v1/findings/{finding.id}/comments",
        json={"body": "First comment"},
        headers=_auth(token),
    )
    await client.post(
        f"/api/v1/findings/{finding.id}/comments",
        json={"body": "Second comment"},
        headers=_auth(token),
    )

    res = await client.get(
        f"/api/v1/findings/{finding.id}/comments",
        headers=_auth(token),
    )
    assert res.status_code == 200
    comments = res.json()
    assert len(comments) == 2
    assert comments[0]["body"] == "First comment"
    assert comments[1]["body"] == "Second comment"
