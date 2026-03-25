"""
FindingIntelligence — persisted result of multi-factor causal analysis and RAG scoring.

One row per canonical finding (UNIQUE on finding_id). The row is upserted each time
the intelligence engine re-runs for that finding.
"""

import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class FindingIntelligence(Base, UUIDPKMixin, TimestampMixin):
    """
    Persisted intelligence result for a canonical finding.
    Covers three layers:
      1. Descriptive  — plain-English narrative from Ollama (or fallback templates)
      2. Causal       — multi-factor weighted root-cause analysis from CausalEngine
      3. RAG scoring  — Red/Amber/Green priority with prioritised actions
    """

    __tablename__ = "finding_intelligence"

    # ── Tenant + Finding scope ────────────────────────────────────────────────
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_findings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # ── Descriptive layer (Ollama / fallback) ────────────────────────────────
    what_is_it: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    attack_scenario: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Causal analysis (CausalEngine) ───────────────────────────────────────
    composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    primary_root_cause: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # JSON: list of serialised CausalFactor dicts
    causal_factors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # JSON: list of human-readable causal chain strings
    causal_chain: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # JSON: list of toxic-combination dicts
    toxic_combinations: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    blast_radius_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── RAG scoring ──────────────────────────────────────────────────────────
    rag_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    rag_composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rag_primary_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    sla_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    escalation_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # JSON: list of stakeholder strings
    stakeholders: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # ── Prioritised actions ───────────────────────────────────────────────────
    # JSON: list of PrioritizedAction dicts (RED / immediate)
    immediate_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # JSON: list of PrioritizedAction dicts (AMBER / sprint)
    sprint_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # JSON: list of PrioritizedAction dicts (GREEN / quarterly)
    quarterly_actions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # ── Generation metadata ──────────────────────────────────────────────────
    ollama_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fallback_used: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    # "pending" | "completed" | "failed"
    generation_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<FindingIntelligence finding={self.finding_id} "
            f"rag={self.rag_level} score={self.composite_score}>"
        )
