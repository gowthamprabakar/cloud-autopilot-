"""
Notification Service — business logic for in-app notifications.

Creates and manages notifications for workspace users.
"""

import uuid

import structlog

from app.core.exceptions import NotFoundError
from app.models.notification import Notification
from app.repositories.notification_repository import NotificationRepository

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    async def create(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None,
        type: str,
        title: str,
        body: str,
        metadata_: dict | None = None,
        link_path: str | None = None,
    ) -> Notification:
        """Create a new notification for a user (or broadcast if user_id is None)."""
        notification = Notification(
            workspace_id=workspace_id,
            user_id=user_id,
            type=type,
            title=title,
            body=body,
            metadata_=metadata_,
            link_path=link_path,
        )
        notification = await self._repo.create(notification)
        logger.info(
            "notification.created",
            notification_id=str(notification.id),
            type=type,
            workspace_id=str(workspace_id),
        )
        return notification

    async def list_for_user(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        unread_only: bool = False,
    ) -> tuple[list[Notification], int]:
        """
        Return notifications for a user in a workspace.
        Returns (items, unread_count).
        """
        items = await self._repo.list_for_user(
            workspace_id=workspace_id,
            user_id=user_id,
            unread_only=unread_only,
        )
        unread_count = await self._repo.count_unread(
            workspace_id=workspace_id,
            user_id=user_id,
        )
        return items, unread_count

    async def mark_read(
        self,
        notification_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification:
        """Mark a single notification as read. Raises NotFoundError if not found or wrong owner."""
        notification = await self._repo.mark_read(notification_id, user_id)
        if notification is None:
            raise NotFoundError(f"Notification {notification_id} not found")
        return notification

    async def mark_all_read(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        """Mark all notifications for a user as read. Returns count updated."""
        count = await self._repo.mark_all_read(workspace_id, user_id)
        logger.info(
            "notification.mark_all_read",
            workspace_id=str(workspace_id),
            user_id=str(user_id),
            count=count,
        )
        return count
