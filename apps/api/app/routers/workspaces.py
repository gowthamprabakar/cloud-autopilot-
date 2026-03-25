"""
Workspaces router — tenant-scoped CRUD.

All endpoints require authentication. Tenant scoping is enforced
by the service layer using current_user.tenant_id.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import (
    UpdateWorkspaceRequest,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.user_service import UserService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _workspace_service(db: AsyncSession = Depends(get_db)) -> WorkspaceService:
    return WorkspaceService(WorkspaceRepository(db))


def _user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(UserRepository(db), WorkspaceRepository(db))


@router.get("/current", response_model=WorkspaceResponse)
async def get_current_workspace(
    current_user: CurrentUserDep,
    svc: UserService = Depends(_user_service),
) -> WorkspaceResponse:
    if current_user.workspace_id is None:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("User has no workspace assigned")
    workspace = await svc.get_workspace(current_user.workspace_id)
    return WorkspaceResponse.model_validate(workspace)


@router.patch(
    "/current",
    response_model=WorkspaceResponse,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def update_current_workspace(
    req: UpdateWorkspaceRequest,
    current_user: CurrentUserDep,
    svc: UserService = Depends(_user_service),
) -> WorkspaceResponse:
    if current_user.workspace_id is None:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("User has no workspace assigned")
    workspace = await svc.update_workspace(current_user.workspace_id, req)
    return WorkspaceResponse.model_validate(workspace)


@router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    current_user: CurrentUserDep,
    svc: WorkspaceService = Depends(_workspace_service),
) -> list[WorkspaceRead]:
    return await svc.list(current_user.tenant_id)


@router.post("", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    req: WorkspaceCreate,
    current_user: CurrentUserDep,
    svc: WorkspaceService = Depends(_workspace_service),
) -> WorkspaceRead:
    return await svc.create(req, current_user.tenant_id)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
async def get_workspace(
    workspace_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: WorkspaceService = Depends(_workspace_service),
) -> WorkspaceRead:
    return await svc.get(workspace_id, current_user.tenant_id)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
async def update_workspace(
    workspace_id: uuid.UUID,
    req: WorkspaceUpdate,
    current_user: CurrentUserDep,
    svc: WorkspaceService = Depends(_workspace_service),
) -> WorkspaceRead:
    return await svc.update(workspace_id, current_user.tenant_id, req)
