"""
ValidationGate — quality gate checkpoint within a simulation.

Each simulation has up to 12 gates. Gates 1, 2, 4, and 12 are
double-weighted. Each gate tracks pass/fail state and evidence.
"""

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class ValidationGate(Base, UUIDPKMixin, TimestampMixin):
    """
    Validation gate checkpoint within a swarm simulation.
    state: "pending" | "running" | "pass" | "fail" | "partial"
    coverage: "wiz" | "swarm" | "both"
    """

    __tablename__ = "validation_gates"

    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 1-12
    gate_number: Mapped[int] = mapped_column(nullable=False)
    # e.g. "Cryptographic Hardening"
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # "pending" | "running" | "pass" | "fail" | "partial"
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    # 0-100
    score: Mapped[float] = mapped_column(default=0.0, nullable=False)
    # Explanation text
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Gates 1, 2, 4, 12 are double-weighted
    is_double_weight: Mapped[bool] = mapped_column(default=False, nullable=False)
    # "wiz" | "swarm" | "both"
    coverage: Mapped[str] = mapped_column(
        String(16), nullable=False, default="both"
    )

    __table_args__ = (
        Index("ix_vgate_simrun_num", "simulation_run_id", "gate_number", unique=True),
    )

    def __repr__(self) -> str:
        return f"<ValidationGate #{self.gate_number} {self.name} state={self.state}>"
