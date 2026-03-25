"""
Sprint 7 — User management tests.

Covers: list members, invite, role update, deactivate, workspace current.
"""

import pytest
from httpx import AsyncClient

# ── Helpers ──────────────────────────────────────────────────────────────────

_BASE_REGISTER = {
    "tenant_name": "User Corp",
    "tenant_slug": "user-corp",
    "workspace_name": "Main Workspace",
    "email": "admin@user-corp.com",
    "password": "adminpassword1",
    "full_name": "Admin User",
    "plan": "baseline",
}


async def _register_and_login(
    client: AsyncClient,
    payload: dict | None = None,
) -> str:
    """Register a new tenant+user and return the access token."""
    p = payload or _BASE_REGISTER
    res = await client.post("/api/v1/auth/register", json=p)
    assert res.status_code == 201, res.text
    return res.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient, email: str, password: str) -> str:
    res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_users_returns_self(client: AsyncClient):
    """Authenticated user can list workspace members and sees themselves."""
    token = await _register_and_login(client)

    res = await client.get("/api/v1/users", headers=_auth(token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    emails = [u["email"] for u in data["items"]]
    assert "admin@user-corp.com" in emails


@pytest.mark.asyncio
async def test_invite_user_requires_admin(client: AsyncClient):
    """Analyst cannot invite users — expects 403."""
    # Register super_admin and invite an analyst
    admin_token = await _register_and_login(client)

    analyst_payload = {
        "email": "analyst@user-corp.com",
        "full_name": "Analyst User",
        "role": "analyst",
        "password": "analystpw99",
    }
    invite_res = await client.post(
        "/api/v1/users/invite", json=analyst_payload, headers=_auth(admin_token)
    )
    assert invite_res.status_code == 201, invite_res.text

    # Login as analyst
    analyst_token = await _login(client, "analyst@user-corp.com", "analystpw99")

    # Analyst tries to invite someone — should fail
    new_user_payload = {
        "email": "another@user-corp.com",
        "full_name": "Another User",
        "role": "viewer",
        "password": "viewerpw99!",
    }
    res = await client.post(
        "/api/v1/users/invite", json=new_user_payload, headers=_auth(analyst_token)
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_invite_user_as_admin(client: AsyncClient):
    """Admin can invite a new user; response is 201 with UserResponse body."""
    token = await _register_and_login(client)

    invite_payload = {
        "email": "newmember@user-corp.com",
        "full_name": "New Member",
        "role": "analyst",
        "password": "newmemberpw1",
    }
    res = await client.post(
        "/api/v1/users/invite", json=invite_payload, headers=_auth(token)
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["email"] == "newmember@user-corp.com"
    assert data["role"] == "analyst"
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_invite_duplicate_email_returns_409(client: AsyncClient):
    """Inviting with an email already in the tenant returns 409."""
    token = await _register_and_login(client)

    invite_payload = {
        "email": "dup@user-corp.com",
        "full_name": "Dup User",
        "role": "analyst",
        "password": "duppw99abc",
    }
    res1 = await client.post(
        "/api/v1/users/invite", json=invite_payload, headers=_auth(token)
    )
    assert res1.status_code == 201, res1.text

    res2 = await client.post(
        "/api/v1/users/invite", json=invite_payload, headers=_auth(token)
    )
    assert res2.status_code == 409, res2.text


@pytest.mark.asyncio
async def test_update_role_requires_admin(client: AsyncClient):
    """Analyst cannot update another user's role — expects 403."""
    admin_token = await _register_and_login(client)

    # Invite a second user as analyst
    invite_res = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "analyst2@user-corp.com",
            "full_name": "Analyst 2",
            "role": "analyst",
            "password": "analystpw99a",
        },
        headers=_auth(admin_token),
    )
    assert invite_res.status_code == 201
    target_user_id = invite_res.json()["id"]

    # Invite a third user as analyst (they'll try to update)
    invite_res2 = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "analyst3@user-corp.com",
            "full_name": "Analyst 3",
            "role": "analyst",
            "password": "analystpw99b",
        },
        headers=_auth(admin_token),
    )
    assert invite_res2.status_code == 201

    analyst_token = await _login(client, "analyst3@user-corp.com", "analystpw99b")

    res = await client.patch(
        f"/api/v1/users/{target_user_id}/role",
        json={"role": "viewer"},
        headers=_auth(analyst_token),
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_update_role_as_admin(client: AsyncClient):
    """Admin can change another user's role."""
    admin_token = await _register_and_login(client)

    invite_res = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "roletest@user-corp.com",
            "full_name": "Role Test",
            "role": "analyst",
            "password": "roletestpw1",
        },
        headers=_auth(admin_token),
    )
    assert invite_res.status_code == 201
    user_id = invite_res.json()["id"]

    res = await client.patch(
        f"/api/v1/users/{user_id}/role",
        json={"role": "viewer"},
        headers=_auth(admin_token),
    )
    assert res.status_code == 200, res.text
    assert res.json()["role"] == "viewer"


@pytest.mark.asyncio
async def test_cannot_change_own_role(client: AsyncClient):
    """User cannot change their own role — expects 403."""
    token = await _register_and_login(client)

    # Get own user id
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    own_id = me_res.json()["id"]

    res = await client.patch(
        f"/api/v1/users/{own_id}/role",
        json={"role": "viewer"},
        headers=_auth(token),
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_deactivate_user_as_admin(client: AsyncClient):
    """Admin can deactivate another user; deactivated user no longer in list."""
    admin_token = await _register_and_login(client)

    invite_res = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "deactivate@user-corp.com",
            "full_name": "To Deactivate",
            "role": "analyst",
            "password": "deactivatepw1",
        },
        headers=_auth(admin_token),
    )
    assert invite_res.status_code == 201
    user_id = invite_res.json()["id"]

    # Deactivate
    del_res = await client.delete(
        f"/api/v1/users/{user_id}", headers=_auth(admin_token)
    )
    assert del_res.status_code == 204, del_res.text

    # User should no longer appear in the list
    list_res = await client.get("/api/v1/users", headers=_auth(admin_token))
    assert list_res.status_code == 200
    emails = [u["email"] for u in list_res.json()["items"]]
    assert "deactivate@user-corp.com" not in emails


@pytest.mark.asyncio
async def test_cannot_deactivate_self(client: AsyncClient):
    """User cannot deactivate themselves — expects 403."""
    token = await _register_and_login(client)

    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    own_id = me_res.json()["id"]

    res = await client.delete(f"/api/v1/users/{own_id}", headers=_auth(token))
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_get_workspace_current(client: AsyncClient):
    """GET /workspaces/current returns the current workspace details."""
    token = await _register_and_login(client)

    res = await client.get("/api/v1/workspaces/current", headers=_auth(token))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["name"] == "Main Workspace"
    assert "id" in data
    assert "tenant_id" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_update_workspace_name(client: AsyncClient):
    """Admin can rename the current workspace."""
    token = await _register_and_login(client)

    res = await client.patch(
        "/api/v1/workspaces/current",
        json={"name": "Renamed Workspace"},
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    assert res.json()["name"] == "Renamed Workspace"


@pytest.mark.asyncio
async def test_update_workspace_requires_admin(client: AsyncClient):
    """Analyst cannot rename the workspace — expects 403."""
    admin_token = await _register_and_login(client)

    invite_res = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "wsanalyst@user-corp.com",
            "full_name": "WS Analyst",
            "role": "analyst",
            "password": "wsanalystpw1",
        },
        headers=_auth(admin_token),
    )
    assert invite_res.status_code == 201

    analyst_token = await _login(client, "wsanalyst@user-corp.com", "wsanalystpw1")

    res = await client.patch(
        "/api/v1/workspaces/current",
        json={"name": "Should Fail"},
        headers=_auth(analyst_token),
    )
    assert res.status_code == 403, res.text
