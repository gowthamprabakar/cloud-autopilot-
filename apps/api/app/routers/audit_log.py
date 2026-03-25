"""
Audit Log router — workspace-scoped audit log retrieval.

All endpoints require authentication. workspace_id is scoped to
current_user.workspace_id.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.repositories.audit_log_repository import AuditLogRepository
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse
from app.services.audit_log_service import AuditLogService

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


def _svc(db: AsyncSession = Depends(get_db)) -> AuditLogService:
    return AuditLogService(AuditLogRepository(db))


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: CurrentUserDep,
    svc: AuditLogService = Depends(_svc),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> AuditLogListResponse:
    """List audit log entries for the current workspace (paginated, newest first)."""
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    workspace_id = current_user.workspace_id

    items, total = await svc.list_workspace_logs(
        workspace_id=workspace_id,
        page=page,
        page_size=page_size,
    )
    pages = max(1, (total + page_size - 1) // page_size)
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(entry) for entry in items],
        total=total,
        page=page,
        pages=pages,
    )
