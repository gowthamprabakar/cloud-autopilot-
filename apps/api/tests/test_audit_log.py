"""
Sprint 8 — Audit Log tests.

Covers: listing, audit entries from user actions, pagination, workspace isolation, auth.
"""

import pytest
from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────────────────────────

_BASE_REGISTER = {
    "tenant_name": "Audit Corp",
    "tenant_slug": "audit-corp",
    "workspace_name": "Audit Workspace",
    "email": "auditadmin@audit-corp.com",
    "password": "auditadminpw1",
    "full_name": "Audit Admin",
    "plan": "baseline",
}

_OTHER_REGISTER = {
    "tenant_name": "Other Audit Corp",
    "tenant_slug": "other-audit-corp",
    "workspace_name": "Other Workspace",
    "email": "otheradmin@other-audit-corp.com",
    "password": "otheradminpw1",
    "full_name": "Other Admin",
    "plan": "baseline",
}


async def _register_and_login(client: AsyncClient, payload: dict | None = None) -> str:
    p = payload or _BASE_REGISTER
    res = await client.post("/api/v1/auth/register", json=p)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_audit_log_empty_workspace(client: AsyncClient):
    """GET /audit-log on a fresh workspace returns an empty list."""
    token = await _register_and_login(client)

    res = await client.get("/api/v1/audit-log", headers=_auth(token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1
    assert data["pages"] == 1


@pytest.mark.asyncio
async def test_audit_log_invite_creates_entry(client: AsyncClient):
    """Inviting a user creates an audit log entry with action='user.invited'."""
    token = await _register_and_login(client)

    invite_payload = {
        "email": "newinvite@audit-corp.com",
        "full_name": "New Invite",
        "role": "analyst",
        "password": "invitepw123",
    }
    invite_res = await client.post(
        "/api/v1/users/invite", json=invite_payload, headers=_auth(token)
    )
    assert invite_res.status_code == 201, invite_res.text

    res = await client.get("/api/v1/audit-log", headers=_auth(token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] >= 1
    actions = [item["action"] for item in data["items"]]
    assert "user.invited" in actions

    invited_entry = next(item for item in data["items"] if item["action"] == "user.invited")
    assert invited_entry["detail"]["invited_email"] == "newinvite@audit-corp.com"
    assert invited_entry["actor_email"] == "auditadmin@audit-corp.com"


@pytest.mark.asyncio
async def test_audit_log_role_change_creates_entry(client: AsyncClient):
    """Changing a user's role creates an audit log entry with action='user.role_changed'."""
    admin_token = await _register_and_login(client)

    invite_res = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "roletest@audit-corp.com",
            "full_name": "Role Test",
            "role": "analyst",
            "password": "roletestpw1",
        },
        headers=_auth(admin_token),
    )
    assert invite_res.status_code == 201
    user_id = invite_res.json()["id"]

    patch_res = await client.patch(
        f"/api/v1/users/{user_id}/role",
        json={"role": "viewer"},
        headers=_auth(admin_token),
    )
    assert patch_res.status_code == 200

    res = await client.get("/api/v1/audit-log", headers=_auth(admin_token))
    assert res.status_code == 200
    actions = [item["action"] for item in res.json()["items"]]
    assert "user.role_changed" in actions

    role_entry = next(
        item for item in res.json()["items"] if item["action"] == "user.role_changed"
    )
    assert role_entry["detail"]["new_role"] == "viewer"
    assert role_entry["detail"]["old_role"] == "analyst"


@pytest.mark.asyncio
async def test_audit_log_deactivate_creates_entry(client: AsyncClient):
    """Deactivating a user creates an audit log entry with action='user.deactivated'."""
    admin_token = await _register_and_login(client)

    invite_res = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "deactivate@audit-corp.com",
            "full_name": "To Deactivate",
            "role": "analyst",
            "password": "deactivatepw1",
        },
        headers=_auth(admin_token),
    )
    assert invite_res.status_code == 201
    user_id = invite_res.json()["id"]

    del_res = await client.delete(
        f"/api/v1/users/{user_id}", headers=_auth(admin_token)
    )
    assert del_res.status_code == 204

    res = await client.get("/api/v1/audit-log", headers=_auth(admin_token))
    assert res.status_code == 200
    actions = [item["action"] for item in res.json()["items"]]
    assert "user.deactivated" in actions

    deact_entry = next(
        item for item in res.json()["items"] if item["action"] == "user.deactivated"
    )
    assert deact_entry["detail"]["email"] == "deactivate@audit-corp.com"


@pytest.mark.asyncio
async def test_audit_log_account_create_creates_entry(client: AsyncClient):
    """Creating an AWS account creates an audit log entry with action='aws_account.created'."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.integrations.aws.sts_client import AssumedRoleCredentials
    from app.jobs.base import JobResult, JobStatus

    token = await _register_and_login(client)

    mock_creds = AssumedRoleCredentials(
        access_key_id="ASIATESTING123",
        secret_access_key="fakesecretkey",
        session_token="faketoken456",
        assumed_role_arn="arn:aws:sts::111122223333:assumed-role/CloudPostureCopilot/test",
        expiration="2099-01-01T00:00:00+00:00",
    )
    mock_identity = {
        "Account": "111122223333",
        "Arn": "arn:aws:sts::111122223333:assumed-role/CloudPostureCopilot/test",
        "UserId": "AROA999888:test",
    }
    inst = MagicMock()
    inst.assume_role = AsyncMock(return_value=mock_creds)
    inst.get_caller_identity = AsyncMock(return_value=mock_identity)

    with patch(
        "app.jobs.aws_account_validate_job.StsClient.from_settings",
        return_value=inst,
    ):
        create_res = await client.post(
            "/api/v1/aws-accounts",
            json={
                "account_id": "111122223333",
                "account_alias": "test-account",
                "role_arn": "arn:aws:iam::111122223333:role/CloudPostureCopilot",
                "external_id": "ext-test-001",
            },
            headers=_auth(token),
        )
    assert create_res.status_code == 201, create_res.text

    res = await client.get("/api/v1/audit-log", headers=_auth(token))
    assert res.status_code == 200
    actions = [item["action"] for item in res.json()["items"]]
    assert "aws_account.created" in actions


@pytest.mark.asyncio
async def test_audit_log_pagination(client: AsyncClient):
    """Audit log pagination returns correct page and pages values."""
    admin_token = await _register_and_login(client)

    # Create 3 invites to have some audit entries
    for i in range(3):
        await client.post(
            "/api/v1/users/invite",
            json={
                "email": f"paginate{i}@audit-corp.com",
                "full_name": f"Paginate User {i}",
                "role": "analyst",
                "password": "paginatepw123",
            },
            headers=_auth(admin_token),
        )

    # Get page 1 with page_size=2
    res = await client.get(
        "/api/v1/audit-log",
        params={"page": 1, "page_size": 2},
        headers=_auth(admin_token),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert len(data["items"]) <= 2
    assert data["total"] >= 3
    assert data["pages"] >= 2


@pytest.mark.asyncio
async def test_audit_log_workspace_isolation(client: AsyncClient):
    """User A cannot see User B's audit log entries."""
    token_a = await _register_and_login(client, _BASE_REGISTER)
    token_b = await _register_and_login(client, _OTHER_REGISTER)

    # User A invites someone — creates an audit entry in workspace A
    await client.post(
        "/api/v1/users/invite",
        json={
            "email": "isolationtest@audit-corp.com",
            "full_name": "Isolation Test",
            "role": "analyst",
            "password": "isolationpw1",
        },
        headers=_auth(token_a),
    )

    # User B should not see workspace A's audit entries
    res_b = await client.get("/api/v1/audit-log", headers=_auth(token_b))
    assert res_b.status_code == 200
    actions_b = [item["action"] for item in res_b.json()["items"]]
    # Workspace B has no user.invited entry — it's in workspace A
    # (B might have 0 entries or only its own entries)
    # Just verify the invite entry from A is not visible to B by checking actor_email
    actor_emails_b = [item["actor_email"] for item in res_b.json()["items"]]
    assert "auditadmin@audit-corp.com" not in actor_emails_b


@pytest.mark.asyncio
async def test_audit_log_requires_auth(client: AsyncClient):
    """GET /audit-log without a token returns 401."""
    res = await client.get("/api/v1/audit-log")
    assert res.status_code == 401
