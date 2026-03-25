"""
Jira Integration tests — Sprint 13.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.services.jira_service import JiraService, _SEVERITY_TO_PRIORITY

# ── Shared payloads ──────────────────────────────────────────────────────────

REGISTER_PAYLOAD = {
    "tenant_name": "Jira Test Corp",
    "tenant_slug": "jira-test-corp",
    "workspace_name": "Production",
    "email": "admin@jira-test.example.com",
    "password": "securepw123",
    "full_name": "Jira Admin",
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


# ── Unit tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jira_severity_priority_mapping():
    """Unit test: _SEVERITY_TO_PRIORITY maps correctly."""
    assert _SEVERITY_TO_PRIORITY["critical"] == "Highest"
    assert _SEVERITY_TO_PRIORITY["high"] == "High"
    assert _SEVERITY_TO_PRIORITY["medium"] == "Medium"
    assert _SEVERITY_TO_PRIORITY["low"] == "Low"
    assert _SEVERITY_TO_PRIORITY["info"] == "Lowest"


@pytest.mark.asyncio
async def test_jira_service_test_connection_mocked():
    """JiraService.test_connection returns {ok: True} when mocked."""
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"name": "Test Project", "key": "TEST"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.jira_service.httpx.AsyncClient", return_value=mock_client):
        svc = JiraService(
            base_url="https://example.atlassian.net",
            email="user@example.com",
            api_token="token123",
            project_key="TEST",
        )
        result = await svc.test_connection()

    assert result["ok"] is True
    assert "Test Project" in result["message"]


@pytest.mark.asyncio
async def test_jira_service_create_issue_mocked():
    """JiraService.create_issue returns {key, url} when mocked."""
    mock_response = MagicMock()
    mock_response.is_success = True
    mock_response.json.return_value = {"key": "PROJ-1", "id": "10001"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    # Build a minimal mock finding
    finding = MagicMock()
    finding.id = uuid.uuid4()
    finding.severity = "high"
    finding.resource_arn = "arn:aws:s3:::my-bucket"
    finding.resource_type = "AwsS3Bucket"
    finding.description = "Bucket is public"
    finding.first_seen_at = "2026-01-01"
    finding.risk_score = 7.5
    finding.title = "Public S3 bucket"

    with patch("app.services.jira_service.httpx.AsyncClient", return_value=mock_client):
        svc = JiraService(
            base_url="https://example.atlassian.net",
            email="user@example.com",
            api_token="token123",
            project_key="PROJ",
        )
        result = await svc.create_issue(finding)

    assert result["key"] == "PROJ-1"
    assert "PROJ-1" in result["url"]
    assert "error" not in result


# ── Integration / API tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jira_unauthenticated_401(client: AsyncClient):
    """POST /integrations/jira/tickets without auth → 401."""
    res = await client.post(
        "/api/v1/integrations/jira/tickets",
        json={"finding_id": str(uuid.uuid4())},
    )
    assert res.status_code == 401, res.text


@pytest.mark.asyncio
async def test_jira_create_ticket_endpoint_no_jira_config(client: AsyncClient):
    """POST /integrations/jira/tickets with no Jira config → success=False, error set."""
    token = await _get_token(client)
    res = await client.post(
        "/api/v1/integrations/jira/tickets",
        json={"finding_id": str(uuid.uuid4())},
        headers=_auth(token),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["success"] is False
    assert "not configured" in body["error"].lower()


@pytest.mark.asyncio
async def test_jira_test_connection_endpoint_no_config(client: AsyncClient):
    """POST /integrations/jira/test-connection without config → 400."""
    token = await _get_token(client)
    res = await client.post(
        "/api/v1/integrations/jira/test-connection",
        headers=_auth(token),
    )
    assert res.status_code == 400, res.text
    assert "not configured" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_ticket_not_found(client: AsyncClient):
    """GET /integrations/jira/tickets/{random_uuid} → 404."""
    token = await _get_token(client)
    random_id = uuid.uuid4()
    res = await client.get(
        f"/api/v1/integrations/jira/tickets/{random_id}",
        headers=_auth(token),
    )
    assert res.status_code == 404, res.text
