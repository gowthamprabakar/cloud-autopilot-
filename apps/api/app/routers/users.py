"""
Users router — workspace-scoped user management.

All endpoints require authentication. workspace_id is scoped to
current_user.workspace_id.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.models.enums import UserRole
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.user import (
    InviteUserRequest,
    UpdateUserRoleRequest,
    UserListResponse,
    UserResponse,
)
from app.services.audit_log_service import AuditLogService
from app.services.email_service import EmailService
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _svc(db: AsyncSession = Depends(get_db)) -> UserService:
    audit_svc = AuditLogService(AuditLogRepository(db))
    return UserService(UserRepository(db), WorkspaceRepository(db), audit_log_service=audit_svc)


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=UserListResponse)
async def list_users(
    current_user: CurrentUserDep,
    svc: UserService = Depends(_svc),
) -> UserListResponse:
    workspace_id = _resolve_workspace_id(current_user)
    members = await svc.list_workspace_members(workspace_id)
    return UserListResponse(
        items=[UserResponse.model_validate(m) for m in members],
        total=len(members),
    )


@router.post(
    "/invite",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def invite_user(
    req: InviteUserRequest,
    current_user: CurrentUserDep,
    svc: UserService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    workspace_id = _resolve_workspace_id(current_user)
    user = await svc.invite_user(
        workspace_id=workspace_id,
        tenant_id=current_user.tenant_id,
        data=req,
        actor_user_id=current_user.id,
        actor_email=current_user.email,
    )
    # Send invitation email (fire-and-forget; silently skipped if SMTP not configured)
    try:
        from app.services.email_templates import user_invited_email
        email_svc = EmailService()
        subject, html, text = user_invited_email(
            invitee_name=req.full_name or req.email,
            inviter_name=current_user.full_name or current_user.email,
            workspace_name="your workspace",
            login_url="/login",
            temporary_password=req.password,
        )
        await email_svc.send(req.email, subject, html, text)
    except Exception:
        pass
    # Fire-and-forget: mark team_member_invited step in onboarding
    try:
        from app.repositories.onboarding_repository import OnboardingRepository
        onboarding_repo = OnboardingRepository(db)
        await onboarding_repo.mark_step(workspace_id, "step_team_member_invited")
    except Exception:
        pass
    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: UserService = Depends(_svc),
) -> UserResponse:
    workspace_id = _resolve_workspace_id(current_user)
    from app.core.exceptions import NotFoundError
    user = await svc.get_user(user_id, workspace_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found in this workspace")
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def update_user_role(
    user_id: uuid.UUID,
    req: UpdateUserRoleRequest,
    current_user: CurrentUserDep,
    svc: UserService = Depends(_svc),
) -> UserResponse:
    workspace_id = _resolve_workspace_id(current_user)
    user = await svc.update_user_role(
        user_id=user_id,
        workspace_id=workspace_id,
        new_role=req.role,
        requesting_user_id=current_user.id,
        actor_email=current_user.email,
    )
    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def deactivate_user(
    user_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: UserService = Depends(_svc),
) -> None:
    workspace_id = _resolve_workspace_id(current_user)
    await svc.deactivate_user(
        user_id=user_id,
        workspace_id=workspace_id,
        requesting_user_id=current_user.id,
        actor_email=current_user.email,
    )
