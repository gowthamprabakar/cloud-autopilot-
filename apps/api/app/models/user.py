import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.workspace import Workspace


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # workspace_id is nullable: super_admin may span workspaces
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default=UserRole.ANALYST
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # TOTP 2FA fields
    totp_secret: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)  # Fernet-encrypted
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    totp_backup_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of hashed codes
    totp_pending: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")  # True between setup and verify

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    workspace: Mapped["Workspace | None"] = relationship(
        "Workspace", back_populates="users"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
