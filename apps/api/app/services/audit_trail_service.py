"""
AuditTrailService — Immutable audit logging for compliance.

Sprint 34: Records all simulation events for SOC2/ISO27001 compliance.
Entries cannot be modified or deleted (append-only).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation_audit import SimulationAuditEntry


class AuditTrailService:
    """Append-only audit trail for simulation lifecycle events."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Write ────────────────────────────────────────────────────────────────

    async def log_event(
        self,
        workspace_id: uuid.UUID,
        run_id: uuid.UUID,
        event_type: str,
        actor: str,
        action: str,
        details: dict[str, Any] | None = None,
        ip: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Append an audit entry. Immutable — no update path exists.

        Returns the created entry as a dict for callers that need confirmation.
        """
        entry = SimulationAuditEntry(
            workspace_id=workspace_id,
            simulation_run_id=run_id,
            user_id=user_id,
            event_type=event_type,
            actor=actor,
            action=action,
            details_json=json.dumps(details) if details else None,
            ip_address=ip,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return self._entry_to_dict(entry)

    # ── Reads ────────────────────────────────────────────────────────────────

    async def get_trail(
        self,
        run_id: uuid.UUID,
        event_type: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Get audit trail for a simulation run, optionally filtered by event type."""
        conditions = [SimulationAuditEntry.simulation_run_id == run_id]
        if event_type:
            conditions.append(SimulationAuditEntry.event_type == event_type)

        stmt = (
            select(SimulationAuditEntry)
            .where(and_(*conditions))
            .order_by(desc(SimulationAuditEntry.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [self._entry_to_dict(row) for row in result.scalars().all()]

    async def get_workspace_trail(
        self,
        workspace_id: uuid.UUID,
        days: int = 30,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Get all audit entries for a workspace within a time window."""
        cutoff = datetime.now(UTC) - timedelta(days=days)
        stmt = (
            select(SimulationAuditEntry)
            .where(
                and_(
                    SimulationAuditEntry.workspace_id == workspace_id,
                    SimulationAuditEntry.created_at >= cutoff,
                )
            )
            .order_by(desc(SimulationAuditEntry.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [self._entry_to_dict(row) for row in result.scalars().all()]

    async def export_compliance_report(
        self,
        workspace_id: uuid.UUID,
        run_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        """
        Export audit trail in compliance-ready format (SOC2/ISO27001).

        Includes: event timeline, actor attributions, gate decisions,
        data access log, and summary statistics.
        """
        conditions = [SimulationAuditEntry.workspace_id == workspace_id]
        if run_id:
            conditions.append(SimulationAuditEntry.simulation_run_id == run_id)

        stmt = (
            select(SimulationAuditEntry)
            .where(and_(*conditions))
            .order_by(SimulationAuditEntry.created_at)
        )
        result = await self.db.execute(stmt)
        entries = result.scalars().all()

        # Categorise entries for compliance sections
        gate_decisions: list[dict] = []
        actor_actions: dict[str, int] = {}
        event_type_counts: dict[str, int] = {}
        timeline: list[dict] = []

        for entry in entries:
            d = self._entry_to_dict(entry)
            timeline.append(d)

            # Track actor activity
            actor_actions[entry.actor] = actor_actions.get(entry.actor, 0) + 1

            # Track event type distribution
            event_type_counts[entry.event_type] = (
                event_type_counts.get(entry.event_type, 0) + 1
            )

            # Collect gate decisions
            if entry.event_type.startswith("gate."):
                gate_decisions.append(d)

        return {
            "report_type": "SOC2/ISO27001 Compliance Audit Trail",
            "generated_at": datetime.now(UTC).isoformat(),
            "workspace_id": str(workspace_id),
            "simulation_run_id": str(run_id) if run_id else "all",
            "summary": {
                "total_events": len(entries),
                "unique_actors": len(actor_actions),
                "event_type_distribution": event_type_counts,
                "actor_activity": actor_actions,
                "gate_decisions_count": len(gate_decisions),
            },
            "gate_decisions": gate_decisions,
            "timeline": timeline,
        }

    async def search_trail(
        self,
        workspace_id: uuid.UUID,
        query: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search audit entries by action text or actor."""
        pattern = f"%{query}%"
        stmt = (
            select(SimulationAuditEntry)
            .where(
                and_(
                    SimulationAuditEntry.workspace_id == workspace_id,
                    or_(
                        SimulationAuditEntry.action.ilike(pattern),
                        SimulationAuditEntry.actor.ilike(pattern),
                        SimulationAuditEntry.event_type.ilike(pattern),
                    ),
                )
            )
            .order_by(desc(SimulationAuditEntry.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [self._entry_to_dict(row) for row in result.scalars().all()]

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _entry_to_dict(entry: SimulationAuditEntry) -> dict[str, Any]:
        details = None
        if entry.details_json:
            try:
                details = json.loads(entry.details_json)
            except (json.JSONDecodeError, TypeError):
                details = entry.details_json

        return {
            "id": str(entry.id),
            "workspace_id": str(entry.workspace_id),
            "simulation_run_id": str(entry.simulation_run_id),
            "user_id": str(entry.user_id) if entry.user_id else None,
            "event_type": entry.event_type,
            "actor": entry.actor,
            "action": entry.action,
            "details": details,
            "ip_address": entry.ip_address,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
