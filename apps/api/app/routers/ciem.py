"""
CIEM router — Cloud Identity & Entitlement Management endpoints.

GET /api/v1/ciem/summary          High-level CIEM stats
GET /api/v1/ciem/entities         IAM entity inventory (roles + users)
GET /api/v1/ciem/escalation-paths Detected privilege escalation paths
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.services.ciem_service import CIEMService

router = APIRouter(prefix="/ciem", tags=["ciem"])


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


@router.get(
    "/summary",
    summary="CIEM high-level summary",
    description="Returns entity counts, escalation path counts, cross-account trust counts, and risk breakdown.",
)
async def get_ciem_summary(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return await CIEMService(db).summary(workspace_id)


@router.get(
    "/entities",
    summary="IAM entity inventory",
    description="Returns all IAM roles and users enriched with permission scope, escalation risk, and open findings.",
)
async def get_ciem_entities(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    return await CIEMService(db).entities(workspace_id)


@router.get(
    "/escalation-paths",
    summary="Privilege escalation paths",
    description="Returns detected privilege escalation paths from both graph edges and IAM findings.",
)
async def get_escalation_paths(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    return await CIEMService(db).escalation_paths(workspace_id)
