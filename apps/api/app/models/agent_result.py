"""
AgentResult — persisted output from any THINK layer agent run.

One record per agent invocation. Callers query by (finding_id, agent_name)
ordering by created_at DESC to get the freshest result.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class AgentResult(Base, UUIDPKMixin, TimestampMixin):
    """
    Persisted output from a THINK layer agent.
    agent_name: "triage" | "attack_path"
    status:     "completed" | "failed"
    """
    __tablename__ = "agent_results"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("canonical_findings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "triage" | "attack_path"
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # "completed" | "failed"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="completed")
    # Which model ran: "ollama/llama3" | "claude-haiku-*" | "none" etc.
    model_used: Mapped[str] = mapped_column(String(128), nullable=False, default="unknown")
    # Structured output — shape varies by agent_name
    output: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    # Error details if status == "failed"
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Latency in ms for the LLM call
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)

    __table_args__ = (
        Index("ix_ar_workspace_finding", "workspace_id", "finding_id"),
        Index("ix_ar_finding_agent", "finding_id", "agent_name"),
    )

    def __repr__(self) -> str:
        return f"<AgentResult {self.agent_name} finding={self.finding_id} status={self.status}>"
