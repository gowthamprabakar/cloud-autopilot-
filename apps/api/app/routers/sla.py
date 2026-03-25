"""
SLA router — SLA tracking for open findings.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.workspace_settings_repository import WorkspaceSettingsRepository
from app.schemas.sla import SlaFindingResponse, SlaSummaryResponse
from app.services.sla_service import SlaService

router = APIRouter(prefix="/sla", tags=["sla"])


def _sla_service(db: AsyncSession = Depends(get_db)) -> SlaService:
    return SlaService(
        canonical_repo=CanonicalFindingRepository(db),
        settings_repo=WorkspaceSettingsRepository(db),
    )


@router.get("", response_model=list[SlaFindingResponse])
async def get_sla_findings(
    current_user: CurrentUserDep,
    status: Annotated[str | None, Query(description="Filter by SLA status: on_track, at_risk, breached")] = None,
    svc: SlaService = Depends(_sla_service),
) -> list[SlaFindingResponse]:
    """Get all open findings with SLA status. Optionally filter by status."""
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    results = await svc.get_findings_with_sla(current_user.workspace_id, status_filter=status)
    return [SlaFindingResponse.model_validate(r) for r in results]


@router.get("/summary", response_model=SlaSummaryResponse)
async def get_sla_summary(
    current_user: CurrentUserDep,
    svc: SlaService = Depends(_sla_service),
) -> SlaSummaryResponse:
    """Get SLA counts by status for dashboard widget."""
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    summary = await svc.get_sla_summary(current_user.workspace_id)
    return SlaSummaryResponse.model_validate(summary)
