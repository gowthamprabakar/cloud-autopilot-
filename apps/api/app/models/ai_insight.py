"""
AiInsight — AI-generated summary for a canonical finding.

Design rules (AI Safe Layer):
- AI never sets risk_score, severity, or compliance state.
- All fields are AUGMENTATION ONLY — displayed alongside, never replacing,
  authoritative backend-computed fields.
- Idempotency: unique on (finding_id, prompt_template_id, input_context_hash).
- generation_status: pending → completed | failed (set by ai_summarize_job).
"""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class AiInsight(Base, UUIDPKMixin, TimestampMixin):
    """AI-generated augmentation for a CanonicalFinding."""
    __tablename__ = "ai_insights"

    __table_args__ = (
        UniqueConstraint(
            "finding_id", "prompt_template_id", "input_context_hash",
            name="uq_ai_insight_idempotency",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Whitelisted prompt key from PROMPT_REGISTRY
    prompt_template_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # SHA256 of the input context used — for cache-hit detection
    input_context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Model that generated this insight
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    # generation_status: pending | completed | failed
    generation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    # Primary output — plain-English summary of the finding
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Structured list of suggested remediation actions (JSON array of strings)
    suggested_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Raw LLM JSON response (kept for audit / reprocessing)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Error message if generation failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    feedbacks: Mapped[list["AiFeedback"]] = relationship(  # type: ignore[name-defined]
        back_populates="insight", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AiInsight finding={self.finding_id} status={self.generation_status}>"
