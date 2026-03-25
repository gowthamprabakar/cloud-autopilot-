"""
SimulationRun — top-level record for an OmniSec swarm simulation.

One row per simulation execution. Tracks overall progress, cost, and
gate results across all agents in the swarm.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class SimulationRun(Base, UUIDPKMixin, TimestampMixin):
    """
    Top-level simulation run encompassing the full swarm lifecycle.
    status: "pending" | "running" | "completed" | "failed"
    """

    __tablename__ = "simulation_runs"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # e.g. "quantum", "cspm", "ciem", etc.
    domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # "pending" | "running" | "completed" | "failed"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    agent_count: Mapped[int] = mapped_column(default=0, nullable=False)
    message_count: Mapped[int] = mapped_column(default=0, nullable=False)
    solution_count: Mapped[int] = mapped_column(default=0, nullable=False)
    gates_passed: Mapped[int] = mapped_column(default=0, nullable=False)
    gates_total: Mapped[int] = mapped_column(default=12, nullable=False)
    # 0-100
    confidence_score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    total_tokens_used: Mapped[int] = mapped_column(default=0, nullable=False)
    total_cost_usd: Mapped[float] = mapped_column(default=0.0, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON string with agent mix, topology
    sim_config: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_simrun_workspace_status", "workspace_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<SimulationRun {self.id} domain={self.domain} status={self.status}>"
