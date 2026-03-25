"""
FindingAssignmentRepository — data access for finding_assignments table.
"""
import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding_assignment import FindingAssignment


class FindingAssignmentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def assign(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        assignee_user_id: uuid.UUID,
        assigned_by_user_id: uuid.UUID | None,
        due_date: datetime | None = None,
        note: str | None = None,
    ) -> FindingAssignment:
        """Deactivate any existing active assignment, then create a new one."""
        # Deactivate existing active assignments for this finding
        await self.db.execute(
            update(FindingAssignment)
            .where(
                FindingAssignment.finding_id == finding_id,
                FindingAssignment.workspace_id == workspace_id,
                FindingAssignment.is_active.is_(True),
            )
            .values(is_active=False)
        )
        await self.db.flush()

        # Create new assignment
        record = FindingAssignment(
            finding_id=finding_id,
            workspace_id=workspace_id,
            assignee_user_id=assignee_user_id,
            assigned_by_user_id=assigned_by_user_id,
            due_date=due_date,
            note=note,
            is_active=True,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_active(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> FindingAssignment | None:
        """Return the current active assignment for a finding, or None."""
        result = await self.db.execute(
            select(FindingAssignment).where(
                FindingAssignment.finding_id == finding_id,
                FindingAssignment.workspace_id == workspace_id,
                FindingAssignment.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    async def list_assigned_to_user(
        self, assignee_user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> list[FindingAssignment]:
        """Return all active assignments for a specific user (My Assignments view)."""
        result = await self.db.execute(
            select(FindingAssignment).where(
                FindingAssignment.assignee_user_id == assignee_user_id,
                FindingAssignment.workspace_id == workspace_id,
                FindingAssignment.is_active.is_(True),
            ).order_by(FindingAssignment.created_at.desc())
        )
        return list(result.scalars().all())

    async def unassign(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> bool:
        """Deactivate the active assignment. Return False if no active assignment."""
        existing = await self.get_active(finding_id, workspace_id)
        if existing is None:
            return False
        await self.db.execute(
            update(FindingAssignment)
            .where(
                FindingAssignment.finding_id == finding_id,
                FindingAssignment.workspace_id == workspace_id,
                FindingAssignment.is_active.is_(True),
            )
            .values(is_active=False)
        )
        await self.db.flush()
        return True
