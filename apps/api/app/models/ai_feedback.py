"""
AiFeedback — user verdict on an AI-generated insight.

Verdicts: accepted | edited | rejected.
Enforces the mandatory human-in-the-loop feedback loop in the AI Safe Layer.
"""

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class AiFeedback(Base, UUIDPKMixin, TimestampMixin):
    """Human feedback on an AiInsight."""
    __tablename__ = "ai_feedback"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    insight_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_insights.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # accepted | edited | rejected
    verdict: Mapped[str] = mapped_column(String(16), nullable=False)
    # If verdict == "edited", the user's corrected version
    edited_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    insight: Mapped["AiInsight"] = relationship(back_populates="feedbacks")  # type: ignore[name-defined]

    def __repr__(self) -> str:
        return f"<AiFeedback insight={self.insight_id} verdict={self.verdict}>"
