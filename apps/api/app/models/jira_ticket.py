"""
JiraTicket — tracks Jira issues created from canonical findings.
One row per finding (unique constraint on finding_id).
"""
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import UUIDPKMixin, TimestampMixin


class JiraTicket(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "jira_tickets"

    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_findings.id", ondelete="CASCADE"),
        unique=True, nullable=False, index=True,
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    jira_key: Mapped[str] = mapped_column(String(50), nullable=False)
    jira_url: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<JiraTicket {self.jira_key} finding_id={self.finding_id}>"
