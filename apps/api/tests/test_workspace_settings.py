"""
Workspace Settings tests — Sprint 12.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import UserRole

# ── Shared payloads ──────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Settings Corp",
    "tenant_slug": "settings-corp",
    "workspace_name": "Production",
    "email": "admin@settings.example.com",
    "password": "securepw123",
    "full_name": "Settings Admin",
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


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_settings_returns_defaults(client: AsyncClient):
    """GET /workspace/settings returns 200 with SLA defaults."""
    token = await _get_token(client)
    res = await client.get("/api/v1/workspace/settings", headers=_auth(token))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["sla_days_critical"] == 3
    assert body["sla_days_high"] == 7
    assert body["sla_days_medium"] == 30
    assert body["sla_days_low"] == 90
    assert body["sla_days_info"] == 180
    assert body["finding_auto_close_days"] == 0
    assert "id" in body
    assert "workspace_id" in body
    assert "created_at" in body


@pytest.mark.asyncio
async def test_get_settings_creates_if_not_exist(client: AsyncClient):
    """Fresh workspace — GET auto-creates settings with defaults."""
    token = await _get_token(client)
    # First call creates
    res1 = await client.get("/api/v1/workspace/settings", headers=_auth(token))
    assert res1.status_code == 200
    settings_id_1 = res1.json()["id"]

    # Second call returns same record
    res2 = await client.get("/api/v1/workspace/settings", headers=_auth(token))
    assert res2.status_code == 200
    assert res2.json()["id"] == settings_id_1


@pytest.mark.asyncio
async def test_update_sla_days(client: AsyncClient):
    """PATCH /workspace/settings updates SLA values."""
    token = await _get_token(client)
    res = await client.patch(
        "/api/v1/workspace/settings",
        json={"sla_days_critical": 1, "sla_days_high": 5},
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["sla_days_critical"] == 1
    assert body["sla_days_high"] == 5
    # Untouched fields keep defaults
    assert body["sla_days_medium"] == 30


@pytest.mark.asyncio
async def test_non_admin_cannot_update_settings(client: AsyncClient, db_session: AsyncSession):
    """Viewer role cannot PATCH workspace settings — must get 403."""
    from app.models.user import User

    # Register as admin
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    user_id = uuid.UUID(me_res.json()["id"])

    # Downgrade role to viewer via db
    from sqlalchemy import select
    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.role = UserRole.VIEWER
    db_session.add(user)
    await db_session.commit()

    res = await client.patch(
        "/api/v1/workspace/settings",
        json={"sla_days_critical": 10},
        headers=_auth(token),
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_invalid_sla_days_422(client: AsyncClient):
    """PATCH with sla_days_critical=0 (below ge=1) → 422."""
    token = await _get_token(client)
    res = await client.patch(
        "/api/v1/workspace/settings",
        json={"sla_days_critical": 0},
        headers=_auth(token),
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_update_is_idempotent(client: AsyncClient):
    """PATCH same value twice returns 200 both times with same value."""
    token = await _get_token(client)

    payload = {"sla_days_critical": 5}

    res1 = await client.patch("/api/v1/workspace/settings", json=payload, headers=_auth(token))
    assert res1.status_code == 200
    assert res1.json()["sla_days_critical"] == 5

    res2 = await client.patch("/api/v1/workspace/settings", json=payload, headers=_auth(token))
    assert res2.status_code == 200
    assert res2.json()["sla_days_critical"] == 5
