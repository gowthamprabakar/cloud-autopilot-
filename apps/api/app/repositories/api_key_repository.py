"""
ApiKeyRepository — data access for workspace-scoped API keys.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        workspace_id: uuid.UUID,
        created_by_user_id: uuid.UUID | None,
        name: str,
        key_prefix: str,
        key_hash: str,
        expires_at: datetime | None = None,
    ) -> ApiKey:
        """Insert new API key record."""
        record = ApiKey(
            workspace_id=workspace_id,
            created_by_user_id=created_by_user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            expires_at=expires_at,
            is_active=True,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        """Look up by SHA-256 hash. Used for authentication."""
        result = await self.db.execute(
            select(ApiKey).where(ApiKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def list_by_workspace(self, workspace_id: uuid.UUID) -> list[ApiKey]:
        """Return all active + inactive keys for a workspace (no hashes in response)."""
        result = await self.db.execute(
            select(ApiKey)
            .where(ApiKey.workspace_id == workspace_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke(self, key_id: uuid.UUID, workspace_id: uuid.UUID) -> bool:
        """Soft-delete: set is_active=False. Return False if not found."""
        result = await self.db.execute(
            select(ApiKey).where(
                ApiKey.id == key_id,
                ApiKey.workspace_id == workspace_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return False
        record.is_active = False
        await self.db.flush()
        return True

    async def touch_last_used(self, key_id: uuid.UUID) -> None:
        """Update last_used_at = now(). Fire and forget."""
        await self.db.execute(
            update(ApiKey)
            .where(ApiKey.id == key_id)
            .values(last_used_at=datetime.now(UTC))
        )
