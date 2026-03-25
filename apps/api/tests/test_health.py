import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_liveness(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "cloud-posture-copilot-api"


@pytest.mark.asyncio
async def test_auth_register_endpoint_exists(client: AsyncClient):
    """Phase 1: verify register endpoint is mounted (empty body → 422, not 404)."""
    response = await client.post("/api/v1/auth/register", json={})
    assert response.status_code == 422
