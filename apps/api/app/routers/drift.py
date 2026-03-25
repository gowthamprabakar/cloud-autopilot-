"""
Drift detection & Root Cause v2 router (Sprint 28).

GET /api/v1/drift/summary      Drift detection summary
GET /api/v1/drift/recurrences  Recurring findings
GET /api/v1/drift/signals      Drift signals (severity changes)
GET /api/v1/drift/clusters     Root cause clusters
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.services.drift_service import DriftService

router = APIRouter(prefix="/drift", tags=["drift"])


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


@router.get(
    "/summary",
    summary="Drift detection summary",
    description=(
        "Returns counts of recurrences, drift signals, and root cause clusters "
        "for the workspace."
    ),
)
async def get_drift_summary(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = DriftService(db)
    return await svc.summary(workspace_id)


@router.get(
    "/recurrences",
    summary="Recurring findings",
    description=(
        "Finds findings that were resolved then reopened — same fingerprint "
        "appears with both resolved_at set AND status=open."
    ),
)
async def get_recurrences(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    svc = DriftService(db)
    return await svc.recurrences(workspace_id)


@router.get(
    "/signals",
    summary="Drift signals",
    description=(
        "Detects resources with severity changes over time — "
        "resource_arn with multiple distinct severity levels."
    ),
)
async def get_drift_signals(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    svc = DriftService(db)
    return await svc.drift_signals(workspace_id)


@router.get(
    "/clusters",
    summary="Root cause clusters",
    description=(
        "Groups open findings by shared resource_type + title pattern "
        "to surface systemic root causes."
    ),
)
async def get_root_cause_clusters(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    svc = DriftService(db)
    return await svc.root_cause_clusters(workspace_id)
