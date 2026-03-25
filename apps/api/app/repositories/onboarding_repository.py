"""
OnboardingRepository — data access for onboarding_progress table.
"""
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.onboarding_progress import OnboardingProgress

_ALL_STEPS = [
    "step_workspace_created",
    "step_aws_account_connected",
    "step_first_sync_complete",
    "step_team_member_invited",
    "step_sla_configured",
]


class OnboardingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create(self, workspace_id: uuid.UUID) -> OnboardingProgress:
        """Return existing progress or create with defaults (step_workspace_created=True)."""
        result = await self.db.execute(
            select(OnboardingProgress).where(
                OnboardingProgress.workspace_id == workspace_id
            )
        )
        progress = result.scalar_one_or_none()
        if progress is None:
            progress = OnboardingProgress(
                workspace_id=workspace_id,
                step_workspace_created=True,
            )
            self.db.add(progress)
            await self.db.flush()
            await self.db.refresh(progress)
        return progress

    async def mark_step(
        self, workspace_id: uuid.UUID, step_name: str, value: bool = True
    ) -> OnboardingProgress:
        """
        Mark a named step as complete (or incomplete).
        step_name: e.g. "step_aws_account_connected"
        If all steps are True after marking, set completed_at = now().
        """
        progress = await self.get_or_create(workspace_id)
        if hasattr(progress, step_name):
            setattr(progress, step_name, value)
        # Check if all steps complete
        all_done = all(getattr(progress, s, False) for s in _ALL_STEPS)
        if all_done and progress.completed_at is None:
            progress.completed_at = datetime.now(UTC)
        elif not all_done:
            progress.completed_at = None
        self.db.add(progress)
        await self.db.flush()
        await self.db.refresh(progress)
        return progress

    async def dismiss(self, workspace_id: uuid.UUID) -> OnboardingProgress:
        """Mark the onboarding wizard as dismissed."""
        progress = await self.get_or_create(workspace_id)
        progress.dismissed = True
        self.db.add(progress)
        await self.db.flush()
        await self.db.refresh(progress)
        return progress
