"""
AuditLog repository — data access for audit log records.

Never contains business logic — only data access.
"""

import uuid

from sqlalchemy import func, select

from app.models.audit_log import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def list_by_workspace(
        self,
        workspace_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditLog]:
        """Return paginated audit log entries for a workspace, newest first."""
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.workspace_id == workspace_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_by_workspace(self, workspace_id: uuid.UUID) -> int:
        """Total count of audit log entries for a workspace."""
        result = await self.db.execute(
            select(func.count()).select_from(AuditLog).where(
                AuditLog.workspace_id == workspace_id
            )
        )
        return result.scalar_one()
