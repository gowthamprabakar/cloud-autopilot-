"""
SwarmAgent — individual agent instance within a simulation run.

Each row represents one agent (e.g. orchestrator, scout, defender)
and tracks its memory state, token usage, and lifecycle.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class SwarmAgent(Base, UUIDPKMixin, TimestampMixin):
    """
    Individual agent within a swarm simulation.
    role: "orchestrator" | "recon" | "exploit" | "defend" | "validate" | "report"
    status: "idle" | "running" | "done" | "error" | "spawning"
    """

    __tablename__ = "swarm_agents"

    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # e.g. "ORCH-01", "SCOUT-01"
    agent_id: Mapped[str] = mapped_column(String(32), nullable=False)
    # e.g. "SwarmMaster", "PathFinder"
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # "orchestrator" | "recon" | "exploit" | "defend" | "validate" | "report"
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # "idle" | "running" | "done" | "error" | "spawning"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="idle")
    # 0-100
    progress: Mapped[int] = mapped_column(default=0, nullable=False)
    # 1-5
    autonomy_level: Mapped[int] = mapped_column(default=3, nullable=False)
    spawn_authority: Mapped[bool] = mapped_column(default=False, nullable=False)
    # The full system prompt sent to Claude
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Claude API response text
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON dict of live key-value state
    working_memory: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON list of last 6 actions
    episodic_memory: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON list of prioritized goals
    goal_stack: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON list of input sources
    perception_feeds: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index("ix_swarm_agent_simrun_role", "simulation_run_id", "role"),
    )

    def __repr__(self) -> str:
        return f"<SwarmAgent {self.agent_id} name={self.name} role={self.role} status={self.status}>"
