"""
WebhookDestination — configurable HTTP endpoints that receive signed event payloads
when findings are created or severity changes.
"""
import uuid
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDPKMixin, TimestampMixin


class WebhookDestination(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "webhook_destinations"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    # HMAC-SHA256 signing secret — generated server-side, shown once on create
    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    # JSON array of event names: ["finding.created", "finding.critical", "finding.status_changed"]
    events: Mapped[str] = mapped_column(Text, nullable=False, default='["finding.created"]')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<WebhookDestination {self.name} url={self.url[:30]}>"
