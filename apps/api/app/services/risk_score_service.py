"""
RiskScoreService — computes transparent 0-100 risk posture score.

Formula (documented, not a black box):
  score = 100 - deductions

  Deductions per severity (capped):
    critical : each open finding deducts min(40/total_critical, 4.0) pts  → max 40
    high     : each open finding deducts min(30/total_high,    2.0) pts  → max 30
    medium   : each open finding deducts min(20/total_medium,  1.0) pts  → max 20
    low      : each open finding deducts min(10/total_low,     0.5) pts  → max 10

  "open" means status in ('open', 'in_progress')
  Final score clamped to [0, 100].

SLA thresholds (used in compliance rate):
    critical → 1 day
    high     → 7 days
    medium   → 30 days
    low      → 90 days
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aws_account import AwsAccount
from app.models.canonical_finding import CanonicalFinding

# ── Constants ──────────────────────────────────────────────────────────────────

_OPEN_STATUSES = ("open", "in_progress")

_MAX_DEDUCTION = {"critical": 40.0, "high": 30.0, "medium": 20.0, "low": 10.0}
_PER_FINDING_CAP = {"critical": 4.0, "high": 2.0, "medium": 1.0, "low": 0.5}

_SLA_DAYS = {"critical": 1, "high": 7, "medium": 30, "low": 90}

_SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_score(counts: dict[str, dict[str, int]]) -> int:
    """
    counts: {"critical": {"open": N, "total": M}, "high": {...}, ...}
    Returns integer score 0-100.
    """
    deduction = 0.0
    for sev, cap in _MAX_DEDUCTION.items():
        bucket = counts.get(sev, {"open": 0, "total": 0})
        total = max(bucket["total"], 1)
        per_finding = min(cap / total, _PER_FINDING_CAP[sev])
        deduction += min(bucket["open"] * per_finding, cap)
    return max(0, min(100, round(100 - deduction)))


def _trend_label(current: int, previous: int) -> str:
    delta = current - previous
    if delta <= -3:
        return "improving"
    if delta >= 3:
        return "worsening"
    return "stable"


def _parse_dt(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
    try:
        s = str(val)
        # Handle both naive and aware ISO strings
        if s.endswith("+00:00"):
            s = s[:-6]
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


# ── Service ───────────────────────────────────────────────────────────────────

class RiskScoreService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _counts_for_workspace(
        self, workspace_id: uuid.UUID, account_uuid: uuid.UUID | None = None
    ) -> dict[str, dict[str, int]]:
        """Return open/total counts per severity for the workspace (or one account).

        account_uuid: AwsAccount.id (UUID primary key) — matches canonical_findings.aws_account_id.
        """
        q = select(
            CanonicalFinding.severity,
            CanonicalFinding.status,
            func.count().label("cnt"),
        ).where(CanonicalFinding.workspace_id == workspace_id)

        if account_uuid is not None:
            q = q.where(CanonicalFinding.aws_account_id == account_uuid)

        q = q.group_by(CanonicalFinding.severity, CanonicalFinding.status)
        rows = (await self.db.execute(q)).fetchall()

        counts: dict[str, dict[str, int]] = {}
        for sev, status, cnt in rows:
            sev = (sev or "").lower()
            if sev not in counts:
                counts[sev] = {"open": 0, "total": 0}
            counts[sev]["total"] += cnt
            if status in _OPEN_STATUSES:
                counts[sev]["open"] += cnt
        return counts

    async def _sla_compliance(
        self, workspace_id: uuid.UUID
    ) -> dict[str, float]:
        """
        For each severity, compute % of open findings still within SLA window.
        (i.e. first_seen_at + SLA_DAYS >= now → within SLA)
        """
        now = datetime.now(timezone.utc)
        result: dict[str, float] = {}

        for sev, days in _SLA_DAYS.items():
            q = select(
                CanonicalFinding.first_seen_at,
                CanonicalFinding.status,
            ).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.severity == sev,
                CanonicalFinding.status.in_(list(_OPEN_STATUSES)),
            )
            rows = (await self.db.execute(q)).fetchall()

            if not rows:
                result[sev] = 1.0
                continue

            within = sum(
                1
                for first_seen, _ in rows
                if (dt := _parse_dt(first_seen)) is not None
                and (now - dt) <= timedelta(days=days)
            )
            result[sev] = round(within / len(rows), 3)

        return result

    async def _trend_score(
        self, workspace_id: uuid.UUID, days_ago: int = 30
    ) -> int:
        """Compute the score as it would have been `days_ago` days ago."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)

        # Only count findings that existed before the cutoff
        q = select(
            CanonicalFinding.severity,
            CanonicalFinding.status,
            func.count().label("cnt"),
        ).where(
            CanonicalFinding.workspace_id == workspace_id,
            CanonicalFinding.first_seen_at <= cutoff.isoformat(),
        ).group_by(CanonicalFinding.severity, CanonicalFinding.status)

        rows = (await self.db.execute(q)).fetchall()
        counts: dict[str, dict[str, int]] = {}
        for sev, status, cnt in rows:
            sev = (sev or "").lower()
            if sev not in counts:
                counts[sev] = {"open": 0, "total": 0}
            counts[sev]["total"] += cnt
            if status in _OPEN_STATUSES:
                counts[sev]["open"] += cnt

        return _compute_score(counts)

    async def summary(self, workspace_id: uuid.UUID) -> dict:
        """Full executive summary for the workspace."""
        counts = await self._counts_for_workspace(workspace_id)
        current_score = _compute_score(counts)
        prev_score = await self._trend_score(workspace_id, days_ago=30)
        sla = await self._sla_compliance(workspace_id)

        total_findings = sum(v["total"] for v in counts.values())
        open_findings = sum(v["open"] for v in counts.values())

        # Per-account scores
        acct_q = select(AwsAccount).where(AwsAccount.workspace_id == workspace_id)
        acct_rows = (await self.db.execute(acct_q)).scalars().all()
        accounts = []
        for acct in acct_rows:
            acct_counts = await self._counts_for_workspace(
                workspace_id, account_uuid=acct.id
            )
            acct_score = _compute_score(acct_counts)
            acct_open = sum(v["open"] for v in acct_counts.values())
            accounts.append({
                "id": str(acct.id),
                "account_id": acct.account_id,
                "alias": acct.account_alias or acct.account_id,
                "risk_score": acct_score,
                "open_findings": acct_open,
                "status": acct.status,
            })
        accounts.sort(key=lambda a: a["risk_score"])

        # Top 5 highest-risk open findings (by risk_score desc)
        top_q = (
            select(
                CanonicalFinding.id,
                CanonicalFinding.title,
                CanonicalFinding.severity,
                CanonicalFinding.risk_score,
                CanonicalFinding.resource_type,
                CanonicalFinding.aws_account_id,
            )
            .where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.status.in_(list(_OPEN_STATUSES)),
            )
            .order_by(CanonicalFinding.risk_score.desc())
            .limit(5)
        )
        top_rows = (await self.db.execute(top_q)).fetchall()
        top_findings = [
            {
                "id": str(r.id),
                "title": r.title,
                "severity": r.severity,
                "risk_score": r.risk_score,
                "resource_type": r.resource_type,
                "account_id": r.aws_account_id,
            }
            for r in top_rows
        ]

        return {
            "risk_score": current_score,
            "previous_score": prev_score,
            "trend": _trend_label(current_score, prev_score),
            "trend_delta": current_score - prev_score,
            "total_findings": total_findings,
            "open_findings": open_findings,
            "by_severity": {
                sev: counts.get(sev, {"open": 0, "total": 0})
                for sev in _SEVERITY_ORDER
            },
            "sla_compliance": sla,
            "accounts": accounts,
            "top_findings": top_findings,
            "score_formula": (
                "100 minus weighted deductions: critical(max 40), "
                "high(max 30), medium(max 20), low(max 10). "
                "Clamped to [0,100]."
            ),
        }

    async def trend(self, workspace_id: uuid.UUID, days: int = 30) -> dict:
        """Daily open-finding counts for the past N days."""
        now = datetime.now(timezone.utc)
        data_points = []

        for i in range(days - 1, -1, -1):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)

            # Count findings that were open on this day:
            # first_seen_at <= day_end AND (resolved_at IS NULL OR resolved_at > day_start)
            q = select(func.count()).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.first_seen_at <= day_end.isoformat(),
                CanonicalFinding.status.in_(list(_OPEN_STATUSES)),
            )
            open_count = (await self.db.execute(q)).scalar() or 0

            # New findings created on this day
            q_new = select(func.count()).where(
                CanonicalFinding.workspace_id == workspace_id,
                CanonicalFinding.first_seen_at >= day_start.isoformat(),
                CanonicalFinding.first_seen_at <= day_end.isoformat(),
            )
            new_count = (await self.db.execute(q_new)).scalar() or 0

            data_points.append({
                "date": day_start.strftime("%Y-%m-%d"),
                "open": open_count,
                "new": new_count,
            })

        return {"days": days, "data_points": data_points}
