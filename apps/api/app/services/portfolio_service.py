"""
PortfolioService — MSP/vCISO multi-workspace portfolio (Sprint 24).
"""
from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.workspace import Workspace
from app.models.canonical_finding import CanonicalFinding
from app.services.risk_score_service import RiskScoreService

class PortfolioService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_workspaces(self) -> list[dict]:
        """Return all workspaces with basic info."""
        result = await self.db.execute(select(Workspace))
        workspaces = list(result.scalars().all())
        return [
            {
                "id": str(w.id),
                "name": str(w.name),
                "slug": str(getattr(w, 'slug', '') or ''),
                "created_at": w.created_at.isoformat() if hasattr(w.created_at, 'isoformat') else str(w.created_at) if w.created_at else None,
            }
            for w in workspaces
        ]

    async def portfolio_summary(self) -> dict[str, Any]:
        """Cross-workspace portfolio summary for MSP/vCISO view."""
        result = await self.db.execute(select(Workspace))
        workspaces = list(result.scalars().all())

        risk_svc = RiskScoreService(self.db)
        workspace_summaries = []
        total_findings = 0
        total_critical = 0
        total_high = 0
        sla_breaches = 0

        for ws in workspaces:
            ws_id = uuid.UUID(str(ws.id)) if not isinstance(ws.id, uuid.UUID) else ws.id
            try:
                summary = await risk_svc.summary(ws_id)
                risk_score = summary.get("risk_score", 0)
                by_sev = summary.get("by_severity", {})
                sla = summary.get("sla_compliance", {})

                open_count = sum(by_sev.get(s, {}).get("open", 0) for s in ["critical", "high", "medium", "low", "info"])
                crit_count = by_sev.get("critical", {}).get("open", 0)
                high_count = by_sev.get("high", {}).get("open", 0)

                # SLA breach = any severity with compliance < 100%
                # sla_compliance format: {"critical": 0.0, "high": 0.0, ...} (flat float 0-1)
                has_sla_breach = any(
                    (sla.get(s, 1.0) if not isinstance(sla.get(s), dict) else sla.get(s, {}).get("compliance_pct", 100)) < 1.0
                    for s in ["critical", "high", "medium", "low"]
                )

                total_findings += open_count
                total_critical += crit_count
                total_high += high_count
                if has_sla_breach:
                    sla_breaches += 1

                workspace_summaries.append({
                    "workspace_id": str(ws.id),
                    "workspace_name": str(ws.name),
                    "risk_score": risk_score,
                    "open_findings": open_count,
                    "critical_count": crit_count,
                    "high_count": high_count,
                    "medium_count": by_sev.get("medium", {}).get("open", 0),
                    "low_count": by_sev.get("low", {}).get("open", 0),
                    "sla_compliance": sla,
                    "has_sla_breach": has_sla_breach,
                    "trend_delta": summary.get("trend_delta", 0),
                })
            except Exception:
                workspace_summaries.append({
                    "workspace_id": str(ws.id),
                    "workspace_name": str(ws.name),
                    "risk_score": 0,
                    "open_findings": 0,
                    "critical_count": 0,
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 0,
                    "sla_compliance": {},
                    "has_sla_breach": False,
                    "trend_delta": 0,
                })

        # Sort by risk_score descending (worst first)
        workspace_summaries.sort(key=lambda x: x["risk_score"], reverse=True)

        return {
            "total_workspaces": len(workspaces),
            "total_open_findings": total_findings,
            "total_critical": total_critical,
            "total_high": total_high,
            "sla_breach_count": sla_breaches,
            "avg_risk_score": round(sum(w["risk_score"] for w in workspace_summaries) / len(workspace_summaries), 1) if workspace_summaries else 0,
            "workspaces": workspace_summaries,
        }

    async def sla_breaches(self) -> list[dict[str, Any]]:
        """All findings approaching or past SLA across all workspaces."""
        from datetime import datetime, UTC
        now = datetime.now(UTC)

        SLA_HOURS = {"critical": 24, "high": 168, "medium": 720, "low": 2160}

        result = await self.db.execute(select(Workspace))
        workspaces = list(result.scalars().all())

        breaches = []
        for ws in workspaces:
            ws_id = ws.id
            findings_result = await self.db.execute(
                select(CanonicalFinding).where(
                    CanonicalFinding.workspace_id == ws_id,
                    CanonicalFinding.status == "open",
                )
            )
            findings = list(findings_result.scalars().all())

            for f in findings:
                sla_limit = SLA_HOURS.get(f.severity or "low", 2160)
                first_seen = f.first_seen_at
                if first_seen is None:
                    continue

                if isinstance(first_seen, str):
                    try:
                        first_seen = datetime.fromisoformat(first_seen)
                        if first_seen.tzinfo is None:
                            first_seen = first_seen.replace(tzinfo=UTC)
                    except Exception:
                        continue

                age_hours = (now - first_seen).total_seconds() / 3600
                remaining_hours = sla_limit - age_hours

                if remaining_hours < sla_limit * 0.2:  # Within 20% of SLA or breached
                    breaches.append({
                        "finding_id": str(f.id),
                        "workspace_id": str(ws.id),
                        "workspace_name": str(ws.name),
                        "title": str(f.title or ""),
                        "severity": str(f.severity or ""),
                        "resource_arn": str(f.resource_arn or ""),
                        "sla_limit_hours": sla_limit,
                        "age_hours": round(age_hours, 1),
                        "remaining_hours": round(remaining_hours, 1),
                        "is_breached": remaining_hours <= 0,
                        "first_seen": first_seen.isoformat() if hasattr(first_seen, 'isoformat') else str(first_seen),
                    })

        # Sort by remaining_hours ascending (most urgent first)
        breaches.sort(key=lambda x: x["remaining_hours"])
        return breaches
