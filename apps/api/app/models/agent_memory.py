"""
AgentMemory — Zep-compatible agent memory persistence model.

Sprint 31: Provides persistent, queryable memory store for OmniSec swarm agents.
Memory types:
  - working:    Live key-value state during simulation (short-term)
  - episodic:   Historical actions and outcomes (medium-term, FIFO bounded)
  - semantic:   Domain knowledge and learned patterns (long-term)
  - procedural: Reusable strategies and playbooks (permanent)
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class AgentMemory(Base, UUIDPKMixin, TimestampMixin):
    """
    Single memory entry for an OmniSec swarm agent.

    Composite natural key: (workspace_id, agent_id, memory_type, key).
    Supports relevance decay, access-count reinforcement, and TTL eviction.
    """

    __tablename__ = "agent_memories"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Logical agent identifier, e.g. "ORCH-01", "SCOUT-03"
    agent_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # "working" | "episodic" | "semantic" | "procedural"
    memory_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    # Memory key — unique within (workspace, agent, type)
    key: Mapped[str] = mapped_column(String(256), nullable=False)
    # JSON-serialized value
    value: Mapped[str] = mapped_column(Text, nullable=False)
    # 0.0–1.0, decays over time via half-life function
    relevance_score: Mapped[float] = mapped_column(default=1.0, nullable=False)
    # Incremented on each recall — frequently accessed memories resist decay
    access_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    # TTL-based eviction: working memories auto-expire after simulation ends
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    # Optional link to a specific simulation run
    simulation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Additional context (JSON string)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        # Fast lookup by natural key
        Index(
            "ix_agentmem_workspace_agent_type_key",
            "workspace_id",
            "agent_id",
            "memory_type",
            "key",
            unique=True,
        ),
        # Recall queries: filter by workspace + agent + type, order by relevance
        Index(
            "ix_agentmem_recall",
            "workspace_id",
            "agent_id",
            "memory_type",
            "relevance_score",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AgentMemory {self.agent_id} "
            f"type={self.memory_type} key={self.key!r} "
            f"relevance={self.relevance_score:.2f}>"
        )
