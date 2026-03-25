"""
Onboarding Wizard router — track and manage workspace onboarding progress.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.core.exceptions import BadRequestError, ForbiddenError
from app.models.enums import UserRole
from app.repositories.onboarding_repository import OnboardingRepository
from app.schemas.onboarding import OnboardingResponse

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

_VALID_STEPS = {
    "aws_account_connected": "step_aws_account_connected",
    "first_sync_complete": "step_first_sync_complete",
    "team_member_invited": "step_team_member_invited",
    "sla_configured": "step_sla_configured",
}


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=OnboardingResponse)
async def get_onboarding(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> OnboardingResponse:
    """Get current workspace onboarding progress (auto-creates on first access)."""
    workspace_id = _resolve_workspace_id(current_user)
    repo = OnboardingRepository(db)
    progress = await repo.get_or_create(workspace_id)
    return OnboardingResponse.model_validate(progress)


@router.post("/dismiss", response_model=OnboardingResponse)
async def dismiss_onboarding(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> OnboardingResponse:
    """Dismiss the onboarding wizard."""
    workspace_id = _resolve_workspace_id(current_user)
    repo = OnboardingRepository(db)
    progress = await repo.dismiss(workspace_id)
    return OnboardingResponse.model_validate(progress)


@router.post(
    "/mark/{step}",
    response_model=OnboardingResponse,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def mark_onboarding_step(
    step: str,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> OnboardingResponse:
    """
    Manually mark a step complete (admin only).
    step: aws_account_connected | first_sync_complete | team_member_invited | sla_configured
    """
    workspace_id = _resolve_workspace_id(current_user)
    if step not in _VALID_STEPS:
        raise BadRequestError(
            f"Invalid step '{step}'. Valid steps: {list(_VALID_STEPS.keys())}"
        )
    repo = OnboardingRepository(db)
    step_field = _VALID_STEPS[step]
    progress = await repo.mark_step(workspace_id, step_field)
    return OnboardingResponse.model_validate(progress)
