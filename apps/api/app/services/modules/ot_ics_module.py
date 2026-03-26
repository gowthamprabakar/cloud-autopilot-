"""
OTICSModule — OT/ICS Critical Infrastructure Convergence simulation.

Sprint 34: Simulates OT/ICS security:
1. Digital twin stress testing (PLC setpoint manipulation)
2. Air gap integrity validation
3. Industrial protocol whitelisting (Modbus/DNP3/IEC 104)
4. Engineering workstation isolation
5. Nation-state dwell time detection (Salt Typhoon, Sandworm)
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding
from app.models.security_graph_node import SecurityGraphNode
from app.models.security_graph_edge import SecurityGraphEdge

# ── Constants ─────────────────────────────────────────────────────────────────

# OT / ICS node types in the security graph
_OT_NODE_TYPES = {
    "plc", "scada", "hmi", "rtu", "dcs", "historian",
    "engineering_workstation", "ot_gateway", "ot_firewall",
    "iot_device", "iot_gateway",
}

# IT node types that could bridge into OT networks
_IT_BRIDGE_NODE_TYPES = {
    "ec2", "vpc", "subnet", "security_group", "lambda",
    "ecs_service", "eks_service", "api_gateway",
}

# Industrial protocols and their default ports
_INDUSTRIAL_PROTOCOLS: dict[str, dict[str, Any]] = {
    "modbus": {"port": 502, "risk": "high", "description": "Modbus TCP — no authentication"},
    "dnp3": {"port": 20000, "risk": "high", "description": "DNP3 — limited authentication"},
    "iec104": {"port": 2404, "risk": "high", "description": "IEC 60870-5-104 — SCADA telecontrol"},
    "opcua": {"port": 4840, "risk": "medium", "description": "OPC UA — supports encryption"},
    "ethernetip": {"port": 44818, "risk": "high", "description": "EtherNet/IP — CIP protocol"},
    "bacnet": {"port": 47808, "risk": "medium", "description": "BACnet — building automation"},
    "profinet": {"port": 34964, "risk": "high", "description": "PROFINET — Siemens industrial"},
    "s7comm": {"port": 102, "risk": "critical", "description": "S7comm — Siemens S7 PLC direct"},
}

# Nation-state APT groups with OT/ICS targeting history
_NATION_STATE_INDICATORS: dict[str, dict[str, Any]] = {
    "salt_typhoon": {
        "aliases": ["GhostEmperor", "FamousSparrow"],
        "origin": "China",
        "targets": ["telecom", "isp", "critical_infrastructure"],
        "ttps": [
            "living-off-the-land", "credential-harvesting",
            "network-infrastructure-compromise", "wiretap-capability",
        ],
        "dwell_time_days": 180,
        "indicators": [
            "unusual dns", "lateral movement", "credential dump",
            "persistence", "telecom", "network device",
        ],
    },
    "sandworm": {
        "aliases": ["Voodoo Bear", "IRIDIUM", "Electrum"],
        "origin": "Russia (GRU Unit 74455)",
        "targets": ["energy", "water", "ics", "scada"],
        "ttps": [
            "industroyer", "blackenergy", "notpetya",
            "cyclops-blink", "ot-protocol-exploitation",
        ],
        "dwell_time_days": 270,
        "indicators": [
            "plc", "scada", "hmi", "industrial", "energy",
            "power grid", "substation", "ics protocol",
        ],
    },
    "volt_typhoon": {
        "aliases": ["Vanguard Panda", "Bronze Silhouette"],
        "origin": "China",
        "targets": ["critical_infrastructure", "water", "energy", "transport"],
        "ttps": [
            "living-off-the-land", "ntds-dit-extraction",
            "pre-positioning", "router-botnet",
        ],
        "dwell_time_days": 365,
        "indicators": [
            "infrastructure", "water", "energy", "transport",
            "long dwell", "lotl", "living off the land",
        ],
    },
    "chernovite": {
        "aliases": ["CHERNOVITE"],
        "origin": "Unknown (state-sponsored)",
        "targets": ["ics", "safety_systems"],
        "ttps": [
            "pipedream", "incontroller", "ot-malware-framework",
            "plc-manipulation", "safety-system-targeting",
        ],
        "dwell_time_days": 120,
        "indicators": [
            "safety system", "sis", "plc manipulation",
            "setpoint", "pipedream", "incontroller",
        ],
    },
}

# Edge types that indicate IT/OT cross-network connectivity
_CROSS_NETWORK_EDGE_TYPES = {
    "connects_to", "has_access_to", "exposes",
    "reads_from", "writes_to", "manages",
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


def _text_matches(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return [kw for kw in keywords if kw.lower() in lower]


# ── Service ───────────────────────────────────────────────────────────────────


class OTICSModule:
    """OT/ICS Critical Infrastructure Convergence — simulates industrial
    control system security assessments including digital twin analysis,
    air gap validation, protocol whitelisting, and nation-state detection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helpers ─────────────────────────────────────────────────

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

    def _classify_node_zone(self, node: SecurityGraphNode) -> str:
        """Classify a node into Purdue model zones."""
        ntype = (node.node_type or "").lower()
        meta = _parse_json(node.node_metadata) or {}
        zone = meta.get("purdue_level", meta.get("zone", ""))

        if ntype in ("plc", "rtu", "dcs"):
            return "level1_basic_control"
        if ntype in ("scada", "hmi", "historian"):
            return "level2_supervisory"
        if ntype in ("engineering_workstation",):
            return "level3_operations"
        if ntype in ("ot_gateway", "ot_firewall"):
            return "dmz"
        if ntype in _IT_BRIDGE_NODE_TYPES:
            return "level4_enterprise_it"
        if ntype in ("iot_device", "iot_gateway"):
            return "level0_physical"
        if zone:
            return str(zone)
        return "level4_enterprise_it"

    def _extract_protocols(self, node: SecurityGraphNode) -> list[dict]:
        """Extract industrial protocol information from node metadata."""
        meta = _parse_json(node.node_metadata) or {}
        protocols: list[dict] = []

        # Check metadata for protocol references
        node_protocols = meta.get("protocols", meta.get("industrial_protocols", []))
        if isinstance(node_protocols, list):
            for proto in node_protocols:
                if isinstance(proto, str):
                    proto_lower = proto.lower()
                    if proto_lower in _INDUSTRIAL_PROTOCOLS:
                        info = _INDUSTRIAL_PROTOCOLS[proto_lower]
                        protocols.append({
                            "name": proto_lower,
                            "port": info["port"],
                            "risk": info["risk"],
                            "description": info["description"],
                        })
                elif isinstance(proto, dict):
                    protocols.append({
                        "name": proto.get("name", "unknown"),
                        "port": proto.get("port", 0),
                        "risk": proto.get("risk", "medium"),
                        "description": proto.get("description", ""),
                    })

        # Check open ports for known industrial protocol ports
        open_ports = meta.get("open_ports", meta.get("ports", []))
        existing_ports = {p["port"] for p in protocols}
        for port_info in open_ports:
            port_num = port_info if isinstance(port_info, int) else port_info.get("port", 0)
            for proto_name, proto_info in _INDUSTRIAL_PROTOCOLS.items():
                if port_num == proto_info["port"] and port_num not in existing_ports:
                    protocols.append({
                        "name": proto_name,
                        "port": port_num,
                        "risk": proto_info["risk"],
                        "description": proto_info["description"],
                    })
                    existing_ports.add(port_num)

        return protocols

    # ── Public API ───────────────────────────────────────────────────────

    async def digital_twin_assessment(self, workspace_id: uuid.UUID) -> dict:
        """Assess digital twin security posture for OT environments.

        Queries SecurityGraphNode for OT-typed assets, evaluates PLC/SCADA
        setpoint integrity, and analyses IT/OT convergence risk through
        edge relationships in the security graph.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        all_edges = await self._all_edges(workspace_id)

        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        # Index findings by resource ARN
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in all_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        # Identify OT nodes and IT nodes
        ot_nodes = [n for n in all_nodes if (n.node_type or "").lower() in _OT_NODE_TYPES]
        it_nodes = [n for n in all_nodes if (n.node_type or "").lower() in _IT_BRIDGE_NODE_TYPES]

        # If no explicit OT nodes, infer from metadata/findings
        if not ot_nodes:
            for node in all_nodes:
                meta = _parse_json(node.node_metadata) or {}
                combined = f"{node.resource_name or ''} {json.dumps(meta)}".lower()
                if any(kw in combined for kw in ("plc", "scada", "hmi", "ot", "ics", "industrial")):
                    ot_nodes.append(node)

        # Build per-asset assessment
        asset_assessments: list[dict] = []
        total_risk = 0.0

        for node in ot_nodes:
            meta = _parse_json(node.node_metadata) or {}
            zone = self._classify_node_zone(node)
            protocols = self._extract_protocols(node)
            arn = node.resource_arn or ""
            linked_findings = findings_by_arn.get(arn, [])
            open_findings = [f for f in linked_findings if f.status in ("open", "in_progress")]

            # Evaluate convergence risk: count edges from IT to this OT node
            it_connections: list[dict] = []
            for edge in all_edges:
                src = node_map.get(edge.source_node_id)
                tgt = node_map.get(edge.target_node_id)
                if not src or not tgt:
                    continue
                # IT -> OT connection
                if (edge.target_node_id == node.id
                        and (src.node_type or "").lower() in _IT_BRIDGE_NODE_TYPES):
                    it_connections.append({
                        "source_node": src.resource_name or str(src.id),
                        "source_type": src.node_type,
                        "edge_type": edge.edge_type,
                        "is_attack_path": bool(edge.is_attack_path),
                        "risk_contribution": edge.risk_contribution or 0.0,
                    })
                # OT -> IT connection (data exfil risk)
                if (edge.source_node_id == node.id
                        and (tgt.node_type or "").lower() in _IT_BRIDGE_NODE_TYPES):
                    it_connections.append({
                        "source_node": node.resource_name or str(node.id),
                        "target_node": tgt.resource_name or str(tgt.id),
                        "target_type": tgt.node_type,
                        "edge_type": edge.edge_type,
                        "direction": "ot_to_it",
                        "is_attack_path": bool(edge.is_attack_path),
                        "risk_contribution": edge.risk_contribution or 0.0,
                    })

            # Calculate per-asset risk score
            asset_risk = 0.0
            risk_factors: list[str] = []

            # High-risk protocols without encryption
            high_risk_protos = [p for p in protocols if p["risk"] in ("critical", "high")]
            if high_risk_protos:
                asset_risk += len(high_risk_protos) * 1.5
                risk_factors.append(f"{len(high_risk_protos)} high-risk industrial protocols")

            # IT connections to OT asset
            if it_connections:
                asset_risk += len(it_connections) * 2.0
                risk_factors.append(f"{len(it_connections)} IT/OT cross-connections")

            # Attack path edges
            attack_path_edges = [c for c in it_connections if c.get("is_attack_path")]
            if attack_path_edges:
                asset_risk += len(attack_path_edges) * 3.0
                risk_factors.append(f"{len(attack_path_edges)} active attack path edges")

            # Open findings
            critical_findings = [f for f in open_findings if f.severity == "critical"]
            high_findings = [f for f in open_findings if f.severity == "high"]
            asset_risk += len(critical_findings) * 2.5
            asset_risk += len(high_findings) * 1.5
            if critical_findings:
                risk_factors.append(f"{len(critical_findings)} critical findings")

            # Internet-facing OT asset (extremely dangerous)
            if node.is_internet_facing:
                asset_risk += 5.0
                risk_factors.append("internet-facing OT asset")

            # Setpoint manipulation indicators
            setpoint_risks: list[str] = []
            for f in open_findings:
                text = f"{f.title} {f.description or ''}".lower()
                if any(kw in text for kw in ("setpoint", "plc", "manipulation", "firmware", "configuration change")):
                    setpoint_risks.append(f.title or "")
            if setpoint_risks:
                asset_risk += len(setpoint_risks) * 2.0
                risk_factors.append(f"{len(setpoint_risks)} setpoint manipulation indicators")

            asset_risk = min(asset_risk, 10.0)
            total_risk += asset_risk

            asset_assessments.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "purdue_zone": zone,
                "risk_score": round(asset_risk, 1),
                "risk_factors": risk_factors,
                "industrial_protocols": protocols,
                "it_connections": it_connections[:10],
                "open_finding_count": len(open_findings),
                "critical_finding_count": len(critical_findings),
                "setpoint_manipulation_indicators": setpoint_risks[:5],
                "is_internet_facing": bool(node.is_internet_facing),
            })

        # Sort by risk descending
        asset_assessments.sort(key=lambda a: -a["risk_score"])

        # Convergence risk summary
        total_it_ot_edges = sum(len(a["it_connections"]) for a in asset_assessments)
        avg_risk = round(total_risk / len(asset_assessments), 1) if asset_assessments else 0.0

        # Recommendations
        recommendations: list[str] = []
        if total_it_ot_edges > 0:
            recommendations.append(
                f"Review {total_it_ot_edges} IT/OT cross-connections — "
                "enforce unidirectional data diodes where possible"
            )
        internet_facing_ot = [a for a in asset_assessments if a["is_internet_facing"]]
        if internet_facing_ot:
            recommendations.append(
                f"CRITICAL: {len(internet_facing_ot)} OT assets are internet-facing — "
                "isolate immediately behind air-gapped network segments"
            )
        high_risk_assets = [a for a in asset_assessments if a["risk_score"] >= 7.0]
        if high_risk_assets:
            recommendations.append(
                f"{len(high_risk_assets)} OT assets have risk score >= 7.0 — "
                "prioritise digital twin stress testing and firmware validation"
            )
        if not ot_nodes:
            recommendations.append(
                "No explicit OT/ICS assets detected — ensure OT asset inventory "
                "is populated in the security graph for full coverage"
            )

        return {
            "total_ot_assets": len(ot_nodes),
            "total_it_assets": len(it_nodes),
            "assessed_assets": len(asset_assessments),
            "average_risk_score": avg_risk,
            "total_it_ot_connections": total_it_ot_edges,
            "internet_facing_ot_count": len(internet_facing_ot),
            "severity_breakdown": {
                sev: sum(
                    1 for a in asset_assessments
                    if (a["risk_score"] >= 8.0 and sev == "critical")
                    or (6.0 <= a["risk_score"] < 8.0 and sev == "high")
                    or (4.0 <= a["risk_score"] < 6.0 and sev == "medium")
                    or (a["risk_score"] < 4.0 and sev == "low")
                )
                for sev in ("critical", "high", "medium", "low")
            },
            "recommendations": recommendations,
            "asset_assessments": asset_assessments,
        }

    async def air_gap_integrity(self, workspace_id: uuid.UUID) -> dict:
        """Validate air gap between IT and OT networks.

        Traverses SecurityGraphEdge relationships to detect any path from
        IT-zone nodes to OT-zone nodes, identifies jump host paths,
        shared credentials, and cross-network firewall rule violations.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_edges = await self._all_edges(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        # Classify nodes by zone
        ot_node_ids: set[uuid.UUID] = set()
        it_node_ids: set[uuid.UUID] = set()

        for node in all_nodes:
            zone = self._classify_node_zone(node)
            if zone in ("level0_physical", "level1_basic_control",
                        "level2_supervisory", "level3_operations"):
                ot_node_ids.add(node.id)
            elif zone == "level4_enterprise_it":
                it_node_ids.add(node.id)
            # DMZ nodes tracked separately for jump host detection

        # Detect direct IT->OT connections (air gap violations)
        violations: list[dict] = []
        for edge in all_edges:
            if edge.edge_type not in _CROSS_NETWORK_EDGE_TYPES:
                continue
            src = node_map.get(edge.source_node_id)
            tgt = node_map.get(edge.target_node_id)
            if not src or not tgt:
                continue

            src_is_it = edge.source_node_id in it_node_ids
            tgt_is_ot = edge.target_node_id in ot_node_ids
            src_is_ot = edge.source_node_id in ot_node_ids
            tgt_is_it = edge.target_node_id in it_node_ids

            if (src_is_it and tgt_is_ot) or (src_is_ot and tgt_is_it):
                edge_meta = _parse_json(edge.edge_metadata) or {}
                severity = "critical" if edge.is_attack_path else "high"
                violations.append({
                    "edge_id": str(edge.id),
                    "source_node": src.resource_name or str(src.id),
                    "source_type": src.node_type,
                    "source_zone": self._classify_node_zone(src),
                    "target_node": tgt.resource_name or str(tgt.id),
                    "target_type": tgt.node_type,
                    "target_zone": self._classify_node_zone(tgt),
                    "edge_type": edge.edge_type,
                    "is_attack_path": bool(edge.is_attack_path),
                    "risk_contribution": edge.risk_contribution or 0.0,
                    "severity": severity,
                    "metadata": edge_meta,
                })

        # Detect jump host patterns: IT -> DMZ -> OT (2-hop paths)
        jump_host_paths: list[dict] = []
        dmz_node_ids: set[uuid.UUID] = set()
        for node in all_nodes:
            if self._classify_node_zone(node) == "dmz":
                dmz_node_ids.add(node.id)

        # Build adjacency for BFS
        adjacency: dict[uuid.UUID, list[tuple[uuid.UUID, SecurityGraphEdge]]] = {}
        for edge in all_edges:
            if edge.edge_type in _CROSS_NETWORK_EDGE_TYPES:
                adjacency.setdefault(edge.source_node_id, []).append(
                    (edge.target_node_id, edge)
                )

        for it_id in it_node_ids:
            for next_id, edge1 in adjacency.get(it_id, []):
                if next_id not in dmz_node_ids:
                    continue
                for ot_id, edge2 in adjacency.get(next_id, []):
                    if ot_id not in ot_node_ids:
                        continue
                    it_node = node_map.get(it_id)
                    dmz_node = node_map.get(next_id)
                    ot_node = node_map.get(ot_id)
                    if it_node and dmz_node and ot_node:
                        jump_host_paths.append({
                            "it_node": it_node.resource_name or str(it_id),
                            "jump_host": dmz_node.resource_name or str(next_id),
                            "ot_node": ot_node.resource_name or str(ot_id),
                            "severity": "high",
                            "path": [
                                {"node": it_node.resource_name, "zone": "enterprise_it"},
                                {"node": dmz_node.resource_name, "zone": "dmz"},
                                {"node": ot_node.resource_name, "zone": "ot"},
                            ],
                        })

        # Detect shared credential indicators from findings
        shared_cred_findings: list[dict] = []
        for f in all_findings:
            if f.status not in ("open", "in_progress"):
                continue
            text = f"{f.title} {f.description or ''}".lower()
            if any(kw in text for kw in (
                "shared credential", "shared password", "cross-network",
                "same password", "credential reuse", "shared account",
                "jump host", "bastion", "rdp", "ssh",
            )):
                shared_cred_findings.append({
                    "finding_id": str(f.id),
                    "title": f.title,
                    "severity": f.severity,
                    "resource_arn": str(f.resource_arn or ""),
                })

        # Integrity score: 100 = perfect air gap, subtract for each violation
        integrity_score = 100.0
        integrity_score -= len(violations) * 15
        integrity_score -= len(jump_host_paths) * 10
        integrity_score -= len(shared_cred_findings) * 5
        integrity_score = max(integrity_score, 0.0)

        status = "intact"
        if integrity_score < 30:
            status = "compromised"
        elif integrity_score < 60:
            status = "degraded"
        elif integrity_score < 90:
            status = "minor_gaps"

        return {
            "integrity_score": round(integrity_score, 1),
            "status": status,
            "total_ot_nodes": len(ot_node_ids),
            "total_it_nodes": len(it_node_ids),
            "total_dmz_nodes": len(dmz_node_ids),
            "direct_violations": len(violations),
            "jump_host_paths_detected": len(jump_host_paths),
            "shared_credential_indicators": len(shared_cred_findings),
            "violations": violations,
            "jump_host_paths": jump_host_paths[:20],
            "shared_credentials": shared_cred_findings[:20],
        }

    async def protocol_whitelist(self, workspace_id: uuid.UUID) -> dict:
        """Audit industrial protocol whitelisting.

        Examines SecurityGraphNode metadata for Modbus, DNP3, IEC 104,
        and other industrial protocols. Cross-references with edge metadata
        for port/protocol information and findings for protocol misuse.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        all_edges = await self._all_edges(workspace_id)

        # Gather all detected protocols across nodes
        detected_protocols: dict[str, list[dict]] = {}
        nodes_with_protocols: list[dict] = []

        for node in all_nodes:
            protocols = self._extract_protocols(node)
            if not protocols:
                continue

            for proto in protocols:
                proto_name = proto["name"]
                detected_protocols.setdefault(proto_name, []).append({
                    "node_id": str(node.id),
                    "node_name": node.resource_name or str(node.id),
                    "node_type": node.node_type,
                    "port": proto["port"],
                })

            nodes_with_protocols.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "zone": self._classify_node_zone(node),
                "protocols": protocols,
                "is_internet_facing": bool(node.is_internet_facing),
            })

        # Check edges for protocol/port information
        edge_protocol_violations: list[dict] = []
        for edge in all_edges:
            edge_meta = _parse_json(edge.edge_metadata) or {}
            port = edge_meta.get("port", 0)
            protocol = edge_meta.get("protocol", "").lower()

            # Check if edge carries industrial protocol traffic
            matched_proto = None
            for proto_name, proto_info in _INDUSTRIAL_PROTOCOLS.items():
                if port == proto_info["port"] or proto_name in protocol:
                    matched_proto = proto_name
                    break

            if not matched_proto:
                continue

            src = next((n for n in all_nodes if n.id == edge.source_node_id), None)
            tgt = next((n for n in all_nodes if n.id == edge.target_node_id), None)
            if not src or not tgt:
                continue

            src_zone = self._classify_node_zone(src)
            tgt_zone = self._classify_node_zone(tgt)

            # Flag if protocol crosses zone boundaries
            is_cross_zone = src_zone != tgt_zone
            severity = "high" if is_cross_zone else "medium"
            if src_zone == "level4_enterprise_it" or tgt_zone == "level4_enterprise_it":
                severity = "critical"

            edge_protocol_violations.append({
                "edge_id": str(edge.id),
                "protocol": matched_proto,
                "port": port,
                "source": src.resource_name or str(src.id),
                "source_zone": src_zone,
                "target": tgt.resource_name or str(tgt.id),
                "target_zone": tgt_zone,
                "is_cross_zone": is_cross_zone,
                "severity": severity,
            })

        # Check findings for protocol-related issues
        protocol_findings: list[dict] = []
        for f in all_findings:
            if f.status not in ("open", "in_progress"):
                continue
            text = f"{f.title} {f.description or ''}".lower()
            matched = _text_matches(text, list(_INDUSTRIAL_PROTOCOLS.keys()))
            if matched or any(kw in text for kw in (
                "industrial protocol", "ot protocol", "ics protocol",
                "unauthorized protocol", "protocol violation",
            )):
                protocol_findings.append({
                    "finding_id": str(f.id),
                    "title": f.title,
                    "severity": f.severity,
                    "matched_protocols": matched,
                    "resource_arn": str(f.resource_arn or ""),
                })

        # Build whitelist compliance summary
        protocol_summary: list[dict] = []
        for proto_name, proto_info in _INDUSTRIAL_PROTOCOLS.items():
            instances = detected_protocols.get(proto_name, [])
            violations = [
                v for v in edge_protocol_violations if v["protocol"] == proto_name
            ]
            protocol_summary.append({
                "protocol": proto_name,
                "port": proto_info["port"],
                "risk_level": proto_info["risk"],
                "description": proto_info["description"],
                "detected_instances": len(instances),
                "cross_zone_violations": len(violations),
                "status": "violation" if violations else ("detected" if instances else "not_detected"),
            })

        return {
            "total_protocols_detected": len(detected_protocols),
            "total_nodes_with_protocols": len(nodes_with_protocols),
            "total_cross_zone_violations": len(edge_protocol_violations),
            "total_protocol_findings": len(protocol_findings),
            "protocol_summary": protocol_summary,
            "nodes_with_protocols": nodes_with_protocols,
            "cross_zone_violations": edge_protocol_violations,
            "protocol_findings": protocol_findings[:20],
        }

    async def nation_state_indicators(self, workspace_id: uuid.UUID) -> dict:
        """Detect nation-state APT dwell time indicators.

        Analyses CanonicalFinding age patterns (first_seen_at vs last_seen_at)
        to identify long-dwell indicators matching Salt Typhoon, Sandworm,
        Volt Typhoon, and CHERNOVITE TTP signatures.
        """
        all_findings = await self._all_findings(workspace_id)
        all_nodes = await self._all_nodes(workspace_id)

        now = datetime.now(timezone.utc)
        open_findings = [f for f in all_findings if f.status in ("open", "in_progress")]

        # Analyse each APT group
        apt_assessments: list[dict] = []

        for apt_name, apt_info in _NATION_STATE_INDICATORS.items():
            # Match findings against APT indicators
            matched_findings: list[dict] = []
            long_dwell_findings: list[dict] = []

            for f in open_findings:
                text = f"{f.title} {f.description or ''}".lower()
                matched_indicators = _text_matches(text, apt_info["indicators"])
                if not matched_indicators:
                    continue

                # Calculate dwell time from first_seen_at
                dwell_days = 0
                if f.first_seen_at:
                    try:
                        first_seen = datetime.fromisoformat(str(f.first_seen_at))
                        if first_seen.tzinfo is None:
                            first_seen = first_seen.replace(tzinfo=timezone.utc)
                        dwell_days = (now - first_seen).days
                    except (ValueError, TypeError):
                        pass

                finding_entry = {
                    "finding_id": str(f.id),
                    "title": f.title,
                    "severity": f.severity,
                    "matched_indicators": matched_indicators,
                    "dwell_days": dwell_days,
                    "first_seen_at": str(f.first_seen_at or ""),
                    "resource_arn": str(f.resource_arn or ""),
                }
                matched_findings.append(finding_entry)

                # Flag if dwell time exceeds APT threshold
                if dwell_days >= apt_info["dwell_time_days"]:
                    long_dwell_findings.append(finding_entry)

            # Check nodes for APT-related metadata
            targeted_nodes: list[dict] = []
            for node in all_nodes:
                meta = _parse_json(node.node_metadata) or {}
                combined = f"{node.resource_name or ''} {json.dumps(meta)}".lower()
                if any(kw in combined for kw in apt_info["indicators"]):
                    targeted_nodes.append({
                        "node_id": str(node.id),
                        "name": node.resource_name or str(node.id),
                        "node_type": node.node_type,
                        "risk_score": node.risk_score,
                    })

            # Calculate threat score
            threat_score = 0.0
            if matched_findings:
                threat_score += min(len(matched_findings) * 1.5, 4.0)
            if long_dwell_findings:
                threat_score += min(len(long_dwell_findings) * 2.5, 4.0)
            if targeted_nodes:
                threat_score += min(len(targeted_nodes) * 0.5, 2.0)
            threat_score = min(threat_score, 10.0)

            threat_level = "low"
            if threat_score >= 7.0:
                threat_level = "critical"
            elif threat_score >= 5.0:
                threat_level = "high"
            elif threat_score >= 3.0:
                threat_level = "medium"

            apt_assessments.append({
                "apt_group": apt_name,
                "aliases": apt_info["aliases"],
                "origin": apt_info["origin"],
                "targets": apt_info["targets"],
                "known_ttps": apt_info["ttps"],
                "expected_dwell_time_days": apt_info["dwell_time_days"],
                "threat_score": round(threat_score, 1),
                "threat_level": threat_level,
                "matched_finding_count": len(matched_findings),
                "long_dwell_finding_count": len(long_dwell_findings),
                "targeted_node_count": len(targeted_nodes),
                "matched_findings": matched_findings[:10],
                "long_dwell_findings": long_dwell_findings[:10],
                "targeted_nodes": targeted_nodes[:10],
            })

        # Sort by threat score descending
        apt_assessments.sort(key=lambda a: -a["threat_score"])

        # Overall dwell time statistics
        dwell_stats: dict[str, int] = {
            "under_30_days": 0,
            "30_to_90_days": 0,
            "90_to_180_days": 0,
            "180_to_365_days": 0,
            "over_365_days": 0,
        }
        for f in open_findings:
            if not f.first_seen_at:
                continue
            try:
                first_seen = datetime.fromisoformat(str(f.first_seen_at))
                if first_seen.tzinfo is None:
                    first_seen = first_seen.replace(tzinfo=timezone.utc)
                days = (now - first_seen).days
            except (ValueError, TypeError):
                continue

            if days < 30:
                dwell_stats["under_30_days"] += 1
            elif days < 90:
                dwell_stats["30_to_90_days"] += 1
            elif days < 180:
                dwell_stats["90_to_180_days"] += 1
            elif days < 365:
                dwell_stats["180_to_365_days"] += 1
            else:
                dwell_stats["over_365_days"] += 1

        elevated_groups = [a for a in apt_assessments if a["threat_level"] in ("critical", "high")]

        return {
            "total_apt_groups_assessed": len(apt_assessments),
            "elevated_threat_groups": len(elevated_groups),
            "total_open_findings_analysed": len(open_findings),
            "dwell_time_distribution": dwell_stats,
            "apt_assessments": apt_assessments,
        }
