"""
VulnService — Vulnerability Management (Sprint 22).

Capabilities:
  1. CVE extraction  — regex parse CVE-YYYY-NNNNN from finding text
  2. EPSS enrichment — Exploit Prediction Scoring System (0–1 probability)
  3. KEV detection   — CISA Known Exploited Vulnerabilities catalog
  4. Inventory       — group findings by CVE, per-CVE affected-resource list
  5. Summary stats   — total CVEs, KEV count, critical EPSS, avg risk score

EPSS/KEV data: bundled static snapshot (updated periodically; real API at
  https://api.first.org/data/v1/epss and https://www.cisa.gov/known-exploited-vulnerabilities-catalog).
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding

# ── Static EPSS scores (probability of exploitation within 30 days) ───────────
# Source: FIRST EPSS model v3 — snapshot 2024-Q4
_EPSS: dict[str, float] = {
    "CVE-2021-44228": 0.97561,  # Log4Shell
    "CVE-2022-0847":  0.00445,  # Dirty Pipe
    "CVE-2022-22965": 0.97532,  # Spring4Shell
    "CVE-2023-44487": 0.09210,  # HTTP/2 Rapid Reset
    "CVE-2023-46604": 0.97430,  # Apache ActiveMQ RCE
    "CVE-2021-22205": 0.97497,  # GitLab RCE
    "CVE-2022-26134": 0.97444,  # Confluence OGNL
    "CVE-2023-4966":  0.96234,  # Citrix Bleed
    "CVE-2022-3786":  0.00312,  # OpenSSL buffer overflow
    "CVE-2021-26084": 0.97402,  # Confluence Server RCE
    "CVE-2023-38545": 0.00276,  # curl SOCKS5
    "CVE-2024-3400":  0.96100,  # PAN-OS command injection
    "CVE-2023-23397": 0.52880,  # Outlook NTLM relay
    "CVE-2022-41082": 0.97120,  # ProxyNotShell
    "CVE-2023-29300": 0.94210,  # ColdFusion deserialization
    "CVE-2022-1388":  0.97565,  # F5 iControl auth bypass
    "CVE-2023-27997": 0.96440,  # FortiOS heap overflow
    "CVE-2022-42475": 0.97210,  # FortiOS SSL-VPN RCE
    "CVE-2023-22515": 0.97300,  # Confluence broken access control
    "CVE-2021-34527": 0.97448,  # PrintNightmare
    "CVE-2022-30190": 0.97501,  # Follina MSDT
    "CVE-2021-40444": 0.97520,  # MSHTML RCE
}

# ── CISA Known Exploited Vulnerabilities (KEV) catalog — selected entries ─────
_KEV: set[str] = {
    "CVE-2021-44228",  # Log4Shell
    "CVE-2022-22965",  # Spring4Shell
    "CVE-2023-46604",  # Apache ActiveMQ
    "CVE-2021-22205",  # GitLab RCE
    "CVE-2022-26134",  # Confluence OGNL
    "CVE-2023-4966",   # Citrix Bleed
    "CVE-2021-26084",  # Confluence Server
    "CVE-2024-3400",   # PAN-OS
    "CVE-2022-41082",  # ProxyNotShell
    "CVE-2023-29300",  # ColdFusion
    "CVE-2022-1388",   # F5 iControl
    "CVE-2023-27997",  # FortiOS
    "CVE-2022-42475",  # FortiOS SSL-VPN
    "CVE-2023-22515",  # Confluence
    "CVE-2021-34527",  # PrintNightmare
    "CVE-2022-30190",  # Follina
    "CVE-2021-40444",  # MSHTML
    "CVE-2022-0847",   # Dirty Pipe (added 2022-04)
    "CVE-2023-23397",  # Outlook NTLM
    "CVE-2023-44487",  # HTTP/2 Rapid Reset
}

# ── Severity → CVSS base score mapping (for CVEs without explicit CVSS) ───────
_SEVERITY_CVSS: dict[str, float] = {
    "critical": 9.0,
    "high":     7.5,
    "medium":   5.5,
    "low":      3.0,
    "info":     1.0,
}

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)


def _extract_cves(text: str) -> list[str]:
    """Return unique, uppercase CVE IDs found in text."""
    return list({m.upper() for m in _CVE_RE.findall(text)})


def _epss(cve_id: str) -> float | None:
    return _EPSS.get(cve_id.upper())


def _in_kev(cve_id: str) -> bool:
    return cve_id.upper() in _KEV


class VulnService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helpers ────────────────────────────────────────────────────

    async def _findings_for_workspace(
        self, workspace_id: uuid.UUID
    ) -> list[CanonicalFinding]:
        result = await self.db.execute(
            select(CanonicalFinding).where(
                CanonicalFinding.workspace_id == workspace_id
            )
        )
        return list(result.scalars().all())

    def _group_by_cve(
        self, findings: list[CanonicalFinding]
    ) -> dict[str, list[CanonicalFinding]]:
        groups: dict[str, list[CanonicalFinding]] = {}
        for f in findings:
            text = (f.title or "") + " " + (f.description or "")
            for cve in _extract_cves(text):
                groups.setdefault(cve, []).append(f)
        return groups

    # ── Public API ──────────────────────────────────────────────────────────

    async def summary(self, workspace_id: uuid.UUID) -> dict[str, Any]:
        findings = await self._findings_for_workspace(workspace_id)
        groups   = self._group_by_cve(findings)

        total_cves  = len(groups)
        kev_count   = sum(1 for cve in groups if _in_kev(cve))
        open_counts = {
            cve: sum(1 for f in flist if f.status == "open")
            for cve, flist in groups.items()
        }
        # CVEs with at least one open finding
        active_cves = sum(1 for c in open_counts if open_counts[c] > 0)

        epss_scores = [_epss(cve) for cve in groups if _epss(cve) is not None]
        avg_epss    = round(sum(epss_scores) / len(epss_scores), 4) if epss_scores else 0.0
        max_epss    = round(max(epss_scores), 4) if epss_scores else 0.0

        # Severity breakdown — worst severity across affected findings per CVE
        sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        sev_breakdown = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for flist in groups.values():
            worst = max(flist, key=lambda f: sev_order.get(f.severity or "info", 0))
            sev = worst.severity or "info"
            if sev in sev_breakdown:
                sev_breakdown[sev] += 1

        # Critical EPSS = CVEs with EPSS ≥ 0.5 (high exploitation probability)
        critical_epss_count = sum(
            1 for cve in groups if (_epss(cve) or 0) >= 0.5
        )

        # EPSS distribution buckets
        epss_dist = {"0.9+": 0, "0.5-0.9": 0, "0.1-0.5": 0, "<0.1": 0}
        for cve in groups:
            score = _epss(cve) or 0.0
            if score >= 0.9:
                epss_dist["0.9+"] += 1
            elif score >= 0.5:
                epss_dist["0.5-0.9"] += 1
            elif score >= 0.1:
                epss_dist["0.1-0.5"] += 1
            else:
                epss_dist["<0.1"] += 1

        return {
            "total_cves":          total_cves,
            "active_cves":         active_cves,
            "kev_count":           kev_count,
            "critical_epss_count": critical_epss_count,
            "avg_epss":            avg_epss,
            "max_epss":            max_epss,
            "severity_breakdown":  sev_breakdown,
            "epss_distribution":   epss_dist,
        }

    async def inventory(self, workspace_id: uuid.UUID) -> list[dict[str, Any]]:
        findings = await self._findings_for_workspace(workspace_id)
        groups   = self._group_by_cve(findings)

        sev_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        result    = []

        for cve, flist in groups.items():
            open_findings   = [f for f in flist if f.status == "open"]
            closed_findings = [f for f in flist if f.status != "open"]

            # Worst severity
            worst = max(flist, key=lambda f: sev_order.get(f.severity or "info", 0))
            severity = worst.severity or "info"

            # Affected resources
            resources = [
                {
                    "resource_arn":  str(f.resource_arn or ""),
                    "resource_type": str(f.resource_type or ""),
                    "region":        str(f.region or ""),
                    "severity":      str(f.severity or ""),
                    "status":        str(f.status or ""),
                    "finding_title": str(f.title or ""),
                    "finding_id":    str(f.id),
                }
                for f in flist
            ]

            epss_score = _epss(cve)
            in_kev     = _in_kev(cve)

            # Risk tier
            if in_kev or (epss_score or 0) >= 0.9:
                risk_tier = "imminent"
            elif (epss_score or 0) >= 0.5 or severity == "critical":
                risk_tier = "high"
            elif severity == "high":
                risk_tier = "elevated"
            else:
                risk_tier = "moderate"

            # First/last seen
            def _dt_str(val) -> str | None:
                if val is None:
                    return None
                return val.isoformat() if hasattr(val, "isoformat") else str(val)

            first_seen = min(
                (f.first_seen_at for f in flist if f.first_seen_at),
                default=None,
            )
            last_seen = max(
                (f.last_seen_at for f in flist if f.last_seen_at),
                default=None,
            )

            result.append(
                {
                    "cve_id":          cve,
                    "severity":        severity,
                    "epss_score":      epss_score,
                    "in_kev":          in_kev,
                    "risk_tier":       risk_tier,
                    "open_count":      len(open_findings),
                    "total_count":     len(flist),
                    "affected_count":  len(resources),
                    "resources":       resources,
                    "cvss_score":      _SEVERITY_CVSS.get(severity, 5.0),
                    "first_seen":      _dt_str(first_seen),
                    "last_seen":       _dt_str(last_seen),
                    "description":     (flist[0].description or "")[:300],
                }
            )

        # Sort: KEV first, then by EPSS desc, then by severity
        result.sort(
            key=lambda x: (
                not x["in_kev"],
                -(x["epss_score"] or 0),
                -sev_order.get(x["severity"], 0),
            )
        )
        return result

    async def cve_detail(
        self, workspace_id: uuid.UUID, cve_id: str
    ) -> dict[str, Any] | None:
        inventory = await self.inventory(workspace_id)
        cve_upper = cve_id.upper()
        for item in inventory:
            if item["cve_id"] == cve_upper:
                return item
        return None
