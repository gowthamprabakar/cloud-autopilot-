"""
CommMessage — inter-agent communication log within a simulation.

Each row is a single message between agents, ordered by sequence_number
within a simulation run.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class CommMessage(Base, UUIDPKMixin, TimestampMixin):
    """
    Inter-agent message within a swarm simulation.
    message_type: "info" | "solution" | "alert" | "spawn" | "wiz"
    """

    __tablename__ = "comm_messages"

    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # e.g. "ORCH-01"
    from_agent_id: Mapped[str] = mapped_column(String(32), nullable=False)
    # e.g. "SCOUT-01" or "ALL"
    to_agent_id: Mapped[str] = mapped_column(String(32), nullable=False)
    # "info" | "solution" | "alert" | "spawn" | "wiz"
    message_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Ordering within simulation
    sequence_number: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        Index("ix_comm_simrun_seq", "simulation_run_id", "sequence_number"),
    )

    def __repr__(self) -> str:
        return f"<CommMessage #{self.sequence_number} {self.from_agent_id}->{self.to_agent_id} type={self.message_type}>"
