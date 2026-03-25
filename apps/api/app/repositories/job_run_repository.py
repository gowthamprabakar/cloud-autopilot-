"""
Job Run Repository — data access for job_runs table.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.models.enums import JobRunStatus
from app.models.job_run import JobRun
from app.repositories.base import BaseRepository


class JobRunRepository(BaseRepository[JobRun]):
    model = JobRun

    async def list_by_aws_account(
        self, aws_account_id: uuid.UUID, limit: int = 20
    ) -> list[JobRun]:
        result = await self.db.execute(
            select(JobRun)
            .where(JobRun.aws_account_id == aws_account_id)
            .order_by(JobRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_by_workspace(
        self, workspace_id: uuid.UUID, limit: int = 50
    ) -> list[JobRun]:
        result = await self.db.execute(
            select(JobRun)
            .where(JobRun.workspace_id == workspace_id)
            .order_by(JobRun.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_running(self, job_run_id: uuid.UUID) -> JobRun:
        return await self.update_fields(
            job_run_id,
            status=JobRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

    async def mark_completed(
        self,
        job_run_id: uuid.UUID,
        progress_detail: dict,
    ) -> JobRun:
        return await self.update_fields(
            job_run_id,
            status=JobRunStatus.COMPLETED,
            finished_at=datetime.now(UTC),
            progress_detail=progress_detail,
        )

    async def mark_failed(
        self,
        job_run_id: uuid.UUID,
        error_message: str,
        progress_detail: dict | None = None,
    ) -> JobRun:
        fields: dict = {
            "status": JobRunStatus.FAILED,
            "finished_at": datetime.now(UTC),
            "error_message": error_message,
        }
        if progress_detail is not None:
            fields["progress_detail"] = progress_detail
        return await self.update_fields(job_run_id, **fields)
