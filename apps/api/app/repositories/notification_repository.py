"""
Notification repository — data access for in-app notifications.

Never contains business logic — only data access.
"""

import uuid

from sqlalchemy import func, select, update

from app.models.notification import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 20,
    ) -> list[Notification]:
        """Return notifications for a user in a workspace, newest first."""
        stmt = (
            select(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_unread(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        """Count unread notifications for a user in a workspace."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        return result.scalar_one()

    async def mark_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification | None:
        """Mark a single notification as read; validates ownership. Returns updated record or None."""
        await self.db.execute(
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_read=True)
        )
        await self.db.flush()
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def mark_all_read(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> int:
        """Mark all unread notifications for a user as read. Returns count updated."""
        # Count unread first (SQLite doesn't support RETURNING in all configurations)
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        count = count_result.scalar_one()

        await self.db.execute(
            update(Notification)
            .where(
                Notification.workspace_id == workspace_id,
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True)
        )
        await self.db.flush()
        return count
