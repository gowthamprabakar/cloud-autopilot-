"""
FindingAssignment — tracks who is responsible for remediating a finding.
One active assignment per finding at a time (soft-replaced on reassign).
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDPKMixin, TimestampMixin


class FindingAssignment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "finding_assignments"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_findings.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    assignee_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    due_date: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    note: Mapped[str | None] = mapped_column(nullable=True)  # optional assignment note
