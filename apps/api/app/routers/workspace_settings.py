"""
Workspace Settings router — per-workspace configuration (SLA days, etc.).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.core.exceptions import ForbiddenError
from app.models.enums import UserRole
from app.repositories.workspace_settings_repository import WorkspaceSettingsRepository
from app.schemas.workspace_settings import WorkspaceSettingsResponse, WorkspaceSettingsUpdate

router = APIRouter(prefix="/workspace/settings", tags=["workspace-settings"])


def _settings_repo(db: AsyncSession = Depends(get_db)) -> WorkspaceSettingsRepository:
    return WorkspaceSettingsRepository(db)


@router.get("", response_model=WorkspaceSettingsResponse)
async def get_workspace_settings(
    current_user: CurrentUserDep,
    repo: WorkspaceSettingsRepository = Depends(_settings_repo),
) -> WorkspaceSettingsResponse:
    """Get current workspace settings, creating defaults if they don't exist."""
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    settings = await repo.get_or_create(current_user.workspace_id)
    return WorkspaceSettingsResponse.model_validate(settings)


@router.patch(
    "",
    response_model=WorkspaceSettingsResponse,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def update_workspace_settings(
    req: WorkspaceSettingsUpdate,
    current_user: CurrentUserDep,
    repo: WorkspaceSettingsRepository = Depends(_settings_repo),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceSettingsResponse:
    """Update workspace SLA settings (admin only)."""
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    update_data = {k: v for k, v in req.model_dump().items() if v is not None}
    settings = await repo.update(current_user.workspace_id, **update_data)
    # Fire-and-forget: if SLA-related fields were updated, mark sla_configured onboarding step
    sla_fields = {"sla_days_critical", "sla_days_high", "sla_days_medium", "sla_days_low", "sla_days_info"}
    if update_data.keys() & sla_fields:
        try:
            from app.repositories.onboarding_repository import OnboardingRepository
            onboarding_repo = OnboardingRepository(db)
            await onboarding_repo.mark_step(current_user.workspace_id, "step_sla_configured")
        except Exception:
            pass
    return WorkspaceSettingsResponse.model_validate(settings)
