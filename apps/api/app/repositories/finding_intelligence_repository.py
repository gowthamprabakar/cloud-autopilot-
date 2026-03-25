"""
FindingIntelligenceRepository — data access for finding_intelligence table.

All writes go through upsert() so there is always exactly one row per finding.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.models.finding_intelligence import FindingIntelligence
from app.repositories.base import BaseRepository


class FindingIntelligenceRepository(BaseRepository[FindingIntelligence]):
    model = FindingIntelligence

    # ── Lookup ────────────────────────────────────────────────────────────────

    async def get_by_finding_id(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> FindingIntelligence | None:
        result = await self.db.execute(
            select(FindingIntelligence).where(
                FindingIntelligence.finding_id == finding_id,
                FindingIntelligence.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    # ── List / paginate ───────────────────────────────────────────────────────

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        rag_level: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[FindingIntelligence]:
        q = select(FindingIntelligence).where(
            FindingIntelligence.workspace_id == workspace_id
        )
        if rag_level is not None:
            q = q.where(FindingIntelligence.rag_level == rag_level)
        q = (
            q.order_by(
                FindingIntelligence.rag_composite_score.desc().nullslast(),
                FindingIntelligence.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ── Aggregate counts ──────────────────────────────────────────────────────

    async def count_by_rag(self, workspace_id: uuid.UUID) -> dict[str, int]:
        """Return {"RED": n, "AMBER": n, "GREEN": n} for the workspace."""
        result = await self.db.execute(
            select(FindingIntelligence.rag_level, func.count())
            .where(
                FindingIntelligence.workspace_id == workspace_id,
                FindingIntelligence.rag_level.isnot(None),
                FindingIntelligence.generation_status == "completed",
            )
            .group_by(FindingIntelligence.rag_level)
        )
        rows = result.all()
        counts: dict[str, int] = {"RED": 0, "AMBER": 0, "GREEN": 0}
        for level, cnt in rows:
            if level in counts:
                counts[level] = cnt
        return counts

    async def count_by_workspace(self, workspace_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).where(
                FindingIntelligence.workspace_id == workspace_id,
                FindingIntelligence.generation_status == "completed",
            )
        )
        return result.scalar_one() or 0

    # ── Upsert ────────────────────────────────────────────────────────────────

    async def upsert(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        **fields: Any,
    ) -> FindingIntelligence:
        """
        Insert or update the intelligence row for this finding.
        Because finding_id has a UNIQUE constraint we can either:
          - Create fresh if not exists
          - Update all provided fields if exists
        This implementation fetches first then creates/updates which works
        identically on SQLite and PostgreSQL without dialect-specific INSERT …
        ON CONFLICT.
        """
        existing = await self.get_by_finding_id(finding_id, workspace_id)
        if existing is None:
            obj = FindingIntelligence(
                finding_id=finding_id,
                workspace_id=workspace_id,
                **fields,
            )
            self.db.add(obj)
            await self.db.flush()
            await self.db.refresh(obj)
            return obj
        else:
            return await self.update_fields(existing.id, **fields)
