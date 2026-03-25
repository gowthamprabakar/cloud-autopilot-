"""
RevokedToken — blocklist of invalidated JWT access token JTIs.
Used to enforce logout and token rotation without relying on short expiry alone.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class RevokedToken(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    def __repr__(self) -> str:
        return f"<RevokedToken jti={self.jti} user_id={self.user_id}>"
