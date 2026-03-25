"""
Workspace service — create, list, update workspaces within a tenant.

Tenant scoping is enforced here. No workspace operation is permitted
without a valid tenant_id matching the caller's JWT.
"""

import uuid

import structlog

from app.core.exceptions import ConflictError, ForbiddenError
from app.models.workspace import Workspace
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate

logger = structlog.get_logger(__name__)


class WorkspaceService:
    def __init__(self, workspace_repo: WorkspaceRepository) -> None:
        self._workspaces = workspace_repo

    async def list(self, tenant_id: uuid.UUID) -> list[WorkspaceRead]:
        workspaces = await self._workspaces.list_by_tenant(tenant_id)
        return [WorkspaceRead.model_validate(w) for w in workspaces]

    async def get(self, workspace_id: uuid.UUID, tenant_id: uuid.UUID) -> WorkspaceRead:
        workspace = await self._workspaces.get_by_id_or_raise(workspace_id)
        if workspace.tenant_id != tenant_id:
            raise ForbiddenError("Workspace does not belong to this tenant")
        return WorkspaceRead.model_validate(workspace)

    async def create(
        self, req: WorkspaceCreate, tenant_id: uuid.UUID
    ) -> WorkspaceRead:
        if await self._workspaces.slug_exists_in_tenant(req.slug, tenant_id):
            raise ConflictError(
                f"Workspace slug '{req.slug}' already exists in this tenant"
            )

        workspace = Workspace(
            tenant_id=tenant_id,
            name=req.name,
            slug=req.slug,
        )
        workspace = await self._workspaces.create(workspace)
        logger.info(
            "workspace.created",
            workspace_id=str(workspace.id),
            tenant_id=str(tenant_id),
        )
        return WorkspaceRead.model_validate(workspace)

    async def update(
        self,
        workspace_id: uuid.UUID,
        tenant_id: uuid.UUID,
        req: WorkspaceUpdate,
    ) -> WorkspaceRead:
        workspace = await self._workspaces.get_by_id_or_raise(workspace_id)
        if workspace.tenant_id != tenant_id:
            raise ForbiddenError("Workspace does not belong to this tenant")

        fields = req.model_dump(exclude_none=True)
        if fields:
            workspace = await self._workspaces.update_fields(workspace_id, **fields)

        return WorkspaceRead.model_validate(workspace)
