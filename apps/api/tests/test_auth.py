"""
Phase 1 auth tests — register, login, /me.
"""

import pytest
from httpx import AsyncClient

REGISTER_PAYLOAD = {
    "tenant_name": "Acme Corp",
    "tenant_slug": "acme-corp",
    "workspace_name": "Production",
    "email": "admin@acme.com",
    "password": "supersecret99",
    "full_name": "Admin User",
    "plan": "baseline",
}


@pytest.mark.asyncio
async def test_register_creates_tenant_and_returns_token(client: AsyncClient):
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 201, res.text
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "tenant_id" in data
    assert "workspace_id" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_register_duplicate_slug_returns_409(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_login_returns_token(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "supersecret99"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    res = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "wrongpassword"},
    )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_user_profile(client: AsyncClient):
    reg = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = reg.json()["access_token"]

    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["email"] == "admin@acme.com"
    assert data["role"] == "super_admin"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client: AsyncClient):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401
