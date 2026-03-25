"""AiFeedback repository — workspace-scoped CRUD."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_feedback import AiFeedback


class AiFeedbackRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, feedback: AiFeedback) -> AiFeedback:
        self._db.add(feedback)
        await self._db.flush()
        await self._db.refresh(feedback)
        return feedback

    async def list_for_insight(
        self, insight_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[AiFeedback]:
        result = await self._db.execute(
            select(AiFeedback).where(
                AiFeedback.insight_id == insight_id,
                AiFeedback.workspace_id == workspace_id,
            ).order_by(AiFeedback.created_at.desc())
        )
        return list(result.scalars().all())
