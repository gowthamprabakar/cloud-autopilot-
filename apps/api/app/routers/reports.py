"""Reports router — executive summary and data export."""

import json
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, get_current_user, require_roles
from app.core.exceptions import ForbiddenError
from app.models.enums import UserRole
from app.repositories.aws_account_repository import AwsAccountRepository
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.report_schedule_repository import ReportScheduleRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.report import ExecutiveSummaryResponse
from app.schemas.report_schedule import ReportScheduleResponse, ReportScheduleUpdate, SendNowResponse
from app.services.digest_service import DigestService
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def _svc(db: AsyncSession = Depends(get_db)) -> ReportService:
    return ReportService(
        finding_repo=CanonicalFindingRepository(db),
        account_repo=AwsAccountRepository(db),
        workspace_repo=WorkspaceRepository(db),
    )


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("/executive-summary", response_model=ExecutiveSummaryResponse)
async def executive_summary(
    current_user: CurrentUserDep,
    svc: ReportService = Depends(_svc),
) -> ExecutiveSummaryResponse:
    """Generate executive summary report for the workspace."""
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.executive_summary(workspace_id)


@router.get("/schedule", response_model=ReportScheduleResponse)
async def get_schedule(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> ReportScheduleResponse:
    """Get current report schedule for the workspace."""
    repo = ReportScheduleRepository(db)
    schedule = await repo.get_or_create(str(current_user.workspace_id))
    return ReportScheduleResponse.from_orm_model(schedule)


@router.put(
    "/schedule",
    response_model=ReportScheduleResponse,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def update_schedule(
    body: ReportScheduleUpdate,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> ReportScheduleResponse:
    """Update report schedule. Admin only."""
    repo = ReportScheduleRepository(db)
    update_kwargs = {}
    if body.enabled is not None:
        update_kwargs["enabled"] = body.enabled
    if body.frequency is not None:
        update_kwargs["frequency"] = body.frequency
    if body.day_of_week is not None:
        update_kwargs["day_of_week"] = body.day_of_week
    if body.recipients is not None:
        update_kwargs["recipients"] = json.dumps(body.recipients)
    schedule = await repo.update(str(current_user.workspace_id), **update_kwargs)
    return ReportScheduleResponse.from_orm_model(schedule)


@router.post(
    "/send-now",
    response_model=SendNowResponse,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def send_now(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> SendNowResponse:
    """Trigger immediate digest send to configured recipients. Admin only."""
    repo = ReportScheduleRepository(db)
    schedule = await repo.get_or_create(str(current_user.workspace_id))
    recipients = []
    if schedule.recipients:
        try:
            recipients = json.loads(schedule.recipients)
        except Exception:
            recipients = []

    svc = DigestService(db)
    sent = await svc.send_digest(str(current_user.workspace_id), recipients)
    await repo.mark_sent(schedule.id)

    return SendNowResponse(sent=sent, workspace_id=str(current_user.workspace_id), recipients=recipients)
