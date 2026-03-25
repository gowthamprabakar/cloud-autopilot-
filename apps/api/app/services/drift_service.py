"""
DriftService — Configuration drift detection & Root Cause v2 (Sprint 28).

Detects:
1. Recurrence — findings that were resolved then reopened (same fingerprint)
2. Configuration drift — resource_arn with changing severity over time
3. Root cause clusters — groups of findings sharing resource_arn or resource_type patterns
"""
from __future__ import annotations
import uuid, hashlib, re
from datetime import datetime, UTC
from collections import defaultdict
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.canonical_finding import CanonicalFinding


def _parse_dt(val) -> datetime | None:
    if val is None: return None
    if hasattr(val, 'utcoffset'): return val
    try:
        dt = datetime.fromisoformat(str(val))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=UTC)
        return dt
    except: return None


class DriftService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _findings(self, workspace_id: uuid.UUID) -> list[CanonicalFinding]:
        result = await self.db.execute(
            select(CanonicalFinding).where(CanonicalFinding.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def recurrences(self, workspace_id: uuid.UUID) -> list[dict]:
        """Find findings that were resolved then reopened (same fingerprint appears with both resolved_at set AND status=open)."""
        findings = await self._findings(workspace_id)
        by_fp = defaultdict(list)
        for f in findings:
            if f.fingerprint:
                by_fp[f.fingerprint].append(f)

        recurrences = []
        for fp, flist in by_fp.items():
            has_resolved = any(f.resolved_at for f in flist)
            has_open = any(f.status == "open" for f in flist)
            if has_resolved and has_open:
                open_f = next(f for f in flist if f.status == "open")
                resolved_f = next((f for f in flist if f.resolved_at), None)
                recurrences.append({
                    "fingerprint": fp,
                    "finding_id": str(open_f.id),
                    "title": str(open_f.title or ""),
                    "severity": str(open_f.severity or ""),
                    "resource_arn": str(open_f.resource_arn or ""),
                    "status": "recurred",
                    "first_resolved_at": str(resolved_f.resolved_at) if resolved_f and resolved_f.resolved_at else None,
                    "reopened_at": str(open_f.first_seen_at) if open_f.first_seen_at else None,
                    "occurrences": len(flist),
                })
        recurrences.sort(key=lambda x: x["occurrences"], reverse=True)
        return recurrences

    async def drift_signals(self, workspace_id: uuid.UUID) -> list[dict]:
        """Detect resources with severity changes or new findings appearing after prior resolution."""
        findings = await self._findings(workspace_id)
        by_arn = defaultdict(list)
        for f in findings:
            arn = str(f.resource_arn or "")
            if arn:
                by_arn[arn].append(f)

        signals = []
        for arn, flist in by_arn.items():
            if len(flist) < 2:
                continue
            severities = list({f.severity for f in flist if f.severity})
            if len(severities) >= 2:
                sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
                worst = max(flist, key=lambda f: sev_order.get(f.severity or "info", 0))
                signals.append({
                    "resource_arn": arn,
                    "resource_type": str(flist[0].resource_type or ""),
                    "drift_type": "severity_change",
                    "severities": sorted(severities, key=lambda s: sev_order.get(s, 0), reverse=True),
                    "finding_count": len(flist),
                    "worst_severity": str(worst.severity or ""),
                    "worst_title": str(worst.title or ""),
                    "region": str(flist[0].region or ""),
                })

        signals.sort(key=lambda x: x["finding_count"], reverse=True)
        return signals

    async def root_cause_clusters(self, workspace_id: uuid.UUID) -> list[dict]:
        """Group open findings by shared resource_type + title pattern to find systemic root causes."""
        findings = await self._findings(workspace_id)
        open_findings = [f for f in findings if f.status == "open"]

        # Cluster by resource_type + title keyword pattern
        clusters = defaultdict(list)
        for f in open_findings:
            # Extract key pattern from title (first 3-4 significant words)
            title = str(f.title or "")
            words = re.findall(r'[A-Za-z]+', title)
            pattern = " ".join(words[:4]).lower() if words else "unknown"
            key = f"{f.resource_type or 'unknown'}::{pattern}"
            clusters[key].append(f)

        result = []
        for key, flist in clusters.items():
            if len(flist) < 2:
                continue
            rtype, pattern = key.split("::", 1)
            sev_dist = defaultdict(int)
            for f in flist:
                sev_dist[f.severity or "info"] += 1

            result.append({
                "cluster_id": hashlib.sha256(key.encode()).hexdigest()[:12],
                "root_cause_pattern": pattern,
                "resource_type": rtype,
                "finding_count": len(flist),
                "severity_distribution": dict(sev_dist),
                "affected_resources": list({str(f.resource_arn or "") for f in flist}),
                "sample_title": str(flist[0].title or ""),
                "sample_finding_id": str(flist[0].id),
            })

        result.sort(key=lambda x: x["finding_count"], reverse=True)
        return result

    async def summary(self, workspace_id: uuid.UUID) -> dict[str, Any]:
        recurrences = await self.recurrences(workspace_id)
        drifts = await self.drift_signals(workspace_id)
        clusters = await self.root_cause_clusters(workspace_id)

        return {
            "recurrence_count": len(recurrences),
            "drift_signal_count": len(drifts),
            "root_cause_clusters": len(clusters),
            "total_recurred_findings": sum(r["occurrences"] for r in recurrences),
            "total_drifted_resources": len(drifts),
            "top_cluster_pattern": clusters[0]["root_cause_pattern"] if clusters else "",
            "top_cluster_size": clusters[0]["finding_count"] if clusters else 0,
        }
