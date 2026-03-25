"""
Detections router — Cloud Detection & Response endpoints (Sprint 23).

GET /api/v1/detections/summary    High-level CDR stats
GET /api/v1/detections/alerts     All detection alerts
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.services.detection_service import DetectionService

router = APIRouter(prefix="/detections", tags=["detections"])


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


@router.get("/summary", summary="Detection summary stats")
async def get_detection_summary(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return await DetectionService(db).summary(workspace_id)


@router.get("/alerts", summary="All detection alerts")
async def get_detection_alerts(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    return await DetectionService(db).alerts(workspace_id)
