"""
ASMModule — Attack Surface Management simulation.

Sprint 33: External exposure analysis:
1. Internet-facing asset enumeration
2. Shadow asset discovery
3. Exposure risk prioritization
4. Asset ownership resolution
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding
from app.models.security_graph_node import SecurityGraphNode
from app.models.security_graph_edge import SecurityGraphEdge

# ── Constants ─────────────────────────────────────────────────────────────────

# Node types that can be internet-facing
_INTERNET_FACING_NODE_TYPES = {
    "ec2", "lambda", "s3_bucket", "rds", "ecs_service",
    "eks_service", "api_gateway", "cloudfront", "elb", "alb", "nlb",
    "elasticache", "redshift",
}

# Keywords that indicate shadow / unmanaged asset signals
_SHADOW_ASSET_KEYWORDS = [
    "unmanaged", "unknown", "untagged", "no owner",
    "orphan", "unused", "stale", "deprecated",
    "no tags", "missing tags",
]

# Keywords that indicate external exposure in findings
_EXPOSURE_KEYWORDS = [
    "public", "internet", "0.0.0.0/0", "::/0",
    "open to world", "exposed", "unrestricted",
    "public access", "public ip", "globally accessible",
    "external", "ingress from any",
]

# Asset types that commonly house sensitive data
_SENSITIVE_ASSET_TYPES = {
    "s3_bucket", "rds", "dynamodb", "redshift",
    "secrets_manager", "elasticache", "efs",
}

# Protocol / port risk scoring
_HIGH_RISK_PORTS = {
    22: "SSH",
    23: "Telnet",
    3389: "RDP",
    3306: "MySQL",
    5432: "PostgreSQL",
    1433: "MSSQL",
    27017: "MongoDB",
    6379: "Redis",
    9200: "Elasticsearch",
    8080: "HTTP-alt",
    8443: "HTTPS-alt",
}

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}


def _parse_json(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return None


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw.lower() in lower]


# ── Service ───────────────────────────────────────────────────────────────────

class ASMModule:
    """Attack Surface Management — enumerates, classifies, and prioritizes
    external exposure across workspace cloud assets."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _internet_facing_nodes(
        self, workspace_id: uuid.UUID,
    ) -> list[SecurityGraphNode]:
        q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id,
            SecurityGraphNode.is_internet_facing == True,  # noqa: E712
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _all_nodes(
        self, workspace_id: uuid.UUID,
    ) -> list[SecurityGraphNode]:
        q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id,
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _all_findings(
        self, workspace_id: uuid.UUID,
    ) -> list[CanonicalFinding]:
        q = select(CanonicalFinding).where(
            CanonicalFinding.workspace_id == workspace_id,
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _all_edges(
        self, workspace_id: uuid.UUID,
    ) -> list[SecurityGraphEdge]:
        q = select(SecurityGraphEdge).where(
            SecurityGraphEdge.workspace_id == workspace_id,
        )
        return list((await self.db.execute(q)).scalars().all())

    def _resolve_owner(self, node: SecurityGraphNode) -> dict:
        """Attempt to resolve asset ownership from metadata and tags."""
        meta = _parse_json(node.node_metadata) or {}
        tags = meta.get("tags", {})
        if isinstance(tags, list):
            # Convert list of {Key, Value} to dict
            tags = {t.get("Key", ""): t.get("Value", "") for t in tags if isinstance(t, dict)}

        owner = (
            tags.get("Owner")
            or tags.get("owner")
            or tags.get("Team")
            or tags.get("team")
            or meta.get("owner")
            or None
        )
        department = (
            tags.get("Department")
            or tags.get("department")
            or tags.get("BusinessUnit")
            or tags.get("business_unit")
            or None
        )
        environment = (
            tags.get("Environment")
            or tags.get("environment")
            or tags.get("Env")
            or tags.get("env")
            or meta.get("environment")
            or None
        )

        return {
            "owner": owner,
            "department": department,
            "environment": environment,
            "has_owner": owner is not None,
            "tag_count": len(tags),
        }

    def _exposure_severity(
        self,
        node: SecurityGraphNode,
        finding_count: int,
        has_sensitive_data: bool,
        exposed_ports: list[dict],
    ) -> str:
        """Calculate exposure severity based on multiple signals."""
        score = 0

        # Internet-facing with sensitive data
        if node.is_internet_facing and has_sensitive_data:
            score += 4

        # High-risk ports exposed
        high_risk_port_count = sum(
            1 for p in exposed_ports if p.get("is_high_risk")
        )
        score += min(high_risk_port_count * 2, 4)

        # Open findings
        score += min(finding_count, 3)

        # Risk score from graph
        if node.risk_score and node.risk_score >= 8:
            score += 2
        elif node.risk_score and node.risk_score >= 5:
            score += 1

        if score >= 8:
            return "critical"
        if score >= 5:
            return "high"
        if score >= 3:
            return "medium"
        return "low"

    # ── Public API ───────────────────────────────────────────────────────

    async def enumerate_exposure(self, workspace_id: uuid.UUID) -> dict:
        """Enumerate all internet-facing assets.

        Queries SecurityGraphNode where is_internet_facing is True,
        correlates with findings, and enriches with ownership data.
        """
        internet_nodes = await self._internet_facing_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        edges = await self._all_edges(workspace_id)
        all_nodes = await self._all_nodes(workspace_id)

        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        # Index findings by ARN
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in all_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        # Also scan findings and edges for nodes that expose resources but
        # aren't flagged is_internet_facing (potential additional exposures)
        additional_exposed_ids: set[uuid.UUID] = set()
        for f in all_findings:
            if f.status not in ("open", "in_progress"):
                continue
            text = f"{f.title} {f.description or ''}".lower()
            if any(kw in text for kw in _EXPOSURE_KEYWORDS):
                # Find matching node by resource_arn
                for n in all_nodes:
                    if n.resource_arn and n.resource_arn == f.resource_arn:
                        additional_exposed_ids.add(n.id)

        # Merge: add any additional exposed nodes not already internet-facing
        internet_node_ids = {n.id for n in internet_nodes}
        for node in all_nodes:
            if node.id in additional_exposed_ids and node.id not in internet_node_ids:
                internet_nodes.append(node)

        assets: list[dict] = []

        for node in internet_nodes:
            meta = _parse_json(node.node_metadata) or {}
            arn = node.resource_arn or ""

            # Gather linked findings
            linked_findings = findings_by_arn.get(arn, [])
            finding_ids = {str(fid) for fid in (_parse_json(node.finding_ids) or [])}
            for f in all_findings:
                if str(f.id) in finding_ids and f not in linked_findings:
                    linked_findings.append(f)

            open_findings = [
                f for f in linked_findings if f.status in ("open", "in_progress")
            ]

            # Extract exposed ports from metadata or edge metadata
            exposed_ports: list[dict] = []
            for port_info in meta.get("open_ports", meta.get("ports", [])):
                if isinstance(port_info, dict):
                    port_num = port_info.get("port", 0)
                    exposed_ports.append({
                        "port": port_num,
                        "protocol": port_info.get("protocol", "tcp"),
                        "service": _HIGH_RISK_PORTS.get(port_num, port_info.get("service", "unknown")),
                        "is_high_risk": port_num in _HIGH_RISK_PORTS,
                    })
                elif isinstance(port_info, int):
                    exposed_ports.append({
                        "port": port_info,
                        "protocol": "tcp",
                        "service": _HIGH_RISK_PORTS.get(port_info, "unknown"),
                        "is_high_risk": port_info in _HIGH_RISK_PORTS,
                    })

            # Also check edge metadata for port exposure
            for edge in edges:
                if edge.source_node_id == node.id or edge.target_node_id == node.id:
                    edge_meta = _parse_json(edge.edge_metadata) or {}
                    if "port" in edge_meta:
                        port_num = edge_meta["port"]
                        if not any(p["port"] == port_num for p in exposed_ports):
                            exposed_ports.append({
                                "port": port_num,
                                "protocol": edge_meta.get("protocol", "tcp"),
                                "service": _HIGH_RISK_PORTS.get(port_num, "unknown"),
                                "is_high_risk": port_num in _HIGH_RISK_PORTS,
                            })

            has_sensitive = bool(node.is_sensitive_data) or node.node_type in _SENSITIVE_ASSET_TYPES
            ownership = self._resolve_owner(node)
            severity = self._exposure_severity(node, len(open_findings), has_sensitive, exposed_ports)

            # Determine exposure type
            exposure_types: list[str] = []
            if node.is_internet_facing:
                exposure_types.append("direct_internet")
            if node.id in additional_exposed_ids:
                exposure_types.append("finding_indicated")
            if exposed_ports:
                exposure_types.append("open_ports")
            if meta.get("public_access", False) or meta.get("public_ip"):
                exposure_types.append("public_access")

            assets.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "region": node.region,
                "severity": severity,
                "exposure_types": exposure_types,
                "is_sensitive_data": has_sensitive,
                "risk_score": node.risk_score,
                "open_finding_count": len(open_findings),
                "exposed_ports": exposed_ports,
                "high_risk_port_count": sum(1 for p in exposed_ports if p.get("is_high_risk")),
                "ownership": ownership,
            })

        # Sort: critical first, then risk score
        assets.sort(key=lambda a: (
            _SEVERITY_ORDER.get(a["severity"], 5),
            -(a["risk_score"] or 0),
            -a["open_finding_count"],
        ))

        return {
            "total_exposed_assets": len(assets),
            "severity_breakdown": {
                sev: sum(1 for a in assets if a["severity"] == sev)
                for sev in ("critical", "high", "medium", "low")
            },
            "assets_with_sensitive_data": sum(1 for a in assets if a["is_sensitive_data"]),
            "assets_without_owner": sum(1 for a in assets if not a["ownership"]["has_owner"]),
            "exposed_assets": assets,
        }

    async def shadow_assets(self, workspace_id: uuid.UUID) -> dict:
        """Identify potential shadow/unmanaged assets.

        Detects assets that lack ownership tags, have stale configurations,
        or are not part of any known deployment/infrastructure-as-code stack.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in all_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        shadow_candidates: list[dict] = []

        for node in all_nodes:
            meta = _parse_json(node.node_metadata) or {}
            ownership = self._resolve_owner(node)

            shadow_signals: list[str] = []

            # No owner tags
            if not ownership["has_owner"]:
                shadow_signals.append("no_owner_tag")

            # Very few tags (likely unmanaged)
            if ownership["tag_count"] < 2:
                shadow_signals.append("insufficient_tags")

            # No CloudFormation / Terraform stack reference
            tags = meta.get("tags", {})
            if isinstance(tags, list):
                tags = {t.get("Key", ""): t.get("Value", "") for t in tags if isinstance(t, dict)}
            has_iac_tag = any(
                k.lower() in ("aws:cloudformation:stack-name", "terraform", "pulumi", "cdk")
                for k in tags
            )
            if not has_iac_tag:
                shadow_signals.append("no_iac_reference")

            # Check findings for shadow indicators
            arn = node.resource_arn or ""
            linked_findings = findings_by_arn.get(arn, [])
            for f in linked_findings:
                text = f"{f.title} {f.description or ''}".lower()
                matched = _match_keywords(text, _SHADOW_ASSET_KEYWORDS)
                if matched:
                    shadow_signals.extend(matched[:2])

            # Check metadata for staleness
            if meta.get("state") in ("stopped", "terminated", "unused"):
                shadow_signals.append("inactive_state")

            # Only include if at least 2 shadow signals
            if len(shadow_signals) < 2:
                continue

            # Determine confidence level
            signal_count = len(set(shadow_signals))
            if signal_count >= 4:
                confidence = "high"
                severity = "high"
            elif signal_count >= 3:
                confidence = "medium"
                severity = "medium"
            else:
                confidence = "low"
                severity = "low"

            # Elevate severity if internet-facing shadow asset
            if node.is_internet_facing and severity != "critical":
                severity = "critical" if confidence == "high" else "high"

            shadow_candidates.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "region": node.region,
                "shadow_signals": list(set(shadow_signals)),
                "signal_count": signal_count,
                "confidence": confidence,
                "severity": severity,
                "is_internet_facing": bool(node.is_internet_facing),
                "risk_score": node.risk_score,
                "ownership": ownership,
            })

        shadow_candidates.sort(key=lambda s: (
            _SEVERITY_ORDER.get(s["severity"], 5),
            -s["signal_count"],
            -(s["risk_score"] or 0),
        ))

        return {
            "total_shadow_candidates": len(shadow_candidates),
            "high_confidence": sum(1 for s in shadow_candidates if s["confidence"] == "high"),
            "medium_confidence": sum(1 for s in shadow_candidates if s["confidence"] == "medium"),
            "internet_facing_shadow": sum(
                1 for s in shadow_candidates if s["is_internet_facing"]
            ),
            "shadow_assets": shadow_candidates,
        }

    async def prioritize_exposures(self, workspace_id: uuid.UUID) -> dict:
        """Risk-rank all exposures by combining enumeration and shadow data.

        Produces a unified, prioritized list of all external exposure risks
        across the workspace with remediation priority scores.
        """
        enum_result = await self.enumerate_exposure(workspace_id)
        shadow_result = await self.shadow_assets(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        # Merge exposed assets and shadow assets into a unified risk list
        seen_ids: set[str] = set()
        prioritized: list[dict] = []

        for asset in enum_result["exposed_assets"]:
            asset_id = asset["id"]
            if asset_id in seen_ids:
                continue
            seen_ids.add(asset_id)

            # Calculate priority score (0-100)
            priority_score = 0.0

            # Severity contribution (40 pts max)
            sev_scores = {"critical": 40, "high": 30, "medium": 20, "low": 10}
            priority_score += sev_scores.get(asset["severity"], 0)

            # Risk score contribution (20 pts max)
            priority_score += min((asset["risk_score"] or 0) * 2, 20)

            # Finding count contribution (20 pts max)
            priority_score += min(asset["open_finding_count"] * 4, 20)

            # Sensitive data bonus (10 pts)
            if asset["is_sensitive_data"]:
                priority_score += 10

            # No owner penalty (10 pts)
            if not asset["ownership"]["has_owner"]:
                priority_score += 10

            prioritized.append({
                "id": asset_id,
                "name": asset["name"],
                "node_type": asset["node_type"],
                "resource_arn": asset["resource_arn"],
                "region": asset["region"],
                "source": "exposure",
                "severity": asset["severity"],
                "priority_score": min(round(priority_score, 1), 100),
                "risk_score": asset["risk_score"],
                "is_sensitive_data": asset["is_sensitive_data"],
                "open_finding_count": asset["open_finding_count"],
                "ownership": asset["ownership"],
                "exposure_types": asset.get("exposure_types", []),
            })

        for shadow in shadow_result["shadow_assets"]:
            asset_id = shadow["id"]
            if asset_id in seen_ids:
                # Merge shadow signals into existing entry
                for p in prioritized:
                    if p["id"] == asset_id:
                        p["source"] = "both"
                        p["shadow_signals"] = shadow["shadow_signals"]
                        p["priority_score"] = min(p["priority_score"] + 10, 100)
                        break
                continue
            seen_ids.add(asset_id)

            priority_score = 0.0
            sev_scores = {"critical": 40, "high": 30, "medium": 20, "low": 10}
            priority_score += sev_scores.get(shadow["severity"], 0)
            priority_score += min((shadow["risk_score"] or 0) * 2, 20)
            priority_score += shadow["signal_count"] * 5
            if shadow["is_internet_facing"]:
                priority_score += 15

            prioritized.append({
                "id": asset_id,
                "name": shadow["name"],
                "node_type": shadow["node_type"],
                "resource_arn": shadow["resource_arn"],
                "region": shadow["region"],
                "source": "shadow",
                "severity": shadow["severity"],
                "priority_score": min(round(priority_score, 1), 100),
                "risk_score": shadow["risk_score"],
                "is_sensitive_data": False,
                "open_finding_count": 0,
                "ownership": shadow["ownership"],
                "shadow_signals": shadow["shadow_signals"],
            })

        # Sort by priority score descending
        prioritized.sort(key=lambda p: -p["priority_score"])

        # Severity distribution
        open_count = sum(
            1 for f in all_findings if f.status in ("open", "in_progress")
        )

        return {
            "total_prioritized_exposures": len(prioritized),
            "critical_count": sum(1 for p in prioritized if p["severity"] == "critical"),
            "high_count": sum(1 for p in prioritized if p["severity"] == "high"),
            "medium_count": sum(1 for p in prioritized if p["severity"] == "medium"),
            "total_open_findings": open_count,
            "exposures_from_enumeration": sum(
                1 for p in prioritized if p["source"] in ("exposure", "both")
            ),
            "exposures_from_shadow": sum(
                1 for p in prioritized if p["source"] in ("shadow", "both")
            ),
            "prioritized_exposures": prioritized,
        }
