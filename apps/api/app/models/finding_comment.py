"""
FindingComment — threaded discussion/audit trail on a canonical finding.
"""
import uuid
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import UUIDPKMixin, TimestampMixin


class FindingComment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "finding_comments"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
