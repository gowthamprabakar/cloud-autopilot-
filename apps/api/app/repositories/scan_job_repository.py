"""
ScanJobRepository — CRUD for ScanJob records.
"""

import uuid
from datetime import datetime, UTC

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scan_job import ScanJob


class ScanJobRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        workspace_id: str,
        triggered_by: str = "manual",
        aws_account_id: str | None = None,
    ) -> ScanJob:
        job = ScanJob(
            workspace_id=uuid.UUID(workspace_id),
            aws_account_id=uuid.UUID(aws_account_id) if aws_account_id else None,
            status="running",
            triggered_by=triggered_by,
            started_at=datetime.now(UTC),
            findings_added=0,
            findings_updated=0,
            findings_total=0,
            sources_scanned=[],
            sources_failed=[],
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_latest(self, workspace_id: str) -> ScanJob | None:
        result = await self.db.execute(
            select(ScanJob)
            .where(ScanJob.workspace_id == uuid.UUID(workspace_id))
            .order_by(desc(ScanJob.started_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_history(
        self, workspace_id: str, limit: int = 20, offset: int = 0
    ) -> list[ScanJob]:
        result = await self.db.execute(
            select(ScanJob)
            .where(ScanJob.workspace_id == uuid.UUID(workspace_id))
            .order_by(desc(ScanJob.started_at))
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_running(self, workspace_id: str) -> ScanJob | None:
        result = await self.db.execute(
            select(ScanJob)
            .where(
                ScanJob.workspace_id == uuid.UUID(workspace_id),
                ScanJob.status == "running",
            )
            .order_by(desc(ScanJob.started_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
