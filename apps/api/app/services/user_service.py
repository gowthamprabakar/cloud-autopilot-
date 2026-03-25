"""
User Service — business logic for user management within a workspace.

Handles inviting users, updating roles, deactivating users,
and workspace detail retrieval/updates.
"""

import uuid

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.user import User
from app.models.workspace import Workspace
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.user import InviteUserRequest
from app.schemas.workspace import UpdateWorkspaceRequest


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        workspace_repo: WorkspaceRepository,
        audit_log_service=None,
    ) -> None:
        self._users = user_repo
        self._workspaces = workspace_repo
        self._audit = audit_log_service

    async def list_workspace_members(self, workspace_id: uuid.UUID) -> list[User]:
        return await self._users.list_by_workspace(workspace_id)

    async def get_user(self, user_id: uuid.UUID, workspace_id: uuid.UUID) -> User | None:
        """Get a single user by ID, verifying they belong to the workspace."""
        user = await self._users.get_by_id(user_id)
        if user is None or user.workspace_id != workspace_id:
            return None
        return user

    async def invite_user(
        self,
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        data: InviteUserRequest,
        actor_user_id: uuid.UUID | None = None,
        actor_email: str = "system",
    ) -> User:
        if await self._users.email_exists_in_tenant(data.email, tenant_id):
            raise ConflictError(f"Email {data.email} already exists in this tenant")

        hashed = hash_password(data.password)
        user = User(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            email=data.email,
            hashed_password=hashed,
            full_name=data.full_name,
            role=data.role,
            is_active=True,
        )
        created = await self._users.create(user)

        if self._audit is not None:
            try:
                await self._audit.log(
                    workspace_id=workspace_id,
                    actor_user_id=actor_user_id,
                    actor_email=actor_email,
                    action="user.invited",
                    resource_type="user",
                    resource_id=str(created.id),
                    detail={"invited_email": data.email, "role": str(data.role)},
                )
            except Exception:
                pass  # audit logging must never block the main operation

        return created

    async def update_user_role(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        new_role: UserRole,
        requesting_user_id: uuid.UUID,
        actor_email: str = "system",
    ) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None or user.workspace_id != workspace_id:
            raise NotFoundError(f"User {user_id} not found in this workspace")
        if str(user.id) == str(requesting_user_id):
            raise ForbiddenError("Cannot change your own role")

        old_role = user.role
        updated = await self._users.update_fields(user_id, role=new_role.value)

        if self._audit is not None:
            try:
                await self._audit.log(
                    workspace_id=workspace_id,
                    actor_user_id=requesting_user_id,
                    actor_email=actor_email,
                    action="user.role_changed",
                    resource_type="user",
                    resource_id=str(user_id),
                    detail={
                        "user_id": str(user_id),
                        "old_role": str(old_role),
                        "new_role": str(new_role),
                    },
                )
            except Exception:
                pass

        return updated

    async def deactivate_user(
        self,
        user_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requesting_user_id: uuid.UUID,
        actor_email: str = "system",
    ) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None or user.workspace_id != workspace_id:
            raise NotFoundError(f"User {user_id} not found in this workspace")
        if str(user.id) == str(requesting_user_id):
            raise ForbiddenError("Cannot deactivate yourself")

        user_email = user.email
        await self._users.update_fields(user_id, is_active=False)

        if self._audit is not None:
            try:
                await self._audit.log(
                    workspace_id=workspace_id,
                    actor_user_id=requesting_user_id,
                    actor_email=actor_email,
                    action="user.deactivated",
                    resource_type="user",
                    resource_id=str(user_id),
                    detail={"user_id": str(user_id), "email": user_email},
                )
            except Exception:
                pass

    async def get_workspace(self, workspace_id: uuid.UUID) -> Workspace:
        workspace = await self._workspaces.get_by_id(workspace_id)
        if workspace is None:
            raise NotFoundError(f"Workspace {workspace_id} not found")
        return workspace

    async def update_workspace(
        self,
        workspace_id: uuid.UUID,
        data: UpdateWorkspaceRequest,
    ) -> Workspace:
        fields = data.model_dump(exclude_unset=True, exclude_none=True)
        if not fields:
            return await self.get_workspace(workspace_id)
        return await self._workspaces.update_fields(workspace_id, **fields)
