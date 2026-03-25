"""
Notifications router — workspace-scoped in-app notification management.

All endpoints require authentication. workspace_id is scoped to
current_user.workspace_id.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _svc(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: CurrentUserDep,
    svc: NotificationService = Depends(_svc),
    unread_only: bool = Query(default=False),
) -> NotificationListResponse:
    """List notifications for the current user in their workspace."""
    workspace_id = _resolve_workspace_id(current_user)
    items, unread_count = await svc.list_for_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
        unread_only=unread_only,
    )
    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in items],
        unread_count=unread_count,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: NotificationService = Depends(_svc),
) -> NotificationResponse:
    """Mark a single notification as read."""
    workspace_id = _resolve_workspace_id(current_user)
    notification = await svc.mark_read(
        notification_id=notification_id,
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    return NotificationResponse.model_validate(notification)


@router.post(
    "/read-all",
    status_code=status.HTTP_200_OK,
)
async def mark_all_notifications_read(
    current_user: CurrentUserDep,
    svc: NotificationService = Depends(_svc),
) -> dict:
    """Mark all notifications for the current user as read."""
    workspace_id = _resolve_workspace_id(current_user)
    count = await svc.mark_all_read(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    return {"marked_read": count}
