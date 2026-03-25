"""
Onboarding Wizard API tests — Sprint 13.
"""

import pytest
from httpx import AsyncClient

# ── Shared payloads ──────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Onboarding Test Corp",
    "tenant_slug": "onboarding-test-corp",
    "workspace_name": "Production",
    "email": "admin@onboarding-test.example.com",
    "password": "securepw123",
    "full_name": "Onboarding Admin",
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
async def test_onboarding_unauthenticated_401(client: AsyncClient):
    """GET /onboarding without token → 401."""
    res = await client.get("/api/v1/onboarding")
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_get_onboarding_returns_initial_state(client: AsyncClient):
    """GET /onboarding returns initial state with 20% completion."""
    token = await _get_token(client)
    res = await client.get("/api/v1/onboarding", headers=_auth(token))
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["step_workspace_created"] is True
    assert body["step_aws_account_connected"] is False
    assert body["step_first_sync_complete"] is False
    assert body["step_team_member_invited"] is False
    assert body["step_sla_configured"] is False
    assert body["completion_percentage"] == 20
    assert body["all_complete"] is False
    assert body["dismissed"] is False
    assert body["completed_at"] is None


@pytest.mark.asyncio
async def test_onboarding_created_on_first_access(client: AsyncClient):
    """Fresh workspace GET /onboarding auto-creates → 200."""
    token = await _get_token(client)
    # First call auto-creates the record
    res1 = await client.get("/api/v1/onboarding", headers=_auth(token))
    assert res1.status_code == 200
    workspace_id_1 = res1.json()["workspace_id"]

    # Second call returns same record for same workspace
    res2 = await client.get("/api/v1/onboarding", headers=_auth(token))
    assert res2.status_code == 200
    assert res2.json()["workspace_id"] == workspace_id_1


@pytest.mark.asyncio
async def test_dismiss_onboarding(client: AsyncClient):
    """POST /onboarding/dismiss sets dismissed=True."""
    token = await _get_token(client)

    # Dismiss
    res = await client.post("/api/v1/onboarding/dismiss", headers=_auth(token))
    assert res.status_code == 200, res.text
    assert res.json()["dismissed"] is True

    # GET still returns dismissed=True
    res2 = await client.get("/api/v1/onboarding", headers=_auth(token))
    assert res2.status_code == 200
    assert res2.json()["dismissed"] is True


@pytest.mark.asyncio
async def test_mark_step_manually(client: AsyncClient):
    """POST /onboarding/mark/aws_account_connected → step marked, 40%."""
    token = await _get_token(client)

    res = await client.post(
        "/api/v1/onboarding/mark/aws_account_connected",
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["step_aws_account_connected"] is True
    assert body["completion_percentage"] == 40  # 2/5 steps

    # Verify via GET
    res2 = await client.get("/api/v1/onboarding", headers=_auth(token))
    assert res2.json()["step_aws_account_connected"] is True


@pytest.mark.asyncio
async def test_completion_percentage_calculation(client: AsyncClient):
    """Mark 3 of 4 remaining steps (workspace_created is always True) → 80% completion."""
    token = await _get_token(client)

    # step_workspace_created is already True by default (1/5 = 20%)
    # marking 3 more brings us to 4/5 = 80%
    steps = [
        "aws_account_connected",
        "first_sync_complete",
        "team_member_invited",
    ]
    for step in steps:
        res = await client.post(
            f"/api/v1/onboarding/mark/{step}",
            headers=_auth(token),
        )
        assert res.status_code == 200, res.text

    res = await client.get("/api/v1/onboarding", headers=_auth(token))
    body = res.json()
    assert body["completion_percentage"] == 80
    assert body["all_complete"] is False


@pytest.mark.asyncio
async def test_all_steps_complete_sets_completed_at(client: AsyncClient):
    """Mark all steps → completed_at is not None."""
    token = await _get_token(client)

    steps = [
        "aws_account_connected",
        "first_sync_complete",
        "team_member_invited",
        "sla_configured",
    ]
    for step in steps:
        res = await client.post(
            f"/api/v1/onboarding/mark/{step}",
            headers=_auth(token),
        )
        assert res.status_code == 200, res.text

    res = await client.get("/api/v1/onboarding", headers=_auth(token))
    body = res.json()
    assert body["all_complete"] is True
    assert body["completion_percentage"] == 100
    assert body["completed_at"] is not None
