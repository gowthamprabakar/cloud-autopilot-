"""
SLA Service — computes SLA status for canonical findings.

SLA status:
  "on_track"  — age < 80% of SLA days for severity
  "at_risk"   — age >= 80% of SLA days but < 100%
  "breached"  — age >= SLA days
  "resolved"  — finding is already resolved/closed

Age is computed from first_seen_at to now.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from app.models.canonical_finding import CanonicalFinding
from app.models.enums import FindingSeverity, FindingStatus

SLA_STATUS = Literal["on_track", "at_risk", "breached", "resolved", "n/a"]

_DEFAULT_SLA_DAYS = {
    FindingSeverity.CRITICAL: 3,
    FindingSeverity.HIGH: 7,
    FindingSeverity.MEDIUM: 30,
    FindingSeverity.LOW: 90,
    FindingSeverity.INFO: 180,
}


def compute_sla_status(finding: CanonicalFinding, sla_days_override: dict | None = None) -> dict:
    """
    Returns a dict with:
      sla_status: SLA_STATUS literal
      sla_due_date: ISO string of the deadline (first_seen_at + sla_days)
      sla_days_remaining: int (negative = overdue)
      sla_days_total: int (total SLA window)
    """
    if finding.status in (FindingStatus.RESOLVED, FindingStatus.ACCEPTED):
        return {
            "sla_status": "resolved",
            "sla_due_date": None,
            "sla_days_remaining": None,
            "sla_days_total": None,
        }

    # Get SLA days for this severity
    sla_map = sla_days_override or {}
    severity = FindingSeverity(finding.severity)
    default_days = _DEFAULT_SLA_DAYS.get(severity, 30)
    sla_key = f"sla_days_{severity.value}"
    total_days = sla_map.get(sla_key, default_days)

    # Parse first_seen_at
    first_seen = finding.first_seen_at
    if first_seen is None:
        return {
            "sla_status": "n/a",
            "sla_due_date": None,
            "sla_days_remaining": None,
            "sla_days_total": total_days,
        }

    if isinstance(first_seen, str):
        first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
    if first_seen.tzinfo is None:
        first_seen = first_seen.replace(tzinfo=UTC)

    due_date = first_seen + timedelta(days=total_days)
    now = datetime.now(UTC)
    days_remaining = (due_date - now).days

    # Status thresholds
    if days_remaining < 0:
        status = "breached"
    elif days_remaining <= total_days * 0.2:  # within last 20% of window
        status = "at_risk"
    else:
        status = "on_track"

    return {
        "sla_status": status,
        "sla_due_date": due_date.isoformat(),
        "sla_days_remaining": days_remaining,
        "sla_days_total": total_days,
    }


class SlaService:
    def __init__(self, canonical_repo, settings_repo):
        self._canonical_repo = canonical_repo
        self._settings_repo = settings_repo

    async def get_findings_with_sla(
        self, workspace_id: uuid.UUID, status_filter: str | None = None
    ) -> list[dict]:
        """
        Return all open findings with SLA metadata attached.
        Optionally filter by sla_status: "on_track" | "at_risk" | "breached"
        """
        settings = await self._settings_repo.get_or_create(workspace_id)
        sla_map = {
            "sla_days_critical": settings.sla_days_critical,
            "sla_days_high": settings.sla_days_high,
            "sla_days_medium": settings.sla_days_medium,
            "sla_days_low": settings.sla_days_low,
            "sla_days_info": settings.sla_days_info,
        }

        # Only fetch OPEN findings for SLA tracking
        findings = await self._canonical_repo.list_by_workspace(
            workspace_id, status=FindingStatus.OPEN, page_size=10000
        )

        results = []
        for f in findings:
            sla_info = compute_sla_status(f, sla_map)
            if status_filter and sla_info["sla_status"] != status_filter:
                continue
            results.append({
                "id": str(f.id),
                "title": f.title,
                "severity": f.severity,
                "resource_type": f.resource_type,
                "resource_arn": f.resource_arn,
                "first_seen_at": f.first_seen_at,
                "risk_score": f.risk_score,
                **sla_info,
            })

        # Sort: breached first, then at_risk, then on_track
        order = {"breached": 0, "at_risk": 1, "on_track": 2, "resolved": 3, "n/a": 4}
        results.sort(key=lambda x: (order.get(x["sla_status"], 5), -(x.get("risk_score") or 0)))
        return results

    async def get_sla_summary(self, workspace_id: uuid.UUID) -> dict:
        """Return counts by SLA status for the dashboard."""
        all_findings = await self.get_findings_with_sla(workspace_id)
        counts = {"breached": 0, "at_risk": 0, "on_track": 0, "total_open": len(all_findings)}
        for f in all_findings:
            s = f.get("sla_status", "on_track")
            if s in counts:
                counts[s] += 1
        return counts
