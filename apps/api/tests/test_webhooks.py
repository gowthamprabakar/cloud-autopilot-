"""
Webhook destination tests — Sprint 11.
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models.aws_account import AwsAccount
from app.models.canonical_finding import CanonicalFinding
from app.models.enums import (
    AwsAccountStatus,
    FindingSeverity,
    FindingSource,
    FindingStatus,
    TenantPlan,
    TenantStatus,
    WorkspaceStatus,
)
from app.models.tenant import Tenant
from app.models.workspace import Workspace

# ── Shared payloads ──────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Webhook Corp",
    "tenant_slug": "webhook-corp",
    "workspace_name": "Production",
    "email": "admin@webhook.example.com",
    "password": "securepw123",
    "full_name": "Webhook Admin",
    "plan": "baseline",
}

REGISTER_PAYLOAD_B = {
    "tenant_name": "Other Corp",
    "tenant_slug": "other-corp",
    "workspace_name": "Other WS",
    "email": "admin@other.example.com",
    "password": "securepw456",
    "full_name": "Other Admin",
    "plan": "baseline",
}

MEMBER_PAYLOAD = {
    "tenant_name": "Member Corp",
    "tenant_slug": "member-corp",
    "workspace_name": "Member WS",
    "email": "member@webhook.example.com",
    "password": "securepw789",
    "full_name": "Member User",
    "plan": "baseline",
}

WEBHOOK_CREATE = {
    "name": "My Webhook",
    "url": "https://example.com/hook",
    "events": ["finding.created"],
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
async def test_create_webhook_returns_secret_once(client: AsyncClient):
    token = await _get_token(client)
    res = await client.post(
        "/api/v1/webhooks", json=WEBHOOK_CREATE, headers=_auth(token)
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert "secret" in body
    assert len(body["secret"]) == 64  # 32-byte hex = 64 chars
    assert body["name"] == "My Webhook"
    assert body["url"] == "https://example.com/hook"
    assert body["events"] == ["finding.created"]
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_list_webhooks_no_secret(client: AsyncClient):
    token = await _get_token(client)
    # Create one
    await client.post("/api/v1/webhooks", json=WEBHOOK_CREATE, headers=_auth(token))
    # List
    res = await client.get("/api/v1/webhooks", headers=_auth(token))
    assert res.status_code == 200, res.text
    items = res.json()
    assert len(items) == 1
    assert "secret" not in items[0]
    assert items[0]["name"] == "My Webhook"


@pytest.mark.asyncio
async def test_delete_webhook(client: AsyncClient):
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/webhooks", json=WEBHOOK_CREATE, headers=_auth(token)
    )
    assert create_res.status_code == 201
    webhook_id = create_res.json()["id"]

    del_res = await client.delete(
        f"/api/v1/webhooks/{webhook_id}", headers=_auth(token)
    )
    assert del_res.status_code == 204

    list_res = await client.get("/api/v1/webhooks", headers=_auth(token))
    assert list_res.status_code == 200
    assert list_res.json() == []


@pytest.mark.asyncio
async def test_non_admin_cannot_create_webhook(client: AsyncClient, db_session):
    """Register user then lower their role to viewer, verify 403 on create."""
    from app.models.user import User
    from sqlalchemy import select

    token = await _get_token(client, MEMBER_PAYLOAD)

    # Fetch the user and set role to viewer
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    user_id = uuid.UUID(me_res.json()["id"])

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.role = "viewer"
    db_session.add(user)
    await db_session.commit()

    res = await client.post(
        "/api/v1/webhooks", json=WEBHOOK_CREATE, headers=_auth(token)
    )
    assert res.status_code == 403, res.text


@pytest.mark.asyncio
async def test_invalid_event_type_422(client: AsyncClient):
    token = await _get_token(client)
    res = await client.post(
        "/api/v1/webhooks",
        json={"name": "Bad Hook", "url": "https://example.com/hook", "events": ["invalid.event"]},
        headers=_auth(token),
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_invalid_url_422(client: AsyncClient):
    token = await _get_token(client)
    res = await client.post(
        "/api/v1/webhooks",
        json={"name": "Bad Hook", "url": "not-a-url", "events": ["finding.created"]},
        headers=_auth(token),
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_webhook_test_ping(client: AsyncClient):
    token = await _get_token(client)
    create_res = await client.post(
        "/api/v1/webhooks", json=WEBHOOK_CREATE, headers=_auth(token)
    )
    assert create_res.status_code == 201
    webhook_id = create_res.json()["id"]

    # Mock httpx.AsyncClient so no real HTTP goes out
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.routers.webhooks.httpx.AsyncClient", return_value=mock_client):
        res = await client.post(
            f"/api/v1/webhooks/{webhook_id}/test", headers=_auth(token)
        )

    assert res.status_code == 200, res.text
    assert res.json()["delivered"] is True


@pytest.mark.asyncio
async def test_workspace_isolation(client: AsyncClient):
    """Workspace A's webhook should NOT be visible to workspace B user."""
    token_a = await _get_token(client, REGISTER_PAYLOAD)
    token_b = await _get_token(
        client,
        {
            "tenant_name": "Isolated Corp B",
            "tenant_slug": "isolated-corp-b",
            "workspace_name": "WS B",
            "email": "admin@isolated-b.example.com",
            "password": "securepw456",
            "full_name": "Admin B",
            "plan": "baseline",
        },
    )

    # Create webhook in workspace A
    await client.post("/api/v1/webhooks", json=WEBHOOK_CREATE, headers=_auth(token_a))

    # Workspace B should see no webhooks
    res = await client.get("/api/v1/webhooks", headers=_auth(token_b))
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_unauthenticated_401(client: AsyncClient):
    res = await client.get("/api/v1/webhooks")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_dispatch_delivers_payload(client: AsyncClient, db_session):
    """Call service.dispatch() directly and verify httpx.AsyncClient.post is called."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.repositories.webhook_repository import WebhookRepository
    from app.services.webhook_service import WebhookService
    from app.schemas.webhook import WebhookCreate

    # Register to get a workspace
    token = await _get_token(client)
    me_res = await client.get("/api/v1/auth/me", headers=_auth(token))
    workspace_id = uuid.UUID(me_res.json()["workspace_id"])

    repo = WebhookRepository(db_session)
    import json, secrets
    secret = secrets.token_hex(32)
    await repo.create(
        workspace_id=workspace_id,
        user_id=None,
        name="Dispatch Test",
        url="https://dispatch.example.com/hook",
        secret=secret,
        events=json.dumps(["finding.created"]),
    )
    await db_session.commit()

    svc = WebhookService(repo=repo)

    mock_response = MagicMock()
    mock_response.is_success = True

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.webhook_service.httpx.AsyncClient", return_value=mock_client):
        await svc.dispatch(workspace_id, "finding.created", {"test": "data"})

    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert "X-Copilot-Signature" in call_kwargs.kwargs.get("headers", {})
    assert call_kwargs.kwargs["headers"]["X-Copilot-Event"] == "finding.created"
