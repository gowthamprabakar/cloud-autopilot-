"""
WebhookRepository — data access for webhook_destinations table.
"""
import json
import uuid

from sqlalchemy import select

from app.models.webhook_destination import WebhookDestination
from app.repositories.base import BaseRepository


class WebhookRepository(BaseRepository[WebhookDestination]):
    model = WebhookDestination

    async def create(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID | None,
        name: str,
        url: str,
        secret: str,
        events: str,
    ) -> WebhookDestination:
        record = WebhookDestination(
            workspace_id=workspace_id,
            created_by_user_id=user_id,
            name=name,
            url=url,
            secret=secret,
            events=events,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def list_by_workspace(
        self, workspace_id: uuid.UUID
    ) -> list[WebhookDestination]:
        result = await self.db.execute(
            select(WebhookDestination)
            .where(WebhookDestination.workspace_id == workspace_id)
            .order_by(WebhookDestination.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_workspace(
        self, webhook_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> WebhookDestination | None:
        result = await self.db.execute(
            select(WebhookDestination).where(
                WebhookDestination.id == webhook_id,
                WebhookDestination.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, webhook_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        record = await self.get_by_workspace(webhook_id, workspace_id)
        if record is None:
            return False
        await self.db.delete(record)
        await self.db.flush()
        return True

    async def list_active_for_event(
        self, workspace_id: uuid.UUID, event_name: str
    ) -> list[WebhookDestination]:
        """
        Fetch all active webhooks for a workspace, then Python-filter by event_name.
        SQLite-compatible (no JSON SQL functions needed).
        """
        result = await self.db.execute(
            select(WebhookDestination).where(
                WebhookDestination.workspace_id == workspace_id,
                WebhookDestination.is_active.is_(True),
            )
        )
        hooks = list(result.scalars().all())
        return [
            h for h in hooks
            if event_name in (json.loads(h.events) if isinstance(h.events, str) else h.events)
        ]
