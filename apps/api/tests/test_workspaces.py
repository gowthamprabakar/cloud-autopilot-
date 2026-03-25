"""
Phase 1 workspace tests — list, create, get, update (tenant-scoped).
"""

import pytest
from httpx import AsyncClient

REGISTER_PAYLOAD = {
    "tenant_name": "Test Corp",
    "tenant_slug": "test-corp",
    "workspace_name": "Default",
    "email": "owner@test.com",
    "password": "password1234",
    "full_name": "Test Owner",
    "plan": "baseline",
}


async def _register_and_token(client: AsyncClient) -> str:
    res = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_list_workspaces_returns_default(client: AsyncClient):
    token = await _register_and_token(client)
    res = await client.get(
        "/api/v1/workspaces",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "Default"


@pytest.mark.asyncio
async def test_create_workspace(client: AsyncClient):
    token = await _register_and_token(client)
    res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Staging", "slug": "staging"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Staging"
    assert data["slug"] == "staging"


@pytest.mark.asyncio
async def test_create_workspace_duplicate_slug_returns_409(client: AsyncClient):
    token = await _register_and_token(client)
    await client.post(
        "/api/v1/workspaces",
        json={"name": "Staging", "slug": "staging"},
        headers={"Authorization": f"Bearer {token}"},
    )
    res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Staging Again", "slug": "staging"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_update_workspace_name(client: AsyncClient):
    token = await _register_and_token(client)
    create_res = await client.post(
        "/api/v1/workspaces",
        json={"name": "Old Name", "slug": "old-name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    ws_id = create_res.json()["id"]

    res = await client.patch(
        f"/api/v1/workspaces/{ws_id}",
        json={"name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"


@pytest.mark.asyncio
async def test_workspaces_require_auth(client: AsyncClient):
    res = await client.get("/api/v1/workspaces")
    assert res.status_code == 401
