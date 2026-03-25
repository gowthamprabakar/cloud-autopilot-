"""Tests for scheduled report endpoints."""
import json
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_schedule_defaults(client: AsyncClient, admin_headers: dict):
    resp = await client.get("/api/v1/reports/schedule", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is False
    assert data["frequency"] == "weekly"
    assert data["day_of_week"] == 1
    assert data["recipients"] == []


@pytest.mark.asyncio
async def test_get_schedule_auto_creates(client: AsyncClient, admin_headers: dict):
    """Calling GET twice is idempotent."""
    resp1 = await client.get("/api/v1/reports/schedule", headers=admin_headers)
    resp2 = await client.get("/api/v1/reports/schedule", headers=admin_headers)
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["id"] == resp2.json()["id"]


@pytest.mark.asyncio
async def test_update_schedule(client: AsyncClient, admin_headers: dict):
    resp = await client.put(
        "/api/v1/reports/schedule",
        json={"enabled": True, "frequency": "weekly", "day_of_week": 5, "recipients": ["exec@example.com"]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["enabled"] is True
    assert data["day_of_week"] == 5
    assert "exec@example.com" in data["recipients"]


@pytest.mark.asyncio
async def test_update_schedule_invalid_frequency(client: AsyncClient, admin_headers: dict):
    resp = await client.put(
        "/api/v1/reports/schedule",
        json={"frequency": "daily"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_schedule_invalid_day(client: AsyncClient, admin_headers: dict):
    resp = await client.put(
        "/api/v1/reports/schedule",
        json={"day_of_week": 8},
        headers=admin_headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_non_admin_cannot_update_schedule(client: AsyncClient, admin_headers: dict):
    """Analyst user cannot update schedule (403)."""
    # First, get the admin's workspace to invite an analyst
    me_resp = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert me_resp.status_code == 200

    # Invite an analyst to the same workspace
    invite_resp = await client.post(
        "/api/v1/users/invite",
        json={
            "email": "analyst@schedule-test.example.com",
            "full_name": "Test Analyst",
            "role": "analyst",
            "password": "analystpassword1",
        },
        headers=admin_headers,
    )
    assert invite_resp.status_code == 201

    # Login as analyst
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "analyst@schedule-test.example.com",
            "password": "analystpassword1",
        },
    )
    assert login_resp.status_code == 200
    analyst_token = login_resp.json()["access_token"]
    analyst_headers = {"Authorization": f"Bearer {analyst_token}"}

    # Analyst should not be able to update
    resp = await client.put(
        "/api/v1/reports/schedule",
        json={"enabled": True},
        headers=analyst_headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_send_now_returns_zero_when_no_recipients(client: AsyncClient, admin_headers: dict):
    resp = await client.post("/api/v1/reports/send-now", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] == 0
    assert data["recipients"] == []
