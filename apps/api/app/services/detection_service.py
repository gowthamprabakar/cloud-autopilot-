"""
DetectionService — Cloud Detection & Response (CDR), Sprint 23.

Correlates across existing data sources (findings, CIEM graph, CVE data)
to fire 8 detection rules and produce MITRE ATT&CK–mapped alerts.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, UTC
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding
from app.models.security_graph_node import SecurityGraphNode
from app.models.security_graph_edge import SecurityGraphEdge

# ── Constants ─────────────────────────────────────────────────────────────────

_CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}", re.IGNORECASE)

_KEV: set[str] = {
    "CVE-2021-44228", "CVE-2022-22965", "CVE-2023-46604", "CVE-2021-22205",
    "CVE-2022-26134", "CVE-2023-4966",  "CVE-2021-26084", "CVE-2024-3400",
    "CVE-2022-41082", "CVE-2023-29300", "CVE-2022-1388",  "CVE-2023-27997",
    "CVE-2022-42475", "CVE-2023-22515", "CVE-2021-34527", "CVE-2022-30190",
    "CVE-2021-40444", "CVE-2022-0847",  "CVE-2023-23397", "CVE-2023-44487",
}

_SEV_SCORE = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _alert_id(rule_id: str, key: str) -> str:
    return hashlib.sha256(f"{rule_id}:{key}".encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _parse_dt(val) -> datetime | None:
    if val is None:
        return None
    if hasattr(val, "utcoffset"):
        return val
    try:
        dt = datetime.fromisoformat(str(val))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except Exception:
        return None


def _risk(severity: str, confidence: float) -> int:
    base = {"critical": 90, "high": 70, "medium": 50}.get(severity, 30)
    return min(100, int(base * confidence))


def _resource(f: CanonicalFinding) -> dict:
    return {
        "arn":    str(f.resource_arn or ""),
        "type":   str(f.resource_type or ""),
        "region": str(f.region or ""),
    }


# ── Service ───────────────────────────────────────────────────────────────────

class DetectionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _findings(self, workspace_id: uuid.UUID) -> list[CanonicalFinding]:
        r = await self.db.execute(
            select(CanonicalFinding).where(CanonicalFinding.workspace_id == workspace_id)
        )
        return list(r.scalars().all())

    async def _nodes(self, workspace_id: uuid.UUID) -> list[SecurityGraphNode]:
        r = await self.db.execute(
            select(SecurityGraphNode).where(SecurityGraphNode.workspace_id == workspace_id)
        )
        return list(r.scalars().all())

    async def _edges(self, workspace_id: uuid.UUID) -> list[SecurityGraphEdge]:
        r = await self.db.execute(
            select(SecurityGraphEdge).where(SecurityGraphEdge.workspace_id == workspace_id)
        )
        return list(r.scalars().all())

    # ── Rules ─────────────────────────────────────────────────────────────────

    def _rule_kev_cve_open(self, findings: list[CanonicalFinding]) -> list[dict]:
        alerts = []
        seen: set[str] = set()
        for f in findings:
            if f.status != "open":
                continue
            text = (f.title or "") + " " + (f.description or "")
            for cve in {m.upper() for m in _CVE_RE.findall(text)}:
                if cve not in _KEV:
                    continue
                aid = _alert_id("KEV_CVE_OPEN", f"{cve}:{f.resource_arn}")
                if aid in seen:
                    continue
                seen.add(aid)
                alerts.append({
                    "id": aid,
                    "rule_id": "KEV_CVE_OPEN",
                    "title": f"CISA KEV CVE Active: {cve} on {f.resource_type or 'resource'}",
                    "description": f"{cve} is in the CISA Known Exploited Vulnerabilities catalog and has an open finding on {f.resource_arn or 'an asset'}.",
                    "severity": "critical",
                    "confidence": 0.98,
                    "tactic": "Initial Access",
                    "technique": "T1190",
                    "risk_score": _risk("critical", 0.98),
                    "status": "open",
                    "affected_resources": [_resource(f)],
                    "finding_ids": [str(f.id)],
                    "detected_at": _now(),
                    "evidence": f"Finding '{f.title}' references {cve} which is actively exploited per CISA KEV catalog.",
                })
        return alerts

    def _rule_public_no_encryption(self, findings: list[CanonicalFinding]) -> list[dict]:
        alerts = []
        open_f = [f for f in findings if f.status == "open"]
        # Group by resource_arn
        by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in open_f:
            arn = str(f.resource_arn or f.id)
            by_arn.setdefault(arn, []).append(f)

        for arn, flist in by_arn.items():
            titles = " ".join(f.title or "" for f in flist).lower()
            has_public = any(kw in titles for kw in ("public", "accessible", "exposed", "open"))
            has_encrypt = any(kw in titles for kw in ("encrypt", "encryption", "kms", "sse"))
            if has_public and has_encrypt:
                aid = _alert_id("PUBLIC_EXPOSURE_NO_ENCRYPTION", arn)
                alerts.append({
                    "id": aid,
                    "rule_id": "PUBLIC_EXPOSURE_NO_ENCRYPTION",
                    "title": f"Public Exposure + Missing Encryption: {arn.split(':')[-1] or arn[:40]}",
                    "description": "A resource has both public exposure and missing encryption findings, creating a high data breach risk.",
                    "severity": "critical",
                    "confidence": 0.92,
                    "tactic": "Collection",
                    "technique": "T1530",
                    "risk_score": _risk("critical", 0.92),
                    "status": "open",
                    "affected_resources": [_resource(flist[0])],
                    "finding_ids": [str(f.id) for f in flist],
                    "detected_at": _now(),
                    "evidence": f"Resource has {len(flist)} correlated findings covering public accessibility and encryption gaps.",
                })
        return alerts

    def _rule_priv_esc_iam(
        self, findings: list[CanonicalFinding], edges: list[SecurityGraphEdge]
    ) -> list[dict]:
        alerts = []
        esc_edges = [
            e for e in edges
            if e.edge_type in {"PRIVILEGE_ESCALATION_PATH", "PRIVILEGE_ESCALATION_TO", "USES_ADMIN_ROLE"}
        ]
        if not esc_edges:
            return alerts

        iam_findings = [
            f for f in findings
            if f.status == "open"
            and any(kw in (f.title or "").lower() for kw in ("iam", "role", "policy", "privilege", "escalat"))
        ]
        if not iam_findings:
            return alerts

        for edge in esc_edges[:5]:  # cap at 5 alerts per rule
            f = iam_findings[0]
            aid = _alert_id("PRIVILEGE_ESCALATION_CRITICAL_IAM", str(edge.id))
            alerts.append({
                "id": aid,
                "rule_id": "PRIVILEGE_ESCALATION_CRITICAL_IAM",
                "title": "Privilege Escalation Path with Open IAM Finding",
                "description": "A privilege escalation path exists in the IAM graph and is correlated with an open IAM security finding.",
                "severity": "critical",
                "confidence": 0.95,
                "tactic": "Privilege Escalation",
                "technique": "T1078.004",
                "risk_score": _risk("critical", 0.95),
                "status": "open",
                "affected_resources": [_resource(f)],
                "finding_ids": [str(f.id)],
                "detected_at": _now(),
                "evidence": f"Graph edge type '{edge.edge_type}' detected alongside open IAM finding: '{f.title}'.",
            })
        return alerts

    def _rule_admin_internet_facing(self, nodes: list[SecurityGraphNode]) -> list[dict]:
        alerts = []
        for node in nodes:
            if node.node_type not in {"iam_role", "iam_user"}:
                continue
            if not node.is_internet_facing:
                continue
            props = {}
            if node.properties:
                try:
                    import json
                    props = json.loads(node.properties) if isinstance(node.properties, str) else node.properties
                except Exception:
                    pass
            scope = props.get("permission_scope", "unknown")
            if scope not in {"admin", "write"}:
                continue
            aid = _alert_id("ADMIN_ENTITY_INTERNET_FACING", str(node.id))
            alerts.append({
                "id": aid,
                "rule_id": "ADMIN_ENTITY_INTERNET_FACING",
                "title": f"Internet-Facing {node.node_type.replace('iam_', 'IAM ').title()} with {scope.title()} Permissions",
                "description": f"IAM entity '{node.name}' has {scope} permissions and is marked internet-facing, enabling direct cloud control plane abuse.",
                "severity": "high",
                "confidence": 0.88,
                "tactic": "Persistence",
                "technique": "T1078",
                "risk_score": _risk("high", 0.88),
                "status": "open",
                "affected_resources": [{"arn": str(node.resource_arn or ""), "type": node.node_type, "region": str(node.region or "")}],
                "finding_ids": [],
                "detected_at": _now(),
                "evidence": f"Node '{node.name}' (type={node.node_type}, scope={scope}) is_internet_facing=True.",
            })
        return alerts

    def _rule_multi_severity_stack(self, findings: list[CanonicalFinding]) -> list[dict]:
        alerts = []
        open_f = [f for f in findings if f.status == "open"]
        by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in open_f:
            arn = str(f.resource_arn or "")
            if arn:
                by_arn.setdefault(arn, []).append(f)

        for arn, flist in by_arn.items():
            sevs = {f.severity for f in flist}
            if {"critical", "high", "medium"}.issubset(sevs):
                aid = _alert_id("MULTI_SEVERITY_STACK", arn)
                alerts.append({
                    "id": aid,
                    "rule_id": "MULTI_SEVERITY_STACK",
                    "title": f"Multi-Severity Finding Stack: {arn.split(':')[-1] or arn[:40]}",
                    "description": f"Resource has {len(flist)} open findings spanning critical, high, and medium severity — indicating a compounding risk profile.",
                    "severity": "high",
                    "confidence": 0.85,
                    "tactic": "Defense Evasion",
                    "technique": "T1562",
                    "risk_score": _risk("high", 0.85),
                    "status": "open",
                    "affected_resources": [_resource(flist[0])],
                    "finding_ids": [str(f.id) for f in flist],
                    "detected_at": _now(),
                    "evidence": f"Severities present: {', '.join(sorted(sevs))}. {len(flist)} total open findings on same resource.",
                })
        return alerts

    def _rule_sla_overdue_critical(self, findings: list[CanonicalFinding]) -> list[dict]:
        alerts = []
        now = datetime.now(UTC)
        for f in findings:
            if f.severity != "critical" or f.status != "open":
                continue
            first = _parse_dt(f.first_seen_at)
            if first is None:
                continue
            age_hours = (now - first).total_seconds() / 3600
            if age_hours > 24:
                aid = _alert_id("SLA_OVERDUE_CRITICAL", str(f.id))
                alerts.append({
                    "id": aid,
                    "rule_id": "SLA_OVERDUE_CRITICAL",
                    "title": f"Critical Finding Overdue SLA: {(f.title or '')[:60]}",
                    "description": f"Critical finding has been open for {int(age_hours)}h, exceeding the 24-hour SLA threshold.",
                    "severity": "high",
                    "confidence": 0.90,
                    "tactic": "Persistence",
                    "technique": "T1098",
                    "risk_score": _risk("high", 0.90),
                    "status": "open",
                    "affected_resources": [_resource(f)],
                    "finding_ids": [str(f.id)],
                    "detected_at": _now(),
                    "evidence": f"First seen: {first.isoformat()}. Age: {int(age_hours)}h. SLA limit: 24h.",
                })
        return alerts

    def _rule_unencrypted_public_data(self, findings: list[CanonicalFinding]) -> list[dict]:
        alerts = []
        seen: set[str] = set()
        for f in findings:
            if f.status != "open":
                continue
            title = (f.title or "").lower()
            if ("encrypt" in title or "kms" in title or "sse" in title) and \
               ("public" in title or "accessible" in title):
                aid = _alert_id("UNENCRYPTED_PUBLIC_DATA", str(f.id))
                if aid in seen:
                    continue
                seen.add(aid)
                alerts.append({
                    "id": aid,
                    "rule_id": "UNENCRYPTED_PUBLIC_DATA",
                    "title": f"Unencrypted Data Publicly Accessible: {f.resource_type or 'resource'}",
                    "description": "A single finding indicates both missing encryption and public accessibility for the same resource.",
                    "severity": "critical",
                    "confidence": 0.93,
                    "tactic": "Exfiltration",
                    "technique": "T1537",
                    "risk_score": _risk("critical", 0.93),
                    "status": "open",
                    "affected_resources": [_resource(f)],
                    "finding_ids": [str(f.id)],
                    "detected_at": _now(),
                    "evidence": f"Finding '{f.title}' combines public access and encryption gap signals.",
                })
        return alerts

    def _rule_identity_gap_exposure(
        self, findings: list[CanonicalFinding], nodes: list[SecurityGraphNode]
    ) -> list[dict]:
        alerts = []
        # Nodes with no MFA
        no_mfa_nodes = []
        for node in nodes:
            if node.node_type not in {"iam_user", "iam_role"}:
                continue
            props = {}
            if node.properties:
                try:
                    import json
                    props = json.loads(node.properties) if isinstance(node.properties, str) else node.properties
                except Exception:
                    pass
            if props.get("has_mfa") is False or props.get("mfa_enabled") is False:
                no_mfa_nodes.append(node)

        if not no_mfa_nodes:
            return alerts

        high_sev_open = [
            f for f in findings
            if f.status == "open" and f.severity in {"critical", "high"}
            and any(kw in (f.title or "").lower() for kw in ("iam", "user", "role", "credential", "mfa", "access key"))
        ]
        if not high_sev_open:
            return alerts

        for node in no_mfa_nodes[:3]:
            f = high_sev_open[0]
            aid = _alert_id("IDENTITY_GAP_EXPOSURE", str(node.id))
            alerts.append({
                "id": aid,
                "rule_id": "IDENTITY_GAP_EXPOSURE",
                "title": f"Identity Gap: {node.name} Has No MFA + Open High/Critical Finding",
                "description": f"IAM entity '{node.name}' has no MFA enabled and is correlated with a high-severity security finding.",
                "severity": "high",
                "confidence": 0.82,
                "tactic": "Credential Access",
                "technique": "T1556",
                "risk_score": _risk("high", 0.82),
                "status": "open",
                "affected_resources": [{"arn": str(node.resource_arn or ""), "type": node.node_type, "region": str(node.region or "")}],
                "finding_ids": [str(f.id)],
                "detected_at": _now(),
                "evidence": f"Node '{node.name}' has no MFA. Correlated finding: '{f.title}'.",
            })
        return alerts

    # ── Public API ─────────────────────────────────────────────────────────────

    async def alerts(self, workspace_id: uuid.UUID) -> list[dict]:
        findings = await self._findings(workspace_id)
        nodes    = await self._nodes(workspace_id)
        edges    = await self._edges(workspace_id)

        all_alerts: list[dict] = []
        all_alerts.extend(self._rule_kev_cve_open(findings))
        all_alerts.extend(self._rule_public_no_encryption(findings))
        all_alerts.extend(self._rule_priv_esc_iam(findings, edges))
        all_alerts.extend(self._rule_admin_internet_facing(nodes))
        all_alerts.extend(self._rule_multi_severity_stack(findings))
        all_alerts.extend(self._rule_sla_overdue_critical(findings))
        all_alerts.extend(self._rule_unencrypted_public_data(findings))
        all_alerts.extend(self._rule_identity_gap_exposure(findings, nodes))

        # Deduplicate by id
        seen: set[str] = set()
        unique = []
        for a in all_alerts:
            if a["id"] not in seen:
                seen.add(a["id"])
                unique.append(a)

        # Sort by risk_score descending
        unique.sort(key=lambda x: x["risk_score"], reverse=True)
        return unique

    async def summary(self, workspace_id: uuid.UUID) -> dict[str, Any]:
        all_alerts = await self.alerts(workspace_id)
        open_alerts = [a for a in all_alerts if a["status"] == "open"]

        by_tactic: dict[str, int] = {}
        by_rule: dict[str, int]   = {}
        for a in all_alerts:
            by_tactic[a["tactic"]] = by_tactic.get(a["tactic"], 0) + 1
            by_rule[a["rule_id"]]  = by_rule.get(a["rule_id"], 0) + 1

        top_tactic = max(by_tactic, key=by_tactic.get) if by_tactic else ""
        confidences = [a["confidence"] for a in all_alerts]
        avg_conf = round(sum(confidences) / len(confidences), 3) if confidences else 0.0

        return {
            "total_alerts":    len(all_alerts),
            "open_alerts":     len(open_alerts),
            "critical_count":  sum(1 for a in all_alerts if a["severity"] == "critical"),
            "high_count":      sum(1 for a in all_alerts if a["severity"] == "high"),
            "medium_count":    sum(1 for a in all_alerts if a["severity"] == "medium"),
            "avg_confidence":  avg_conf,
            "top_tactic":      top_tactic,
            "rules_fired":     len(by_rule),
            "by_tactic":       by_tactic,
            "by_rule":         by_rule,
        }
