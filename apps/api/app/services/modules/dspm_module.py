"""
DSPMModule — Data Security Posture Management simulation.

Sprint 33: Simulates data security:
1. Sensitive data classification (PII/PHI/PCI)
2. Data exposure path analysis
3. Data flow tracing
4. Regulatory compliance (GDPR/HIPAA/PCI-DSS/CCPA)
5. Breach impact modeling
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

_DATA_STORE_NODE_TYPES = {
    "s3_bucket", "rds", "dynamodb", "redshift", "elasticache",
    "efs", "ebs_volume", "secrets_manager",
}

# Keywords in finding titles/descriptions that signal data-classification level
_PII_KEYWORDS = [
    "pii", "personal", "email", "ssn", "social security",
    "name", "address", "phone", "date of birth", "passport",
]
_PHI_KEYWORDS = [
    "phi", "health", "hipaa", "medical", "patient", "diagnosis",
    "prescription", "treatment",
]
_PCI_KEYWORDS = [
    "pci", "credit card", "card number", "cardholder", "cvv",
    "payment", "pci-dss", "card data",
]

# Regulatory framework mapping — finding keyword → applicable frameworks
_FRAMEWORK_KEYWORD_MAP: dict[str, list[str]] = {
    "encryption": ["GDPR", "HIPAA", "PCI-DSS", "CCPA"],
    "public access": ["GDPR", "HIPAA", "PCI-DSS", "CCPA"],
    "logging": ["HIPAA", "PCI-DSS"],
    "access control": ["GDPR", "HIPAA", "PCI-DSS", "CCPA"],
    "data retention": ["GDPR", "CCPA"],
    "backup": ["HIPAA"],
    "mfa": ["PCI-DSS", "HIPAA"],
    "audit": ["HIPAA", "PCI-DSS"],
    "versioning": ["GDPR", "HIPAA"],
    "ssl": ["PCI-DSS"],
    "tls": ["PCI-DSS"],
    "kms": ["GDPR", "HIPAA", "PCI-DSS"],
}

# Severity-based estimated financial impact per record (USD)
_BREACH_COST_PER_RECORD: dict[str, float] = {
    "PII": 164.0,
    "PHI": 429.0,
    "PCI": 180.0,
    "Confidential": 120.0,
    "Public": 10.0,
}

# Estimated record counts by resource type (for simulation)
_ESTIMATED_RECORDS: dict[str, int] = {
    "s3_bucket": 500_000,
    "rds": 1_000_000,
    "dynamodb": 750_000,
    "redshift": 2_000_000,
    "elasticache": 100_000,
    "efs": 250_000,
    "ebs_volume": 50_000,
    "secrets_manager": 500,
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


def _classify_text(text: str) -> list[str]:
    """Return list of data classification labels that match the text."""
    lower = text.lower()
    labels: list[str] = []
    if any(kw in lower for kw in _PII_KEYWORDS):
        labels.append("PII")
    if any(kw in lower for kw in _PHI_KEYWORDS):
        labels.append("PHI")
    if any(kw in lower for kw in _PCI_KEYWORDS):
        labels.append("PCI")
    return labels


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(severity, 5)


# ── Service ───────────────────────────────────────────────────────────────────

class DSPMModule:
    """Data Security Posture Management — classifies, traces, and models
    data risk across workspace cloud resources."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _data_store_nodes(
        self, workspace_id: uuid.UUID,
    ) -> list[SecurityGraphNode]:
        q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id,
            SecurityGraphNode.node_type.in_(list(_DATA_STORE_NODE_TYPES)),
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _data_findings(
        self, workspace_id: uuid.UUID,
    ) -> list[CanonicalFinding]:
        """Fetch findings related to data-store resource types."""
        resource_patterns = [f"AWS::{t.upper().replace('_', '')}%" for t in _DATA_STORE_NODE_TYPES]
        # Also match S3, RDS, DynamoDB by common resource_type prefixes
        resource_patterns += [
            "AWS::S3%", "AWS::RDS%", "AWS::DynamoDB%",
            "AWS::Redshift%", "AWS::ElastiCache%", "AWS::EFS%",
            "AWS::EBS%", "AWS::SecretsManager%",
        ]
        conditions = [CanonicalFinding.resource_type.like(p) for p in resource_patterns]
        q = select(CanonicalFinding).where(
            CanonicalFinding.workspace_id == workspace_id,
            or_(*conditions),
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

    async def _all_nodes(
        self, workspace_id: uuid.UUID,
    ) -> list[SecurityGraphNode]:
        q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id,
        )
        return list((await self.db.execute(q)).scalars().all())

    def _classify_node(
        self,
        node: SecurityGraphNode,
        findings_by_arn: dict[str, list[CanonicalFinding]],
        all_findings: list[CanonicalFinding],
    ) -> list[str]:
        """Determine data classification labels for a node."""
        labels: set[str] = set()

        # Check node metadata
        meta = _parse_json(node.node_metadata) or {}
        meta_text = json.dumps(meta).lower()
        labels.update(_classify_text(meta_text))

        # Check node name / ARN
        combined = f"{node.resource_name or ''} {node.resource_arn or ''}"
        labels.update(_classify_text(combined))

        # Check linked findings
        arn = node.resource_arn or ""
        matched_findings = findings_by_arn.get(arn, [])
        finding_ids = {str(fid) for fid in (_parse_json(node.finding_ids) or [])}
        for f in all_findings:
            if str(f.id) in finding_ids:
                matched_findings.append(f)
        for f in matched_findings:
            text = f"{f.title} {f.description or ''}"
            labels.update(_classify_text(text))

        # If marked sensitive in graph but no specific label, default Confidential
        if node.is_sensitive_data and not labels:
            labels.add("Confidential")

        return sorted(labels) if labels else ["Public"]

    # ── Public API ───────────────────────────────────────────────────────

    async def classify_data_stores(self, workspace_id: uuid.UUID) -> dict:
        """Classify data stores by sensitivity level.

        Returns inventory of S3 buckets, RDS instances, DynamoDB tables, etc.
        with classification: PII, PHI, PCI, Confidential, Public.
        """
        nodes = await self._data_store_nodes(workspace_id)
        data_findings = await self._data_findings(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        # Index findings by resource ARN
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in data_findings:
            arn = f.resource_arn or ""
            findings_by_arn.setdefault(arn, []).append(f)

        stores: list[dict] = []
        classification_summary: dict[str, int] = {}

        for node in nodes:
            meta = _parse_json(node.node_metadata) or {}
            classifications = self._classify_node(node, findings_by_arn, all_findings)
            encryption_status = meta.get("encryption", meta.get("encrypted", "unknown"))
            public_access = meta.get("public_access", node.is_internet_facing)

            # Count open findings for this node
            finding_ids = {str(fid) for fid in (_parse_json(node.finding_ids) or [])}
            open_finding_count = sum(
                1 for f in all_findings
                if str(f.id) in finding_ids and f.status in ("open", "in_progress")
            )

            store_entry = {
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "region": node.region,
                "classifications": classifications,
                "highest_classification": classifications[0] if classifications else "Public",
                "encryption_status": encryption_status,
                "public_access": bool(public_access),
                "is_internet_facing": bool(node.is_internet_facing),
                "risk_score": node.risk_score,
                "open_findings": open_finding_count,
            }
            stores.append(store_entry)

            for cls_label in classifications:
                classification_summary[cls_label] = classification_summary.get(cls_label, 0) + 1

        # Sort: highest sensitivity first, then risk_score desc
        _cls_order = {"PHI": 0, "PCI": 1, "PII": 2, "Confidential": 3, "Public": 4}
        stores.sort(key=lambda s: (
            min(_cls_order.get(c, 5) for c in s["classifications"]),
            -(s["risk_score"] or 0),
        ))

        return {
            "total_data_stores": len(stores),
            "classification_summary": classification_summary,
            "data_stores": stores,
        }

    async def exposure_paths(self, workspace_id: uuid.UUID) -> dict:
        """Trace data exposure paths from sensitive stores to internet.

        Walks the security graph from data-store nodes through edges to
        internet-facing nodes, identifying exposure chains.
        """
        nodes = await self._all_nodes(workspace_id)
        edges = await self._all_edges(workspace_id)
        data_nodes = [n for n in nodes if n.node_type in _DATA_STORE_NODE_TYPES]
        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in nodes}

        # Build adjacency list (outgoing edges from each node)
        adjacency: dict[uuid.UUID, list[SecurityGraphEdge]] = {}
        for edge in edges:
            adjacency.setdefault(edge.source_node_id, []).append(edge)

        exposure_results: list[dict] = []

        for data_node in data_nodes:
            if not data_node.is_sensitive_data and not data_node.is_internet_facing:
                # Only trace from sensitive or already-exposed stores
                meta = _parse_json(data_node.node_metadata) or {}
                if not meta.get("public_access", False):
                    continue

            # BFS from data_node to find internet-facing targets
            visited: set[uuid.UUID] = set()
            queue: list[tuple[uuid.UUID, list[dict]]] = [(data_node.id, [])]

            while queue:
                current_id, path = queue.pop(0)
                if current_id in visited:
                    continue
                visited.add(current_id)

                current_node = node_map.get(current_id)
                if not current_node:
                    continue

                # If we reached an internet-facing node (not the start), record path
                if (
                    current_id != data_node.id
                    and (current_node.is_internet_facing or current_node.node_type == "internet")
                ):
                    exposure_results.append({
                        "source_store": {
                            "id": str(data_node.id),
                            "name": data_node.resource_name or str(data_node.id),
                            "type": data_node.node_type,
                        },
                        "exposure_target": {
                            "id": str(current_node.id),
                            "name": current_node.resource_name or str(current_node.id),
                            "type": current_node.node_type,
                        },
                        "path_length": len(path),
                        "path_edges": path,
                        "is_attack_path": any(e.get("is_attack_path") for e in path),
                        "max_risk_contribution": max(
                            (e.get("risk_contribution") or 0 for e in path), default=0
                        ),
                    })
                    continue  # Don't keep traversing past internet node

                # Expand neighbors
                for edge in adjacency.get(current_id, []):
                    if edge.target_node_id not in visited:
                        edge_info = {
                            "edge_type": edge.edge_type,
                            "is_attack_path": bool(edge.is_attack_path),
                            "risk_contribution": edge.risk_contribution,
                            "source": current_node.resource_name or str(current_node.id),
                            "target": (
                                node_map[edge.target_node_id].resource_name
                                if edge.target_node_id in node_map
                                else str(edge.target_node_id)
                            ),
                        }
                        queue.append((edge.target_node_id, path + [edge_info]))

        # Sort by risk: attack paths first, then path length (shorter = more direct)
        exposure_results.sort(key=lambda e: (
            not e["is_attack_path"],
            -e["max_risk_contribution"],
            e["path_length"],
        ))

        return {
            "total_exposure_paths": len(exposure_results),
            "paths_with_attack_chain": sum(
                1 for e in exposure_results if e["is_attack_path"]
            ),
            "exposure_paths": exposure_results,
        }

    async def breach_impact(self, workspace_id: uuid.UUID) -> dict:
        """Model potential data breach impact.

        Calculates: records at risk, financial impact, notification requirements
        based on data classifications and exposure paths.
        """
        classification_result = await self.classify_data_stores(workspace_id)
        exposure_result = await self.exposure_paths(workspace_id)

        stores = classification_result["data_stores"]
        exposed_store_ids = {
            p["source_store"]["id"] for p in exposure_result["exposure_paths"]
        }

        total_records_at_risk = 0
        total_financial_impact = 0.0
        notification_requirements: dict[str, bool] = {
            "GDPR_72h_notification": False,
            "HIPAA_60d_notification": False,
            "PCI_DSS_incident_response": False,
            "CCPA_consumer_notification": False,
            "SEC_4d_disclosure": False,
        }
        impacted_stores: list[dict] = []

        for store in stores:
            is_exposed = store["id"] in exposed_store_ids or store["public_access"]
            if not is_exposed and store["highest_classification"] == "Public":
                continue

            # Estimate records based on resource type
            estimated_records = _ESTIMATED_RECORDS.get(store["node_type"], 100_000)
            # Scale by risk score — higher risk = more likely full exposure
            risk_multiplier = min((store["risk_score"] or 1.0) / 10.0, 1.0)
            records_at_risk = int(estimated_records * risk_multiplier) if is_exposed else 0

            # Financial impact per classification
            store_cost = 0.0
            for cls_label in store["classifications"]:
                cost_per_record = _BREACH_COST_PER_RECORD.get(cls_label, 50.0)
                store_cost += records_at_risk * cost_per_record

            # Notification requirements
            for cls_label in store["classifications"]:
                if cls_label == "PII":
                    notification_requirements["GDPR_72h_notification"] = True
                    notification_requirements["CCPA_consumer_notification"] = True
                    notification_requirements["SEC_4d_disclosure"] = True
                if cls_label == "PHI":
                    notification_requirements["HIPAA_60d_notification"] = True
                if cls_label == "PCI":
                    notification_requirements["PCI_DSS_incident_response"] = True

            total_records_at_risk += records_at_risk
            total_financial_impact += store_cost

            impacted_stores.append({
                "id": store["id"],
                "name": store["name"],
                "node_type": store["node_type"],
                "classifications": store["classifications"],
                "is_exposed": is_exposed,
                "estimated_records_at_risk": records_at_risk,
                "estimated_financial_impact_usd": round(store_cost, 2),
            })

        # Sort by financial impact descending
        impacted_stores.sort(key=lambda s: -s["estimated_financial_impact_usd"])

        return {
            "total_data_stores_analyzed": len(stores),
            "exposed_stores": len(exposed_store_ids),
            "total_records_at_risk": total_records_at_risk,
            "total_estimated_financial_impact_usd": round(total_financial_impact, 2),
            "notification_requirements": notification_requirements,
            "impacted_stores": impacted_stores,
        }

    async def regulatory_compliance(self, workspace_id: uuid.UUID) -> dict:
        """Assess regulatory compliance for data handling.

        Maps findings to GDPR/HIPAA/PCI-DSS/CCPA requirements and reports
        compliance gaps per framework.
        """
        all_findings = await self._all_findings(workspace_id)
        data_findings = await self._data_findings(workspace_id)
        classification_result = await self.classify_data_stores(workspace_id)

        # Determine which frameworks apply based on data classifications
        active_frameworks: set[str] = set()
        cls_summary = classification_result.get("classification_summary", {})
        if cls_summary.get("PII", 0) > 0:
            active_frameworks.update(["GDPR", "CCPA"])
        if cls_summary.get("PHI", 0) > 0:
            active_frameworks.add("HIPAA")
        if cls_summary.get("PCI", 0) > 0:
            active_frameworks.add("PCI-DSS")
        # Default: always check GDPR and CCPA
        active_frameworks.update(["GDPR", "CCPA"])

        # Map open findings to framework violations
        framework_violations: dict[str, list[dict]] = {fw: [] for fw in active_frameworks}

        open_findings = [
            f for f in (data_findings or all_findings)
            if f.status in ("open", "in_progress")
        ]

        for finding in open_findings:
            text = f"{finding.title} {finding.description or ''}".lower()
            matched_frameworks: set[str] = set()

            for keyword, frameworks in _FRAMEWORK_KEYWORD_MAP.items():
                if keyword in text:
                    for fw in frameworks:
                        if fw in active_frameworks:
                            matched_frameworks.add(fw)

            # Also check compliance_frameworks field on the finding
            finding_frameworks = _parse_json(finding.compliance_frameworks) or []
            for fw_id in finding_frameworks:
                fw_str = str(fw_id).upper()
                for active_fw in active_frameworks:
                    if active_fw.replace("-", "_") in fw_str or active_fw in fw_str:
                        matched_frameworks.add(active_fw)

            for fw in matched_frameworks:
                framework_violations[fw].append({
                    "finding_id": str(finding.id),
                    "title": finding.title,
                    "severity": finding.severity,
                    "resource_arn": finding.resource_arn,
                    "resource_type": finding.resource_type,
                })

        # Build per-framework compliance report
        compliance_report: dict[str, dict] = {}
        for fw in sorted(active_frameworks):
            violations = framework_violations.get(fw, [])
            critical = sum(1 for v in violations if v["severity"] == "critical")
            high = sum(1 for v in violations if v["severity"] == "high")
            total = len(violations)

            if total == 0:
                status = "compliant"
            elif critical > 0:
                status = "critical_violations"
            elif high > 0:
                status = "violations"
            else:
                status = "warnings"

            compliance_report[fw] = {
                "status": status,
                "total_violations": total,
                "critical_violations": critical,
                "high_violations": high,
                "violations": violations[:20],  # Cap detail list
            }

        overall_status = "compliant"
        for fw, report in compliance_report.items():
            if report["status"] == "critical_violations":
                overall_status = "critical_violations"
                break
            if report["status"] == "violations":
                overall_status = "violations"

        return {
            "active_frameworks": sorted(active_frameworks),
            "overall_status": overall_status,
            "total_open_findings": len(open_findings),
            "compliance_report": compliance_report,
        }
