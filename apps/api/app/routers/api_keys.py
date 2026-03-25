"""
API Keys router — workspace-scoped machine-to-machine access tokens.

All endpoints require authentication. workspace_id is derived from
current_user.workspace_id.  Create and revoke are admin-only.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.enums import UserRole
from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def _svc(db: AsyncSession = Depends(get_db)) -> ApiKeyService:
    return ApiKeyService(ApiKeyRepository(db))


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(
    current_user: CurrentUserDep,
    svc: ApiKeyService = Depends(_svc),
) -> list[ApiKeyResponse]:
    """List all API keys for the current workspace."""
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.list_keys(workspace_id)


@router.post(
    "",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def create_key(
    req: ApiKeyCreate,
    current_user: CurrentUserDep,
    svc: ApiKeyService = Depends(_svc),
) -> ApiKeyCreatedResponse:
    """Create a new API key. The raw key is returned ONCE — store it securely."""
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.create_key(
        workspace_id=workspace_id,
        user_id=current_user.id,
        req=req,
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def revoke_key(
    key_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: ApiKeyService = Depends(_svc),
) -> None:
    """Revoke an API key. The key will be immediately rejected on next use."""
    workspace_id = _resolve_workspace_id(current_user)
    found = await svc.revoke_key(key_id, workspace_id)
    if not found:
        raise NotFoundError(f"API key {key_id} not found in this workspace")
