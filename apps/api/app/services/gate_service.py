"""
GateService — 12-Gate Validation Engine lifecycle.

Sprint 30: Creates, scores, and manages validation gates for simulation runs.
"""

from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.validation_gate import ValidationGate
from app.services.gate_parser import parse_gates, parse_confidence


GATE_DEFINITIONS = [
    {"number": 1, "name": "Cryptographic Hardening", "double_weight": True, "coverage": "both"},
    {"number": 2, "name": "Attack Surface Reduction", "double_weight": True, "coverage": "both"},
    {"number": 3, "name": "IaC Policy Correctness", "double_weight": False, "coverage": "swarm"},
    {"number": 4, "name": "Detection Completeness", "double_weight": True, "coverage": "both"},
    {"number": 5, "name": "Automated Response Speed", "double_weight": False, "coverage": "both"},
    {"number": 6, "name": "Blast Radius Containment", "double_weight": False, "coverage": "swarm"},
    {"number": 7, "name": "Lateral Movement Prevention", "double_weight": False, "coverage": "both"},
    {"number": 8, "name": "Credential Lifecycle", "double_weight": False, "coverage": "both"},
    {"number": 9, "name": "Cross-Account Coverage", "double_weight": False, "coverage": "both"},
    {"number": 10, "name": "Continuous Monitoring", "double_weight": False, "coverage": "both"},
    {"number": 11, "name": "IR Playbook Completeness", "double_weight": False, "coverage": "swarm"},
    {"number": 12, "name": "Red-Team Pass Rate", "double_weight": True, "coverage": "swarm"},
]


class GateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def initialize_gates(self, run_id: uuid.UUID) -> list[ValidationGate]:
        """Create all 12 gates in pending state for a new simulation run."""
        gates = []
        for gdef in GATE_DEFINITIONS:
            gate = ValidationGate(
                simulation_run_id=run_id,
                gate_number=gdef["number"],
                name=gdef["name"],
                state="pending",
                score=0.0,
                is_double_weight=gdef["double_weight"],
                coverage=gdef["coverage"],
            )
            self.db.add(gate)
            gates.append(gate)
        await self.db.flush()
        return gates

    async def update_from_validator_output(self, run_id: uuid.UUID, validator_output: str) -> list[ValidationGate]:
        """Parse VALID-01 output and update gate records."""
        parsed = parse_gates(validator_output)

        # Load existing gates
        result = await self.db.execute(
            select(ValidationGate)
            .where(ValidationGate.simulation_run_id == run_id)
            .order_by(ValidationGate.gate_number)
        )
        gates = list(result.scalars().all())
        gate_map = {g.gate_number: g for g in gates}

        for p in parsed:
            gate = gate_map.get(p["gate_number"])
            if gate:
                gate.state = p["state"]
                gate.score = p["score"]
                gate.evidence = p.get("evidence", "")

        await self.db.flush()
        return gates

    async def compute_confidence(self, run_id: uuid.UUID) -> float:
        """Compute weighted confidence score across all 12 gates."""
        result = await self.db.execute(
            select(ValidationGate)
            .where(ValidationGate.simulation_run_id == run_id)
        )
        gates = list(result.scalars().all())

        total_weight = 0.0
        weighted_score = 0.0
        for g in gates:
            weight = 2.0 if g.is_double_weight else 1.0
            total_weight += weight
            weighted_score += g.score * weight

        return round(weighted_score / total_weight, 2) if total_weight > 0 else 0.0

    async def get_gates(self, run_id: uuid.UUID) -> list[ValidationGate]:
        """Get all gates for a run, ordered by gate number."""
        result = await self.db.execute(
            select(ValidationGate)
            .where(ValidationGate.simulation_run_id == run_id)
            .order_by(ValidationGate.gate_number)
        )
        return list(result.scalars().all())

    async def summary(self, run_id: uuid.UUID) -> dict:
        """Return gate summary stats."""
        gates = await self.get_gates(run_id)
        return {
            "total": len(gates),
            "passed": sum(1 for g in gates if g.state == "pass"),
            "failed": sum(1 for g in gates if g.state == "fail"),
            "partial": sum(1 for g in gates if g.state == "partial"),
            "pending": sum(1 for g in gates if g.state == "pending"),
            "confidence": await self.compute_confidence(run_id),
        }
