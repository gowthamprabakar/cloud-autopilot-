"""
CIEMService — Cloud Identity & Entitlement Management.

Sprint 21 — CIEM Foundation.

Capabilities:
  1. IAM entity inventory  (roles, users from security_graph_nodes)
  2. Effective permission classification (admin / write / read / limited)
  3. Permission escalation detection — 5 key patterns:
       a. iam:PassRole          — role can pass itself to services
       b. iam:CreatePolicy      — can create arbitrary policies
       c. iam:AttachRolePolicy  — can attach admin-level managed policies
       d. iam:PutRolePolicy     — can inject inline policies
       e. sts:AssumeRole        — broad cross-account assumption
     Detection uses both graph edge types AND finding descriptions.
  4. Cross-account trust analysis  (CAN_ASSUME / CAN_BE_ASSUMED_BY edges)
  5. Summary statistics for the CIEM dashboard
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding
from app.models.security_graph_node import SecurityGraphNode
from app.models.security_graph_edge import SecurityGraphEdge

# ── Constants ─────────────────────────────────────────────────────────────────

_IAM_NODE_TYPES = {"iam_role", "iam_user", "iam_group", "iam_policy"}

_ESCALATION_EDGE_TYPES = {
    "PRIVILEGE_ESCALATION_PATH",
    "PRIVILEGE_ESCALATION_TO",
    "USES_ADMIN_ROLE",
}

_CROSS_ACCOUNT_EDGE_TYPES = {
    "CAN_ASSUME",
    "CAN_BE_ASSUMED_BY",
}

# Patterns in finding titles/descriptions that indicate escalation risk
_ESCALATION_KEYWORDS = [
    "iam:PassRole",
    "iam:CreatePolicy",
    "iam:AttachRolePolicy",
    "iam:PutRolePolicy",
    "sts:AssumeRole",
    "privilege escalation",
    "admin",
    "iam:CreateRole",
    "iam:*",
    "AdministratorAccess",
]

_PERMISSION_SCOPE_ORDER = ["admin", "write", "read", "limited", "unknown"]

_ESCALATION_RISK_COLOR = {
    "critical": "bg-red-100 text-red-700",
    "high":     "bg-orange-100 text-orange-700",
    "medium":   "bg-yellow-100 text-yellow-700",
    "low":      "bg-blue-100 text-blue-700",
}


def _parse_json(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return None


def _escalation_risk_from_score(score: float | None) -> str:
    if score is None:
        return "low"
    if score >= 9.0:
        return "critical"
    if score >= 7.0:
        return "high"
    if score >= 5.0:
        return "medium"
    return "low"


# ── Service ───────────────────────────────────────────────────────────────────

class CIEMService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Entity helpers ──────────────────────────────────────────────────────

    async def _iam_nodes(self, workspace_id: uuid.UUID) -> list[SecurityGraphNode]:
        q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id,
            SecurityGraphNode.node_type.in_(list(_IAM_NODE_TYPES)),
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _all_edges(self, workspace_id: uuid.UUID) -> list[SecurityGraphEdge]:
        q = select(SecurityGraphEdge).where(
            SecurityGraphEdge.workspace_id == workspace_id
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _iam_findings(self, workspace_id: uuid.UUID) -> list[CanonicalFinding]:
        q = select(CanonicalFinding).where(
            CanonicalFinding.workspace_id == workspace_id,
            CanonicalFinding.resource_type.like("AWS::IAM%"),
        )
        return list((await self.db.execute(q)).scalars().all())

    # ── Escalation detection ────────────────────────────────────────────────

    def _node_has_escalation_finding(
        self,
        node: SecurityGraphNode,
        findings_by_arn: dict[str, list[CanonicalFinding]],
        all_findings: list[CanonicalFinding],
    ) -> tuple[bool, list[str]]:
        """Check if the node's linked findings indicate privilege escalation."""
        found_patterns: list[str] = []

        # Check via resource_arn match
        arn = node.resource_arn or ""
        matched = findings_by_arn.get(arn, [])

        # Also check via finding_ids
        finding_id_list = _parse_json(node.finding_ids) or []
        id_set = {str(fid) for fid in finding_id_list}
        for f in all_findings:
            if str(f.id) in id_set:
                matched.append(f)

        for f in matched:
            text = f"{f.title} {f.description or ''}".lower()
            for kw in _ESCALATION_KEYWORDS:
                if kw.lower() in text:
                    found_patterns.append(kw)

        return bool(found_patterns), list(set(found_patterns))

    def _node_has_escalation_edge(
        self,
        node: SecurityGraphNode,
        edges: list[SecurityGraphEdge],
        node_id_map: dict[uuid.UUID, SecurityGraphNode],
    ) -> tuple[bool, list[str]]:
        """Check if any edges from/to this node represent escalation paths."""
        paths: list[str] = []
        for edge in edges:
            if edge.edge_type not in _ESCALATION_EDGE_TYPES:
                continue
            if edge.source_node_id == node.id:
                target = node_id_map.get(edge.target_node_id)
                target_name = target.resource_name if target else "unknown"
                paths.append(f"{edge.edge_type} → {target_name}")
            elif edge.target_node_id == node.id:
                source = node_id_map.get(edge.source_node_id)
                source_name = source.resource_name if source else "unknown"
                paths.append(f"{source_name} → {edge.edge_type}")
        return bool(paths), paths

    # ── Cross-account trust ─────────────────────────────────────────────────

    def _cross_account_edges(
        self,
        edges: list[SecurityGraphEdge],
        node_id_map: dict[uuid.UUID, SecurityGraphNode],
    ) -> list[dict]:
        results = []
        for edge in edges:
            if edge.edge_type not in _CROSS_ACCOUNT_EDGE_TYPES:
                continue
            src = node_id_map.get(edge.source_node_id)
            tgt = node_id_map.get(edge.target_node_id)
            if not src or not tgt:
                continue
            results.append({
                "edge_type": edge.edge_type,
                "source": src.resource_name or str(src.id),
                "source_type": src.node_type,
                "target": tgt.resource_name or str(tgt.id),
                "target_type": tgt.node_type,
                "risk_contribution": edge.risk_contribution,
                "is_attack_path": bool(edge.is_attack_path),
            })
        return results

    # ── Public API ──────────────────────────────────────────────────────────

    async def entities(self, workspace_id: uuid.UUID) -> list[dict]:
        """Return enriched IAM entity list."""
        nodes = await self._iam_nodes(workspace_id)
        edges = await self._all_edges(workspace_id)
        iam_findings = await self._iam_findings(workspace_id)
        all_findings_q = select(CanonicalFinding).where(
            CanonicalFinding.workspace_id == workspace_id
        )
        all_findings = list((await self.db.execute(all_findings_q)).scalars().all())

        node_id_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in
            list((await self.db.execute(
                select(SecurityGraphNode).where(SecurityGraphNode.workspace_id == workspace_id)
            )).scalars().all())
        }

        # Build findings by ARN index
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in iam_findings:
            arn = f.resource_arn or ""
            findings_by_arn.setdefault(arn, []).append(f)

        result = []
        for node in nodes:
            meta = _parse_json(node.metadata) or {}
            permission_scope = meta.get("permission_scope", "unknown")
            has_mfa = meta.get("has_mfa", None)
            cross_account = meta.get("cross_account", False)
            policies = meta.get("policies", [])

            esc_finding, esc_patterns = self._node_has_escalation_finding(
                node, findings_by_arn, all_findings
            )
            esc_edge, esc_edge_paths = self._node_has_escalation_edge(
                node, edges, node_id_map
            )

            has_escalation = esc_finding or esc_edge
            escalation_patterns = list(set(esc_patterns + esc_edge_paths))
            escalation_risk = _escalation_risk_from_score(node.risk_score)
            if not has_escalation and escalation_risk in ("critical", "high"):
                # Downgrade if no actual escalation signal
                escalation_risk = "medium" if node.risk_score and node.risk_score >= 7 else "low"
            if has_escalation:
                # Upgrade risk based on pattern count
                if len(escalation_patterns) >= 3:
                    escalation_risk = "critical"
                elif len(escalation_patterns) >= 1:
                    escalation_risk = max(escalation_risk, "high",
                                          key=lambda x: ["low","medium","high","critical"].index(x))

            result.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "type": node.node_type,
                "resource_arn": node.resource_arn,
                "region": node.region,
                "risk_score": node.risk_score,
                "is_internet_facing": bool(node.is_internet_facing),
                "is_sensitive_data": bool(node.is_sensitive_data),
                "permission_scope": permission_scope,
                "has_mfa": has_mfa,
                "cross_account": cross_account,
                "policies": policies,
                "has_escalation": has_escalation,
                "escalation_risk": escalation_risk,
                "escalation_patterns": escalation_patterns[:5],
                "open_findings": len([
                    f for f in all_findings
                    if str(f.id) in {str(fid) for fid in (_parse_json(node.finding_ids) or [])}
                    and f.status in ("open", "in_progress")
                ]),
            })

        # Sort: internet-facing first, then by risk_score desc
        result.sort(key=lambda e: (
            not e["is_internet_facing"],
            -(e["risk_score"] or 0),
        ))
        return result

    async def escalation_paths(self, workspace_id: uuid.UUID) -> list[dict]:
        """Return detected privilege escalation paths."""
        edges = await self._all_edges(workspace_id)
        all_nodes_q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id
        )
        all_nodes = list((await self.db.execute(all_nodes_q)).scalars().all())
        node_id_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        iam_findings = await self._iam_findings(workspace_id)
        all_findings_q = select(CanonicalFinding).where(
            CanonicalFinding.workspace_id == workspace_id
        )
        all_findings = list((await self.db.execute(all_findings_q)).scalars().all())

        paths = []

        # Graph-based escalation edges
        for edge in edges:
            if edge.edge_type in _ESCALATION_EDGE_TYPES | _CROSS_ACCOUNT_EDGE_TYPES:
                src = node_id_map.get(edge.source_node_id)
                tgt = node_id_map.get(edge.target_node_id)
                severity = "critical" if edge.is_attack_path else "high"
                paths.append({
                    "id": str(edge.id),
                    "type": "graph_edge",
                    "pattern": edge.edge_type,
                    "source": src.resource_name if src else "unknown",
                    "source_type": src.node_type if src else "unknown",
                    "target": tgt.resource_name if tgt else "unknown",
                    "target_type": tgt.node_type if tgt else "unknown",
                    "severity": severity,
                    "is_attack_path": bool(edge.is_attack_path),
                    "risk_contribution": edge.risk_contribution,
                })

        # Finding-based escalation signals
        for f in iam_findings:
            if f.status not in ("open", "in_progress"):
                continue
            text = f"{f.title} {f.description or ''}"
            matched_patterns = [kw for kw in _ESCALATION_KEYWORDS if kw.lower() in text.lower()]
            if not matched_patterns:
                continue
            paths.append({
                "id": str(f.id),
                "type": "finding",
                "pattern": matched_patterns[0],
                "source": f.resource_arn or f.title,
                "source_type": f.resource_type or "AWS::IAM",
                "target": "escalation_target",
                "target_type": "privilege",
                "severity": f.severity,
                "is_attack_path": f.risk_score is not None and f.risk_score >= 8.0,
                "risk_contribution": f.risk_score,
                "finding_title": f.title,
            })

        # Sort: attack paths first, then severity
        _sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        paths.sort(key=lambda p: (
            not p["is_attack_path"],
            _sev_order.get(p["severity"], 5),
            -(p["risk_contribution"] or 0),
        ))
        return paths

    async def summary(self, workspace_id: uuid.UUID) -> dict:
        """High-level CIEM summary for the dashboard header."""
        entities_list = await self.entities(workspace_id)
        paths_list = await self.escalation_paths(workspace_id)
        cross_account = await self._cross_account_summary(workspace_id)

        total = len(entities_list)
        roles = sum(1 for e in entities_list if e["type"] == "iam_role")
        users = sum(1 for e in entities_list if e["type"] == "iam_user")
        admin_entities = sum(1 for e in entities_list if e["permission_scope"] == "admin")
        internet_facing = sum(1 for e in entities_list if e["is_internet_facing"])
        no_mfa = sum(1 for e in entities_list if e["has_mfa"] is False)
        escalation_count = sum(1 for e in entities_list if e["has_escalation"])
        critical_paths = sum(1 for p in paths_list if p["severity"] == "critical")

        return {
            "total_entities": total,
            "roles": roles,
            "users": users,
            "admin_entities": admin_entities,
            "internet_facing_roles": internet_facing,
            "no_mfa_count": no_mfa,
            "escalation_paths_count": len(paths_list),
            "entities_with_escalation": escalation_count,
            "critical_paths": critical_paths,
            "cross_account_trusts": len(cross_account),
            "risk_breakdown": {
                "critical": sum(1 for e in entities_list if e["escalation_risk"] == "critical"),
                "high":     sum(1 for e in entities_list if e["escalation_risk"] == "high"),
                "medium":   sum(1 for e in entities_list if e["escalation_risk"] == "medium"),
                "low":      sum(1 for e in entities_list if e["escalation_risk"] == "low"),
            },
        }

    async def _cross_account_summary(self, workspace_id: uuid.UUID) -> list[dict]:
        edges = await self._all_edges(workspace_id)
        all_nodes_q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id
        )
        all_nodes = list((await self.db.execute(all_nodes_q)).scalars().all())
        node_id_map = {n.id: n for n in all_nodes}
        return self._cross_account_edges(edges, node_id_map)
