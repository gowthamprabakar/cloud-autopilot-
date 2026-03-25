"""
Compliance router — workspace-scoped compliance coverage stats.

All endpoints require authentication. workspace_id is scoped to
current_user.workspace_id.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.schemas.compliance import ComplianceFrameworkSummary, ComplianceStatsResponse
from app.services.compliance_service import ComplianceService

router = APIRouter(prefix="/compliance", tags=["compliance"])


def _svc(db: AsyncSession = Depends(get_db)) -> ComplianceService:
    return ComplianceService(
        canonical_repo=CanonicalFindingRepository(db),
    )


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("/stats", response_model=ComplianceStatsResponse)
async def get_compliance_stats(
    current_user: CurrentUserDep,
    svc: ComplianceService = Depends(_svc),
) -> ComplianceStatsResponse:
    workspace_id = _resolve_workspace_id(current_user)
    stats = await svc.get_compliance_stats(workspace_id)
    frameworks = [
        ComplianceFrameworkSummary(**fw) for fw in stats["frameworks"]
    ]
    return ComplianceStatsResponse(
        frameworks=frameworks,
        last_updated=stats["last_updated"],
    )
