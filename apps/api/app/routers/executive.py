"""
Executive router — CISO / executive dashboard endpoints.

GET /api/v1/executive/summary   Full risk posture summary for the workspace
GET /api/v1/executive/trend     Daily finding counts for last N days (default 30)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.services.risk_score_service import RiskScoreService

router = APIRouter(prefix="/executive", tags=["executive"])


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


@router.get(
    "/summary",
    summary="Executive risk posture summary",
    description=(
        "Returns overall risk score (0–100), trend vs 30 days ago, "
        "per-severity counts, SLA compliance rates, per-account scores, "
        "and top 5 highest-risk open findings."
    ),
)
async def get_executive_summary(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = RiskScoreService(db)
    return await svc.summary(workspace_id)


@router.get(
    "/trend",
    summary="Findings trend over time",
    description="Returns daily open + new finding counts for the past N days.",
)
async def get_executive_trend(
    current_user: CurrentUserDep,
    days: Annotated[int, Query(ge=7, le=90, description="Number of days (7–90)")] = 30,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = RiskScoreService(db)
    return await svc.trend(workspace_id, days=days)
