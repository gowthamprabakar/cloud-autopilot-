"""
SuppressionRule — workspace-scoped rule that mutes matching findings.

When the suppression job runs, findings matching any active rule
are set to status=SUPPRESSED.

Match fields are ANDed — all non-None conditions must be true.
"""
import uuid
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class SuppressionRule(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "suppression_rules"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # required justification
    # Match conditions (ANDed together, NULL = match any)
    match_title_contains: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_resource_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    match_resource_arn_contains: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_severity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    expires_at: Mapped[str | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<SuppressionRule id={self.id} name={self.name!r} active={self.is_active}>"
