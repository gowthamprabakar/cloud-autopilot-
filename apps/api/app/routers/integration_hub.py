"""
Integration Hub router (Sprint 32).

GET    /api/v1/integration-hub             List all integrations
POST   /api/v1/integration-hub             Create new integration
PUT    /api/v1/integration-hub/{id}        Update integration
DELETE /api/v1/integration-hub/{id}        Delete integration
POST   /api/v1/integration-hub/{id}/test   Test connectivity
POST   /api/v1/integration-hub/dispatch    Manual event dispatch
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.services.integration_hub import IntegrationHub, VALID_TYPES

router = APIRouter(prefix="/integration-hub", tags=["integrations"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


def _integration_to_dict(i) -> dict[str, Any]:
    return {
        "id": str(i.id),
        "workspace_id": str(i.workspace_id),
        "integration_type": i.integration_type,
        "name": i.name,
        "is_enabled": i.is_enabled,
        "last_sync_at": i.last_sync_at.isoformat() if i.last_sync_at else None,
        "last_error": i.last_error,
        "event_filter": i.event_filter,
        "created_at": i.created_at.isoformat() if i.created_at else None,
        "updated_at": i.updated_at.isoformat() if i.updated_at else None,
    }


# ── Request / Response schemas ───────────────────────────────────────────────


class CreateIntegrationRequest(BaseModel):
    integration_type: str = Field(
        ..., description="One of: slack, jira, pagerduty, siem, github, gitlab"
    )
    name: str = Field(..., min_length=1, max_length=128)
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Connection details (webhook_url, api_token, etc.)",
    )
    event_filter: list[str] | None = Field(
        None,
        description="Event types to forward (empty = all)",
    )


class UpdateIntegrationRequest(BaseModel):
    name: str | None = None
    is_enabled: bool | None = None
    config: dict[str, Any] | None = None
    event_filter: list[str] | None = None


class DispatchEventRequest(BaseModel):
    event_type: str = Field(..., description="e.g. simulation.completed, gate.failed")
    payload: dict[str, Any] = Field(default_factory=dict)


# ── Routes ───────────────────────────────────────────────────────────────────


@router.get("")
async def list_integrations(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """List all integrations for the current workspace."""
    ws_id = _workspace_id(current_user)
    hub = IntegrationHub(db)
    integrations = await hub.list_integrations(ws_id)
    return {
        "items": [_integration_to_dict(i) for i in integrations],
        "total": len(integrations),
    }


@router.post("", status_code=201)
async def create_integration(
    body: CreateIntegrationRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Create a new external integration."""
    ws_id = _workspace_id(current_user)
    if body.integration_type not in VALID_TYPES:
        raise BadRequestError(
            f"Invalid type '{body.integration_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_TYPES))}"
        )
    hub = IntegrationHub(db)
    integration = await hub.create_integration(
        workspace_id=ws_id,
        integration_type=body.integration_type,
        name=body.name,
        config=body.config,
        event_filter=body.event_filter,
    )
    return _integration_to_dict(integration)


@router.put("/{integration_id}")
async def update_integration(
    integration_id: uuid.UUID,
    body: UpdateIntegrationRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing integration."""
    _workspace_id(current_user)  # ensure user has workspace
    hub = IntegrationHub(db)
    updates = body.model_dump(exclude_none=True)
    integration = await hub.update_integration(integration_id, updates)
    if not integration:
        raise NotFoundError("Integration not found")
    return _integration_to_dict(integration)


@router.delete("/{integration_id}")
async def delete_integration(
    integration_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Remove an integration."""
    _workspace_id(current_user)
    hub = IntegrationHub(db)
    deleted = await hub.delete_integration(integration_id)
    if not deleted:
        raise NotFoundError("Integration not found")
    return {"ok": True}


@router.post("/{integration_id}/test")
async def test_integration(
    integration_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Test connectivity for an integration by sending a test event."""
    _workspace_id(current_user)
    hub = IntegrationHub(db)
    result = await hub.test_integration(integration_id)
    return result


@router.post("/dispatch")
async def dispatch_event(
    body: DispatchEventRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Manually dispatch an event to all matching integrations."""
    ws_id = _workspace_id(current_user)
    hub = IntegrationHub(db)
    results = await hub.dispatch_event(ws_id, body.event_type, body.payload)
    return {
        "dispatched": len([r for r in results if r.get("ok")]),
        "failed": len([r for r in results if not r.get("ok")]),
        "results": results,
    }
