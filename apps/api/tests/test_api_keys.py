"""
Sprint 11 — API Key authentication tests.

Covers: create, list, revoke, authentication via sk- tokens,
expiry, workspace isolation, and role enforcement.
"""

import pytest
from datetime import UTC, datetime, timedelta
from httpx import AsyncClient

# ── Helpers ───────────────────────────────────────────────────────────────────

_REGISTER_A = {
    "tenant_name": "Acme API",
    "tenant_slug": "acme-api",
    "workspace_name": "Production",
    "email": "admin@acme-api.example.com",
    "password": "adminpassword1",
    "full_name": "Acme Admin",
    "plan": "baseline",
}

_REGISTER_B = {
    "tenant_name": "Beta Corp",
    "tenant_slug": "beta-corp",
    "workspace_name": "Beta WS",
    "email": "admin@beta-corp.example.com",
    "password": "betapassword1",
    "full_name": "Beta Admin",
    "plan": "baseline",
}


async def _register(client: AsyncClient, payload: dict) -> dict:
    """Register a new tenant+user, return the full response JSON."""
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    return res.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _create_api_key(
    client: AsyncClient,
    token: str,
    name: str = "Test Key",
    expires_at: datetime | None = None,
) -> dict:
    """Create an API key, return the response JSON."""
    payload: dict = {"name": name}
    if expires_at is not None:
        payload["expires_at"] = expires_at.isoformat()
    res = await client.post(
        "/api/v1/api-keys",
        json=payload,
        headers=_auth(token),
    )
    assert res.status_code == 201, res.text
    return res.json()


# ── Tests ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_api_key_returns_raw_key_once(client: AsyncClient):
    """POST /api-keys returns 201 with a raw_key starting 'sk-'."""
    reg = await _register(client, _REGISTER_A)
    token = reg["access_token"]

    data = await _create_api_key(client, token, "My CI Key")

    assert "raw_key" in data
    assert data["raw_key"].startswith("sk-")
    assert "id" in data
    assert data["name"] == "My CI Key"
    assert data["is_active"] is True
    # key_prefix should match the start of the raw key
    assert data["raw_key"].startswith(data["key_prefix"])


@pytest.mark.asyncio
async def test_list_api_keys_does_not_expose_raw_key(client: AsyncClient):
    """GET /api-keys shows key_prefix but never exposes raw_key."""
    reg = await _register(client, _REGISTER_A)
    token = reg["access_token"]

    created = await _create_api_key(client, token, "List Test Key")

    res = await client.get("/api/v1/api-keys", headers=_auth(token))
    assert res.status_code == 200, res.text
    items = res.json()
    assert isinstance(items, list)
    assert len(items) >= 1

    found = next((k for k in items if k["id"] == created["id"]), None)
    assert found is not None
    assert "key_prefix" in found
    assert "raw_key" not in found  # must NOT be present in list response


@pytest.mark.asyncio
async def test_api_key_authenticates_me_endpoint(client: AsyncClient):
    """Create API key → GET /me with Bearer sk-... → 200."""
    reg = await _register(client, _REGISTER_A)
    token = reg["access_token"]

    created = await _create_api_key(client, token, "Me Auth Key")
    raw_key = created["raw_key"]

    res = await client.get("/api/v1/auth/me", headers=_auth(raw_key))
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["email"] == _REGISTER_A["email"]


@pytest.mark.asyncio
async def test_api_key_authenticates_findings_endpoint(client: AsyncClient):
    """Create API key → GET /findings with Bearer sk-... → 200."""
    reg = await _register(client, _REGISTER_A)
    token = reg["access_token"]

    created = await _create_api_key(client, token, "Findings Auth Key")
    raw_key = created["raw_key"]

    res = await client.get("/api/v1/findings", headers=_auth(raw_key))
    # 200 with empty list is fine — we just need auth to work
    assert res.status_code == 200, res.text


@pytest.mark.asyncio
async def test_revoke_api_key_blocks_access(client: AsyncClient):
    """Create → use → DELETE → use again → 401."""
    reg = await _register(client, _REGISTER_A)
    token = reg["access_token"]

    created = await _create_api_key(client, token, "Revoke Test Key")
    raw_key = created["raw_key"]
    key_id = created["id"]

    # First use succeeds
    res = await client.get("/api/v1/auth/me", headers=_auth(raw_key))
    assert res.status_code == 200, res.text

    # Revoke
    res = await client.delete(
        f"/api/v1/api-keys/{key_id}", headers=_auth(token)
    )
    assert res.status_code == 204, res.text

    # Second use is blocked
    res = await client.get("/api/v1/auth/me", headers=_auth(raw_key))
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_non_admin_cannot_create_api_key(client: AsyncClient):
    """A member-role user gets 403 when trying to create an API key."""
    reg = await _register(client, _REGISTER_A)
    admin_token = reg["access_token"]

    # Invite a member
    invite_res = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "member@acme-api.example.com",
            "full_name": "Plain Member",
            "role": "analyst",
            "password": "memberpassword1",
        },
        headers=_auth(admin_token),
    )
    assert invite_res.status_code == 201, invite_res.text

    # Login as member
    login_res = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "member@acme-api.example.com",
            "password": "memberpassword1",
        },
    )
    assert login_res.status_code == 200, login_res.text
    member_token = login_res.json()["access_token"]

    # Member tries to create an API key
    res = await client.post(
        "/api/v1/api-keys",
        json={"name": "Member Key"},
        headers=_auth(member_token),
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_workspace_isolation(client: AsyncClient):
    """Workspace A key cannot see workspace B's data (findings list is empty for A)."""
    reg_a = await _register(client, _REGISTER_A)
    token_a = reg_a["access_token"]

    reg_b = await _register(client, _REGISTER_B)
    token_b = reg_b["access_token"]

    created_a = await _create_api_key(client, token_a, "WS A Key")
    raw_key_a = created_a["raw_key"]

    # workspace A's key only sees workspace A's api-keys list
    res_a = await client.get("/api/v1/api-keys", headers=_auth(raw_key_a))
    assert res_a.status_code == 200, res_a.text
    items_a = res_a.json()

    # Create a key for workspace B
    created_b = await _create_api_key(client, token_b, "WS B Key")

    # Workspace A key should NOT see workspace B's key
    res_a2 = await client.get("/api/v1/api-keys", headers=_auth(raw_key_a))
    assert res_a2.status_code == 200, res_a2.text
    ids_seen_by_a = [k["id"] for k in res_a2.json()]
    assert created_b["id"] not in ids_seen_by_a


@pytest.mark.asyncio
async def test_invalid_key_returns_401(client: AsyncClient):
    """GET /me with 'sk-garbage' → 401."""
    res = await client.get(
        "/api/v1/auth/me", headers=_auth("sk-totallybogusandnotreal12345")
    )
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_expired_key_rejected(client: AsyncClient):
    """Create key with expires_at=yesterday → use → 401."""
    reg = await _register(client, _REGISTER_A)
    token = reg["access_token"]

    yesterday = datetime.now(UTC) - timedelta(days=1)
    created = await _create_api_key(client, token, "Expired Key", expires_at=yesterday)
    raw_key = created["raw_key"]

    res = await client.get("/api/v1/auth/me", headers=_auth(raw_key))
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_list_shows_revoked_keys(client: AsyncClient):
    """Create, revoke → GET /api-keys → key appears with is_active=False."""
    reg = await _register(client, _REGISTER_A)
    token = reg["access_token"]

    created = await _create_api_key(client, token, "Revoke List Test")
    key_id = created["id"]

    # Revoke
    res = await client.delete(
        f"/api/v1/api-keys/{key_id}", headers=_auth(token)
    )
    assert res.status_code == 204, res.text

    # List should still show the key with is_active=False
    res = await client.get("/api/v1/api-keys", headers=_auth(token))
    assert res.status_code == 200, res.text
    items = res.json()
    revoked = next((k for k in items if k["id"] == key_id), None)
    assert revoked is not None
    assert revoked["is_active"] is False
