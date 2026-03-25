"""
Webhooks router — workspace-scoped webhook destination management.

All write operations require ADMIN or SUPER_ADMIN role.
"""
import json
import uuid

import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.enums import UserRole
from app.repositories.webhook_repository import WebhookRepository
from app.schemas.webhook import WebhookCreate, WebhookCreatedResponse, WebhookResponse
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _svc(db: AsyncSession = Depends(get_db)) -> WebhookService:
    return WebhookService(repo=WebhookRepository(db))


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=list[WebhookResponse])
async def list_webhooks(
    current_user: CurrentUserDep,
    svc: WebhookService = Depends(_svc),
) -> list[WebhookResponse]:
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.list_webhooks(workspace_id)


@router.post(
    "",
    response_model=WebhookCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def create_webhook(
    req: WebhookCreate,
    current_user: CurrentUserDep,
    svc: WebhookService = Depends(_svc),
) -> WebhookCreatedResponse:
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.create(workspace_id, current_user.id, req)


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def delete_webhook(
    webhook_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: WebhookService = Depends(_svc),
) -> None:
    workspace_id = _resolve_workspace_id(current_user)
    deleted = await svc.delete(webhook_id, workspace_id)
    if not deleted:
        raise NotFoundError(f"Webhook {webhook_id} not found")


@router.post(
    "/{webhook_id}/test",
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def test_webhook(
    webhook_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a test ping to the webhook URL. Returns delivered status."""
    workspace_id = _resolve_workspace_id(current_user)
    repo = WebhookRepository(db)
    hook = await repo.get_by_workspace(webhook_id, workspace_id)
    if hook is None:
        raise NotFoundError(f"Webhook {webhook_id} not found")

    import hashlib
    import hmac as hmac_lib

    body = json.dumps(
        {"event": "webhook.test", "data": {"message": "test ping"}}, default=str
    )
    sig = "sha256=" + hmac_lib.new(
        hook.secret.encode(), body.encode(), digestmod=hashlib.sha256
    ).hexdigest()

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                hook.url,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Copilot-Signature": sig,
                    "X-Copilot-Event": "webhook.test",
                },
            )
        if resp.is_success:
            return {"delivered": True}
        return {"delivered": False, "error": f"HTTP {resp.status_code}"}
    except Exception as exc:
        return {"delivered": False, "error": str(exc)}
