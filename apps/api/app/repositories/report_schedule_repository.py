"""Repository for report schedules."""
import json
import uuid
from datetime import datetime, UTC
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.report_schedule import ReportSchedule


class ReportScheduleRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, workspace_id: str) -> ReportSchedule:
        result = await self.db.execute(
            select(ReportSchedule).where(ReportSchedule.workspace_id == workspace_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        schedule = ReportSchedule(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            enabled=False,
            frequency="weekly",
            day_of_week=1,
            recipients=json.dumps([]),
        )
        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def update(self, workspace_id: str, **kwargs) -> ReportSchedule:
        schedule = await self.get_or_create(workspace_id)
        for key, value in kwargs.items():
            if value is not None and hasattr(schedule, key):
                setattr(schedule, key, value)
        schedule.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def get_all_enabled(self) -> list[ReportSchedule]:
        result = await self.db.execute(
            select(ReportSchedule).where(ReportSchedule.enabled == True)
        )
        return list(result.scalars().all())

    async def mark_sent(self, schedule_id: str) -> None:
        result = await self.db.execute(
            select(ReportSchedule).where(ReportSchedule.id == schedule_id)
        )
        schedule = result.scalar_one_or_none()
        if schedule:
            schedule.last_sent_at = datetime.now(UTC)
            await self.db.commit()
