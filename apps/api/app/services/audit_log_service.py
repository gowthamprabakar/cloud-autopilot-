"""
Audit Log Service — business logic for recording and querying audit log entries.

Every significant user or system action should be logged here for SOC2 compliance.
"""

import uuid

import structlog

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import AuditLogRepository

logger = structlog.get_logger(__name__)


class AuditLogService:
    def __init__(self, repo: AuditLogRepository) -> None:
        self._repo = repo

    async def log(
        self,
        workspace_id: uuid.UUID,
        actor_user_id: uuid.UUID | None,
        actor_email: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        detail: dict | None = None,
        ip_address: str | None = None,
    ) -> AuditLog:
        """
        Record an audit log entry. Fire-and-forget — failures are logged but
        should not block the calling operation.
        """
        entry = AuditLog(
            workspace_id=workspace_id,
            actor_user_id=actor_user_id,
            actor_email=actor_email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            detail=detail,
            ip_address=ip_address,
        )
        entry = await self._repo.create(entry)
        logger.info(
            "audit_log.created",
            action=action,
            actor_email=actor_email,
            workspace_id=str(workspace_id),
        )
        return entry

    async def list_workspace_logs(
        self,
        workspace_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        Return paginated audit log entries for a workspace.
        Returns (items, total_count).
        """
        offset = (page - 1) * page_size
        items = await self._repo.list_by_workspace(
            workspace_id=workspace_id,
            limit=page_size,
            offset=offset,
        )
        total = await self._repo.count_by_workspace(workspace_id)
        return items, total
