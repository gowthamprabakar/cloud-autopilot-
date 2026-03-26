"""
Immutable audit trail for simulation events.

Sprint 34: Append-only audit entries for SOC2/ISO27001 compliance.
Each entry records a discrete event in a simulation lifecycle.
No update or delete operations are exposed — entries are immutable.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class SimulationAuditEntry(Base, UUIDPKMixin, TimestampMixin):
    """
    Immutable audit trail entry for a simulation event.

    event_type examples:
      - simulation.created, simulation.started, simulation.completed
      - agent.started, agent.completed, agent.failed
      - gate.scored, gate.passed, gate.failed
      - solution.generated, comm.message, export.requested
    """

    __tablename__ = "simulation_audit_entries"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Dot-namespaced event type, e.g. "simulation.created", "gate.scored"
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # Attribution: "user:<uuid>", "agent:ORCH-01", or "system"
    actor: Mapped[str] = mapped_column(String(256), nullable=False)
    # Human-readable action description
    action: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON blob with event-specific details (gate scores, agent config, etc.)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Client IP for user-initiated actions
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    __table_args__ = (
        Index("ix_simaudit_run_type", "simulation_run_id", "event_type"),
        Index("ix_simaudit_workspace_created", "workspace_id", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<SimulationAuditEntry {self.id} "
            f"type={self.event_type} actor={self.actor}>"
        )
