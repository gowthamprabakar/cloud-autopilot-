"""
SessionHistoryService — Cross-simulation learning and history.

Sprint 34: Tracks simulation history for trend analysis and learning.
Provides domain trends, cost analysis, and run-to-run comparisons.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, and_, func, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulation_run import SimulationRun
from app.models.validation_gate import ValidationGate


class SessionHistoryService:
    """Cross-simulation learning, trend analysis, and cost tracking."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── History ──────────────────────────────────────────────────────────────

    async def get_history(
        self,
        workspace_id: uuid.UUID,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get simulation history with trend data.

        Returns runs ordered by creation time descending, including:
        domain, confidence, gates passed, cost, and duration.
        """
        conditions = [SimulationRun.workspace_id == workspace_id]
        if domain:
            conditions.append(SimulationRun.domain == domain)

        stmt = (
            select(SimulationRun)
            .where(and_(*conditions))
            .order_by(desc(SimulationRun.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        runs = result.scalars().all()

        return [
            {
                "id": str(run.id),
                "domain": run.domain,
                "status": run.status,
                "confidence_score": run.confidence_score,
                "gates_passed": run.gates_passed,
                "gates_total": run.gates_total,
                "agent_count": run.agent_count,
                "total_cost_usd": run.total_cost_usd,
                "total_tokens_used": run.total_tokens_used,
                "duration_seconds": run.duration_seconds,
                "created_at": run.created_at.isoformat() if run.created_at else None,
                "completed_at": (
                    run.completed_at.isoformat() if run.completed_at else None
                ),
            }
            for run in runs
        ]

    # ── Domain Trends ────────────────────────────────────────────────────────

    async def get_domain_trends(
        self,
        workspace_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Analyze trends per threat domain across simulation runs.

        Returns average confidence by domain, improvement over time,
        most simulated domains, and best/worst performing.
        """
        stmt = (
            select(
                SimulationRun.domain,
                func.count(SimulationRun.id).label("run_count"),
                func.avg(SimulationRun.confidence_score).label("avg_confidence"),
                func.min(SimulationRun.confidence_score).label("min_confidence"),
                func.max(SimulationRun.confidence_score).label("max_confidence"),
                func.avg(SimulationRun.gates_passed).label("avg_gates_passed"),
                func.avg(SimulationRun.total_cost_usd).label("avg_cost"),
                func.avg(SimulationRun.duration_seconds).label("avg_duration"),
            )
            .where(
                and_(
                    SimulationRun.workspace_id == workspace_id,
                    SimulationRun.status == "completed",
                )
            )
            .group_by(SimulationRun.domain)
            .order_by(desc(func.count(SimulationRun.id)))
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        domains: list[dict[str, Any]] = []
        best_domain: dict[str, Any] | None = None
        worst_domain: dict[str, Any] | None = None

        for row in rows:
            entry = {
                "domain": row.domain,
                "run_count": row.run_count,
                "avg_confidence": round(float(row.avg_confidence or 0), 2),
                "min_confidence": round(float(row.min_confidence or 0), 2),
                "max_confidence": round(float(row.max_confidence or 0), 2),
                "avg_gates_passed": round(float(row.avg_gates_passed or 0), 1),
                "avg_cost_usd": round(float(row.avg_cost or 0), 4),
                "avg_duration_seconds": round(float(row.avg_duration or 0), 1),
            }
            domains.append(entry)

            avg = entry["avg_confidence"]
            if best_domain is None or avg > best_domain["avg_confidence"]:
                best_domain = entry
            if worst_domain is None or avg < worst_domain["avg_confidence"]:
                worst_domain = entry

        # Confidence improvement over time (compare first half vs second half)
        improvement = await self._compute_improvement(workspace_id)

        return {
            "workspace_id": str(workspace_id),
            "total_domains": len(domains),
            "domains": domains,
            "best_performing": best_domain,
            "worst_performing": worst_domain,
            "confidence_improvement": improvement,
        }

    async def _compute_improvement(
        self,
        workspace_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Compare average confidence of first-half vs second-half of runs."""
        stmt = (
            select(SimulationRun.confidence_score, SimulationRun.created_at)
            .where(
                and_(
                    SimulationRun.workspace_id == workspace_id,
                    SimulationRun.status == "completed",
                )
            )
            .order_by(SimulationRun.created_at)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        if len(rows) < 2:
            return {"trend": "insufficient_data", "delta": 0.0}

        mid = len(rows) // 2
        first_half_avg = sum(r.confidence_score for r in rows[:mid]) / mid
        second_half_avg = sum(r.confidence_score for r in rows[mid:]) / (
            len(rows) - mid
        )
        delta = round(second_half_avg - first_half_avg, 2)

        if delta > 1.0:
            trend = "improving"
        elif delta < -1.0:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "delta": delta,
            "first_half_avg": round(first_half_avg, 2),
            "second_half_avg": round(second_half_avg, 2),
        }

    # ── Cost Analysis ────────────────────────────────────────────────────────

    async def get_cost_analysis(
        self,
        workspace_id: uuid.UUID,
        days: int = 30,
    ) -> dict[str, Any]:
        """
        Analyze API cost trends.

        Returns daily cost, per-domain cost, cost per agent, and budget utilisation.
        """
        cutoff = datetime.now(UTC) - timedelta(days=days)

        stmt = (
            select(SimulationRun)
            .where(
                and_(
                    SimulationRun.workspace_id == workspace_id,
                    SimulationRun.created_at >= cutoff,
                )
            )
            .order_by(SimulationRun.created_at)
        )
        result = await self.db.execute(stmt)
        runs = result.scalars().all()

        total_cost = 0.0
        total_tokens = 0
        total_agents = 0
        daily_costs: dict[str, float] = defaultdict(float)
        domain_costs: dict[str, float] = defaultdict(float)
        domain_tokens: dict[str, int] = defaultdict(int)

        for run in runs:
            cost = run.total_cost_usd or 0.0
            tokens = run.total_tokens_used or 0
            agents = run.agent_count or 0

            total_cost += cost
            total_tokens += tokens
            total_agents += agents

            day_key = (
                run.created_at.strftime("%Y-%m-%d") if run.created_at else "unknown"
            )
            daily_costs[day_key] += cost
            domain_costs[run.domain] += cost
            domain_tokens[run.domain] += tokens

        run_count = len(runs)
        avg_cost_per_run = round(total_cost / run_count, 4) if run_count else 0.0
        avg_cost_per_agent = (
            round(total_cost / total_agents, 4) if total_agents else 0.0
        )

        return {
            "workspace_id": str(workspace_id),
            "period_days": days,
            "total_runs": run_count,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "avg_cost_per_run": avg_cost_per_run,
            "avg_cost_per_agent": avg_cost_per_agent,
            "daily_costs": dict(daily_costs),
            "domain_costs": {k: round(v, 4) for k, v in domain_costs.items()},
            "domain_tokens": dict(domain_tokens),
        }

    # ── Run Comparison ───────────────────────────────────────────────────────

    async def compare_runs(
        self,
        run_id_1: uuid.UUID,
        run_id_2: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Compare two simulation runs side-by-side.

        Returns gate scores diff, confidence diff, and agent output summary diff.
        """
        stmt = select(SimulationRun).where(
            SimulationRun.id.in_([run_id_1, run_id_2])
        )
        result = await self.db.execute(stmt)
        runs_by_id: dict[uuid.UUID, SimulationRun] = {
            r.id: r for r in result.scalars().all()
        }

        if run_id_1 not in runs_by_id or run_id_2 not in runs_by_id:
            missing = []
            if run_id_1 not in runs_by_id:
                missing.append(str(run_id_1))
            if run_id_2 not in runs_by_id:
                missing.append(str(run_id_2))
            return {"error": f"Run(s) not found: {', '.join(missing)}"}

        run_a = runs_by_id[run_id_1]
        run_b = runs_by_id[run_id_2]

        # Fetch gate scores for both runs
        gates_a = await self._get_gate_scores(run_id_1)
        gates_b = await self._get_gate_scores(run_id_2)

        # Build gate comparison
        all_gate_names = sorted(set(list(gates_a.keys()) + list(gates_b.keys())))
        gate_comparison = []
        for name in all_gate_names:
            score_a = gates_a.get(name)
            score_b = gates_b.get(name)
            gate_comparison.append(
                {
                    "gate": name,
                    "run_1_score": score_a,
                    "run_2_score": score_b,
                    "delta": (
                        round((score_b or 0) - (score_a or 0), 2)
                        if score_a is not None and score_b is not None
                        else None
                    ),
                }
            )

        return {
            "run_1": self._run_summary(run_a),
            "run_2": self._run_summary(run_b),
            "confidence_diff": round(
                (run_b.confidence_score or 0) - (run_a.confidence_score or 0), 2
            ),
            "gates_passed_diff": (run_b.gates_passed or 0) - (run_a.gates_passed or 0),
            "cost_diff": round(
                (run_b.total_cost_usd or 0) - (run_a.total_cost_usd or 0), 4
            ),
            "duration_diff": round(
                (run_b.duration_seconds or 0) - (run_a.duration_seconds or 0), 1
            ),
            "gate_comparison": gate_comparison,
        }

    async def _get_gate_scores(
        self, run_id: uuid.UUID
    ) -> dict[str, float]:
        """Fetch gate name -> score mapping for a run."""
        stmt = (
            select(ValidationGate.name, ValidationGate.score)
            .where(ValidationGate.simulation_run_id == run_id)
            .order_by(ValidationGate.gate_number)
        )
        result = await self.db.execute(stmt)
        return {row.name: float(row.score) for row in result.all()}

    @staticmethod
    def _run_summary(run: SimulationRun) -> dict[str, Any]:
        return {
            "id": str(run.id),
            "domain": run.domain,
            "status": run.status,
            "confidence_score": run.confidence_score,
            "gates_passed": run.gates_passed,
            "gates_total": run.gates_total,
            "agent_count": run.agent_count,
            "total_cost_usd": run.total_cost_usd,
            "duration_seconds": run.duration_seconds,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
