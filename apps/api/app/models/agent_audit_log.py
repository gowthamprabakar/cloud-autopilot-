"""
AgentAuditLog — append-only audit trail for all THINK layer agent invocations.

Written by BaseAgent (passive observer inside execute()). Never updated after creation.
Provides full traceability: who triggered what agent, when, with what input, what was decided.
"""

import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class AgentAuditLog(Base, UUIDPKMixin, TimestampMixin):
    """One row per agent invocation — append only, never updated."""
    __tablename__ = "agent_audit_logs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # null if not associated with a specific finding (future: graph-level agents)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("canonical_findings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Who triggered: "api_user" | "scheduler" | "system"
    triggered_by: Mapped[str] = mapped_column(String(64), nullable=False)
    # SHA256 of the serialized input payload — idempotency / dedup key
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Short human-readable summary of what the agent concluded (≤ 500 chars)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_used: Mapped[str] = mapped_column(String(128), nullable=False, default="unknown")
    latency_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    __table_args__ = (
        Index("ix_aal_workspace_agent", "workspace_id", "agent_name"),
        Index("ix_aal_finding_agent", "finding_id", "agent_name"),
    )

    def __repr__(self) -> str:
        return f"<AgentAuditLog {self.agent_name} finding={self.finding_id}>"
