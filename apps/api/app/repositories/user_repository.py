import uuid

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email_and_tenant(
        self, email: str, tenant_id: uuid.UUID
    ) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.email == email,
                User.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Cross-tenant email lookup — only used during login (no tenant context yet)."""
        result = await self.db.execute(
            select(User).where(User.email == email, User.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def list_by_tenant(self, tenant_id: uuid.UUID) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at)
        )
        return list(result.scalars().all())

    async def email_exists_in_tenant(self, email: str, tenant_id: uuid.UUID) -> bool:
        return await self.get_by_email_and_tenant(email, tenant_id) is not None

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.workspace_id == workspace_id, User.is_active.is_(True))
            .order_by(User.created_at)
        )
        return list(result.scalars().all())
