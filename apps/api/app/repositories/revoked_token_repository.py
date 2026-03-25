"""
RevokedTokenRepository — data access for the JWT blocklist.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.revoked_token import RevokedToken


class RevokedTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, jti: str, user_id: uuid.UUID, expires_at: datetime) -> None:
        """Insert a revoked JTI into the blocklist."""
        record = RevokedToken(
            jti=jti,
            user_id=user_id,
            expires_at=expires_at,
        )
        self.db.add(record)
        await self.db.flush()

    async def is_revoked(self, jti: str) -> bool:
        """Return True if jti exists in the revoked_tokens table."""
        result = await self.db.execute(
            select(RevokedToken).where(RevokedToken.jti == jti)
        )
        return result.scalar_one_or_none() is not None
