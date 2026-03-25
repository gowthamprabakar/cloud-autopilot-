"""
Tests for JWT revocation and refresh token rotation.

Sprint 10 — Security hardening.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ── Helpers ────────────────────────────────────────────────────────────────────

_REG_BASE = {
    "tenant_name": "Revoc Corp",
    "tenant_slug": "revoc-corp",
    "workspace_name": "Main",
    "email": "revoc@example.com",
    "password": "securepassword1",
    "full_name": "Revoc User",
}


async def _register_and_login(client: AsyncClient, suffix: str = "") -> tuple[str, str]:
    """Register a user and return (access_token, email)."""
    payload = {**_REG_BASE, "tenant_slug": f"revoc-{suffix}", "email": f"revoc{suffix}@example.com"}
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201, res.text
    token = res.json()["access_token"]
    return token, payload["email"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ──────────────────────────────────────────────────────────────────────

async def test_access_token_valid_before_logout(client: AsyncClient):
    """Token works before logout."""
    token, _ = await _register_and_login(client, "pre")
    res = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert res.status_code == 200


async def test_logout_revokes_access_token(client: AsyncClient):
    """After logout, the same access token returns 401."""
    token, _ = await _register_and_login(client, "rev1")
    # Logout using the Bearer header (so revocation captures the jti)
    out = await client.post("/api/v1/auth/logout", headers=_auth(token))
    assert out.status_code == 204
    # Same token must now be rejected
    res = await client.get("/api/v1/auth/me", headers=_auth(token))
    assert res.status_code == 401


async def test_logout_without_token_returns_401(client: AsyncClient):
    """Calling logout with no auth returns 401."""
    res = await client.post("/api/v1/auth/logout")
    assert res.status_code == 401


async def test_refresh_issues_new_access_token(client: AsyncClient):
    """
    Login sets a refresh_token cookie; calling /refresh returns a new access token.
    """
    # Use login so we can inspect cookies
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh1@example.com", "password": "securepassword1"},
    )
    # First register
    await client.post(
        "/api/v1/auth/register",
        json={
            **_REG_BASE,
            "tenant_slug": "refresh-corp1",
            "email": "refresh1@example.com",
        },
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh1@example.com", "password": "securepassword1"},
    )
    assert login_res.status_code == 200
    # httpx stores the cookie automatically
    ref_res = await client.post("/api/v1/auth/refresh")
    assert ref_res.status_code == 200
    data = ref_res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_refresh_new_token_grants_access(client: AsyncClient):
    """New access token from /refresh works for authenticated requests."""
    await client.post(
        "/api/v1/auth/register",
        json={**_REG_BASE, "tenant_slug": "refresh-corp2", "email": "refresh2@example.com"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh2@example.com", "password": "securepassword1"},
    )
    ref_res = await client.post("/api/v1/auth/refresh")
    assert ref_res.status_code == 200
    new_token = ref_res.json()["access_token"]
    me_res = await client.get("/api/v1/auth/me", headers=_auth(new_token))
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "refresh2@example.com"


async def test_refresh_rotates_token(client: AsyncClient):
    """After refresh, using the OLD refresh cookie returns 401 (rotation enforced)."""
    await client.post(
        "/api/v1/auth/register",
        json={**_REG_BASE, "tenant_slug": "refresh-corp3", "email": "refresh3@example.com"},
    )
    await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh3@example.com", "password": "securepassword1"},
    )
    # Capture the old refresh token cookie value
    old_cookie = client.cookies.get("refresh_token")
    # First refresh — rotates the token
    first_ref = await client.post("/api/v1/auth/refresh")
    assert first_ref.status_code == 200
    # Forcibly restore the OLD cookie
    if old_cookie:
        client.cookies.set("refresh_token", old_cookie)
        second_ref = await client.post("/api/v1/auth/refresh")
        assert second_ref.status_code == 401


async def test_refresh_rejects_missing_cookie(client: AsyncClient):
    """POST /refresh with no refresh_token cookie returns 401."""
    # Fresh client with no cookies
    res = await client.post("/api/v1/auth/refresh")
    assert res.status_code == 401


async def test_refresh_rejects_garbage_token(client: AsyncClient):
    """POST /refresh with garbage cookie value returns 401."""
    client.cookies.set("refresh_token", "garbage-not-a-real-token")
    res = await client.post("/api/v1/auth/refresh")
    assert res.status_code == 401


async def test_logout_revokes_all_refresh_tokens(client: AsyncClient):
    """After logout, refresh token is also invalidated."""
    await client.post(
        "/api/v1/auth/register",
        json={**_REG_BASE, "tenant_slug": "revoc-corp4", "email": "revoc4@example.com"},
    )
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "revoc4@example.com", "password": "securepassword1"},
    )
    token = login_res.json()["access_token"]
    # Store refresh cookie
    refresh_cookie = client.cookies.get("refresh_token")
    # Logout
    await client.post("/api/v1/auth/logout", headers=_auth(token))
    # Try to use the old refresh token
    if refresh_cookie:
        client.cookies.set("refresh_token", refresh_cookie)
        ref_res = await client.post("/api/v1/auth/refresh")
        assert ref_res.status_code == 401
