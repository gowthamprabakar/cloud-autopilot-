"""AiInsight repository — workspace-scoped CRUD."""

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_insight import AiInsight


class AiInsightRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, insight_id: uuid.UUID, workspace_id: uuid.UUID) -> AiInsight | None:
        result = await self._db.execute(
            select(AiInsight).where(
                AiInsight.id == insight_id,
                AiInsight.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_for_finding(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        prompt_template_id: str | None = None,
    ) -> AiInsight | None:
        """Return the most recent completed insight for a finding."""
        stmt = select(AiInsight).where(
            AiInsight.finding_id == finding_id,
            AiInsight.workspace_id == workspace_id,
            AiInsight.generation_status == "completed",
        )
        if prompt_template_id:
            stmt = stmt.where(AiInsight.prompt_template_id == prompt_template_id)
        stmt = stmt.order_by(AiInsight.created_at.desc()).limit(1)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_hash(
        self,
        finding_id: uuid.UUID,
        prompt_template_id: str,
        input_context_hash: str,
    ) -> AiInsight | None:
        """Idempotency check — return existing insight if same hash."""
        result = await self._db.execute(
            select(AiInsight).where(
                AiInsight.finding_id == finding_id,
                AiInsight.prompt_template_id == prompt_template_id,
                AiInsight.input_context_hash == input_context_hash,
            )
        )
        return result.scalar_one_or_none()

    async def create(self, insight: AiInsight) -> AiInsight:
        self._db.add(insight)
        await self._db.flush()
        await self._db.refresh(insight)
        return insight

    async def update_completed(
        self,
        insight_id: uuid.UUID,
        summary: str,
        suggested_actions: list[str],
        raw_response: str,
    ) -> None:
        await self._db.execute(
            update(AiInsight)
            .where(AiInsight.id == insight_id)
            .values(
                generation_status="completed",
                summary=summary,
                suggested_actions=suggested_actions,
                raw_response=raw_response,
            )
        )

    async def update_failed(self, insight_id: uuid.UUID, error_message: str) -> None:
        await self._db.execute(
            update(AiInsight)
            .where(AiInsight.id == insight_id)
            .values(generation_status="failed", error_message=error_message)
        )
