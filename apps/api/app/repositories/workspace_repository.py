import uuid

from sqlalchemy import select

from app.models.workspace import Workspace
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[Workspace]:
        result = await self.db.execute(
            select(Workspace)
            .where(Workspace.tenant_id == tenant_id, Workspace.is_active.is_(True))
            .order_by(Workspace.created_at)
        )
        return list(result.scalars().all())

    async def get_by_slug_and_tenant(
        self, slug: str, tenant_id: uuid.UUID
    ) -> Workspace | None:
        result = await self.db.execute(
            select(Workspace).where(
                Workspace.slug == slug,
                Workspace.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def slug_exists_in_tenant(self, slug: str, tenant_id: uuid.UUID) -> bool:
        return await self.get_by_slug_and_tenant(slug, tenant_id) is not None
