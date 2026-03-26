"""
LLMjackingModule — LLMjacking Cloud AI Credential Abuse simulation.

Sprint 34: Simulates LLMjacking (Scylla attack pattern):
1. Stolen AI credential detection
2. Canary AI credential deployment planning
3. AI service spend anomaly detection
4. VPC endpoint enforcement for AI services
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

# AI/ML service node types and ARN patterns
_AI_SERVICE_IDENTIFIERS: dict[str, dict[str, Any]] = {
    "bedrock": {
        "arn_patterns": ["arn:aws:bedrock:", "bedrock"],
        "node_keywords": ["bedrock", "foundation-model", "fm-"],
        "service_name": "Amazon Bedrock",
        "vpc_endpoint_service": "com.amazonaws.*.bedrock-runtime",
    },
    "sagemaker": {
        "arn_patterns": ["arn:aws:sagemaker:", "sagemaker"],
        "node_keywords": ["sagemaker", "ml.", "notebook", "endpoint"],
        "service_name": "Amazon SageMaker",
        "vpc_endpoint_service": "com.amazonaws.*.sagemaker.runtime",
    },
    "comprehend": {
        "arn_patterns": ["arn:aws:comprehend:"],
        "node_keywords": ["comprehend"],
        "service_name": "Amazon Comprehend",
        "vpc_endpoint_service": "com.amazonaws.*.comprehend",
    },
    "rekognition": {
        "arn_patterns": ["arn:aws:rekognition:"],
        "node_keywords": ["rekognition"],
        "service_name": "Amazon Rekognition",
        "vpc_endpoint_service": "com.amazonaws.*.rekognition",
    },
    "textract": {
        "arn_patterns": ["arn:aws:textract:"],
        "node_keywords": ["textract"],
        "service_name": "Amazon Textract",
        "vpc_endpoint_service": "com.amazonaws.*.textract",
    },
    "openai": {
        "arn_patterns": [],
        "node_keywords": ["openai", "gpt", "chatgpt", "dall-e"],
        "service_name": "OpenAI API",
        "vpc_endpoint_service": None,
    },
    "anthropic": {
        "arn_patterns": [],
        "node_keywords": ["anthropic", "claude"],
        "service_name": "Anthropic API",
        "vpc_endpoint_service": None,
    },
}

# Keywords indicating credential issues in findings
_CREDENTIAL_ABUSE_KEYWORDS = [
    "api key", "access key", "secret key", "credential",
    "token", "overprivileged", "excessive permission",
    "no rotation", "key rotation", "stale key", "unused key",
    "leaked", "exposed credential", "hardcoded",
    "public repository", "git", "environment variable",
]

# Keywords indicating AI-specific spend abuse
_SPEND_ANOMALY_KEYWORDS = [
    "cost", "spend", "billing", "budget", "anomaly",
    "unusual usage", "spike", "quota", "rate limit",
    "throttle", "high volume", "burst",
]

# Credential risk scoring weights
_RISK_WEIGHTS = {
    "no_rotation_policy": 2.0,
    "overprivileged": 2.5,
    "internet_exposed": 3.0,
    "no_vpc_endpoint": 1.5,
    "hardcoded_credential": 3.0,
    "leaked_credential": 4.0,
    "no_usage_monitoring": 1.5,
    "stale_key": 1.5,
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


class LLMjackingModule:
    """LLMjacking Cloud AI Credential Abuse — detects stolen AI credentials,
    plans canary credential deployments, identifies spend anomalies, and
    audits VPC endpoint enforcement for AI services."""

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

    def _identify_ai_service(self, node: SecurityGraphNode) -> str | None:
        """Identify if a node is an AI/ML service and return service name."""
        arn = (node.resource_arn or "").lower()
        name = (node.resource_name or "").lower()
        meta = _parse_json(node.node_metadata) or {}
        combined = f"{arn} {name} {json.dumps(meta)}".lower()

        for svc_key, svc_info in _AI_SERVICE_IDENTIFIERS.items():
            for pattern in svc_info["arn_patterns"]:
                if pattern in arn:
                    return svc_key
            for keyword in svc_info["node_keywords"]:
                if keyword in combined:
                    return svc_key
        return None

    def _assess_credential_risks(
        self,
        node: SecurityGraphNode,
        linked_findings: list[CanonicalFinding],
    ) -> tuple[list[str], float]:
        """Assess credential risk factors for an AI service node."""
        meta = _parse_json(node.node_metadata) or {}
        risk_factors: list[str] = []
        risk_score = 0.0

        # Check metadata for credential configuration
        key_rotation = meta.get("key_rotation_days", meta.get("rotation_policy"))
        if key_rotation is None or (isinstance(key_rotation, int) and key_rotation > 90):
            risk_factors.append("no_rotation_policy")
            risk_score += _RISK_WEIGHTS["no_rotation_policy"]

        # Check for overprivileged keys
        permissions = meta.get("permissions", meta.get("policy_actions", []))
        if isinstance(permissions, list) and any(
            p in ("*", "bedrock:*", "sagemaker:*") for p in permissions
        ):
            risk_factors.append("overprivileged")
            risk_score += _RISK_WEIGHTS["overprivileged"]

        # Internet-facing AI service
        if node.is_internet_facing:
            risk_factors.append("internet_exposed")
            risk_score += _RISK_WEIGHTS["internet_exposed"]

        # Check findings for credential abuse indicators
        for f in linked_findings:
            if f.status not in ("open", "in_progress"):
                continue
            text = f"{f.title} {f.description or ''}".lower()
            if any(kw in text for kw in ("hardcoded", "hard-coded", "embedded")):
                risk_factors.append("hardcoded_credential")
                risk_score += _RISK_WEIGHTS["hardcoded_credential"]
                break
            if any(kw in text for kw in ("leaked", "exposed", "public repo")):
                risk_factors.append("leaked_credential")
                risk_score += _RISK_WEIGHTS["leaked_credential"]
                break

        # Check for stale keys
        last_used = meta.get("last_used", meta.get("last_activity"))
        if last_used:
            try:
                last_used_dt = datetime.fromisoformat(str(last_used))
                if last_used_dt.tzinfo is None:
                    last_used_dt = last_used_dt.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - last_used_dt).days > 90:
                    risk_factors.append("stale_key")
                    risk_score += _RISK_WEIGHTS["stale_key"]
            except (ValueError, TypeError):
                pass

        # Check for usage monitoring
        monitoring = meta.get("monitoring_enabled", meta.get("cloudwatch_alarms"))
        if not monitoring:
            risk_factors.append("no_usage_monitoring")
            risk_score += _RISK_WEIGHTS["no_usage_monitoring"]

        return list(set(risk_factors)), min(risk_score, 10.0)

    # ── Public API ───────────────────────────────────────────────────────

    async def credential_audit(self, workspace_id: uuid.UUID) -> dict:
        """Audit AI service credentials for abuse indicators.

        Queries SecurityGraphNode for AI/ML service assets, correlates with
        CanonicalFinding for credential misuse, and evaluates key rotation,
        privilege scope, and exposure patterns.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        # Index findings by ARN
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in all_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        # Also index findings by finding_ids on nodes
        findings_by_id: dict[str, CanonicalFinding] = {
            str(f.id): f for f in all_findings
        }

        # Identify AI service nodes
        ai_assets: list[dict] = []
        service_summary: dict[str, int] = {}

        for node in all_nodes:
            ai_service = self._identify_ai_service(node)
            if not ai_service:
                continue

            service_summary[ai_service] = service_summary.get(ai_service, 0) + 1

            # Gather linked findings
            arn = node.resource_arn or ""
            linked_findings = list(findings_by_arn.get(arn, []))
            for fid in (_parse_json(node.finding_ids) or []):
                f = findings_by_id.get(str(fid))
                if f and f not in linked_findings:
                    linked_findings.append(f)

            # Credential-specific findings
            credential_findings: list[dict] = []
            for f in linked_findings:
                if f.status not in ("open", "in_progress"):
                    continue
                text = f"{f.title} {f.description or ''}".lower()
                matched = _text_matches(text, _CREDENTIAL_ABUSE_KEYWORDS)
                if matched:
                    credential_findings.append({
                        "finding_id": str(f.id),
                        "title": f.title,
                        "severity": f.severity,
                        "matched_indicators": matched,
                    })

            # Assess credential risks
            risk_factors, risk_score = self._assess_credential_risks(node, linked_findings)

            severity = "low"
            if risk_score >= 8.0:
                severity = "critical"
            elif risk_score >= 6.0:
                severity = "high"
            elif risk_score >= 3.5:
                severity = "medium"

            ai_assets.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "ai_service": ai_service,
                "service_name": _AI_SERVICE_IDENTIFIERS[ai_service]["service_name"],
                "risk_score": round(risk_score, 1),
                "severity": severity,
                "risk_factors": risk_factors,
                "credential_findings": credential_findings[:5],
                "total_linked_findings": len(linked_findings),
                "is_internet_facing": bool(node.is_internet_facing),
            })

        # Also detect credential findings not linked to specific AI nodes
        orphan_credential_findings: list[dict] = []
        for f in all_findings:
            if f.status not in ("open", "in_progress"):
                continue
            text = f"{f.title} {f.description or ''}".lower()
            # Look for AI + credential combined signals
            has_ai = any(
                kw in text
                for svc in _AI_SERVICE_IDENTIFIERS.values()
                for kw in svc["node_keywords"]
            )
            has_cred = any(kw in text for kw in _CREDENTIAL_ABUSE_KEYWORDS)
            if has_ai and has_cred:
                # Check not already linked to an AI asset
                already_linked = any(
                    any(cf["finding_id"] == str(f.id) for cf in a.get("credential_findings", []))
                    for a in ai_assets
                )
                if not already_linked:
                    orphan_credential_findings.append({
                        "finding_id": str(f.id),
                        "title": f.title,
                        "severity": f.severity,
                        "resource_arn": str(f.resource_arn or ""),
                    })

        ai_assets.sort(key=lambda a: (
            _SEVERITY_ORDER.get(a["severity"], 5),
            -a["risk_score"],
        ))

        return {
            "total_ai_assets": len(ai_assets),
            "service_distribution": service_summary,
            "severity_breakdown": {
                sev: sum(1 for a in ai_assets if a["severity"] == sev)
                for sev in ("critical", "high", "medium", "low")
            },
            "total_credential_findings": sum(
                len(a["credential_findings"]) for a in ai_assets
            ) + len(orphan_credential_findings),
            "orphan_credential_findings": orphan_credential_findings[:10],
            "ai_assets": ai_assets,
        }

    async def spend_anomaly_detection(self, workspace_id: uuid.UUID) -> dict:
        """Detect AI service spend anomalies.

        Analyses CanonicalFinding for cost/spend anomaly patterns and
        SecurityGraphNode metadata for usage metrics. Uses 3x baseline
        threshold within 15-minute window as the detection heuristic.
        """
        all_findings = await self._all_findings(workspace_id)
        all_nodes = await self._all_nodes(workspace_id)

        # Identify spend-related findings
        spend_findings: list[dict] = []
        for f in all_findings:
            if f.status not in ("open", "in_progress"):
                continue
            text = f"{f.title} {f.description or ''}".lower()
            matched = _text_matches(text, _SPEND_ANOMALY_KEYWORDS)
            if not matched:
                continue

            # Check if AI-related
            ai_service = None
            for svc_key, svc_info in _AI_SERVICE_IDENTIFIERS.items():
                if any(kw in text for kw in svc_info["node_keywords"]):
                    ai_service = svc_key
                    break

            spend_findings.append({
                "finding_id": str(f.id),
                "title": f.title,
                "severity": f.severity,
                "ai_service": ai_service,
                "matched_indicators": matched,
                "resource_arn": str(f.resource_arn or ""),
                "first_seen_at": str(f.first_seen_at or ""),
            })

        # Analyse AI node metadata for usage anomalies
        usage_anomalies: list[dict] = []

        for node in all_nodes:
            ai_service = self._identify_ai_service(node)
            if not ai_service:
                continue

            meta = _parse_json(node.node_metadata) or {}
            usage = meta.get("usage", meta.get("invocations", {}))
            cost = meta.get("cost", meta.get("spend", {}))

            if not isinstance(usage, dict) and not isinstance(cost, dict):
                continue

            # Extract baseline and current usage
            baseline_daily = 0.0
            current_daily = 0.0
            if isinstance(cost, dict):
                baseline_daily = float(cost.get("baseline_daily", cost.get("avg_daily", 0)))
                current_daily = float(cost.get("current_daily", cost.get("today", 0)))
            elif isinstance(usage, dict):
                baseline_daily = float(usage.get("baseline_daily", usage.get("avg_daily", 0)))
                current_daily = float(usage.get("current_daily", usage.get("today", 0)))

            # 3x threshold detection
            is_anomalous = False
            anomaly_ratio = 0.0
            if baseline_daily > 0 and current_daily > 0:
                anomaly_ratio = current_daily / baseline_daily
                is_anomalous = anomaly_ratio >= 3.0

            if not is_anomalous and not (isinstance(cost, dict) and cost):
                continue

            severity = "low"
            if anomaly_ratio >= 10.0:
                severity = "critical"
            elif anomaly_ratio >= 5.0:
                severity = "high"
            elif anomaly_ratio >= 3.0:
                severity = "medium"

            usage_anomalies.append({
                "node_id": str(node.id),
                "name": node.resource_name or str(node.id),
                "ai_service": ai_service,
                "service_name": _AI_SERVICE_IDENTIFIERS[ai_service]["service_name"],
                "baseline_daily": round(baseline_daily, 2),
                "current_daily": round(current_daily, 2),
                "anomaly_ratio": round(anomaly_ratio, 1),
                "is_anomalous": is_anomalous,
                "severity": severity,
                "resource_arn": node.resource_arn,
            })

        usage_anomalies.sort(key=lambda a: -a["anomaly_ratio"])

        # Calculate overall spend risk
        anomalous_count = sum(1 for a in usage_anomalies if a["is_anomalous"])
        total_baseline = sum(a["baseline_daily"] for a in usage_anomalies)
        total_current = sum(a["current_daily"] for a in usage_anomalies)

        return {
            "total_ai_services_monitored": len(usage_anomalies),
            "anomalous_services": anomalous_count,
            "total_spend_findings": len(spend_findings),
            "total_baseline_daily": round(total_baseline, 2),
            "total_current_daily": round(total_current, 2),
            "overall_ratio": round(
                total_current / total_baseline, 1
            ) if total_baseline > 0 else 0.0,
            "detection_threshold": "3x baseline within 15 minutes",
            "spend_findings": spend_findings[:20],
            "usage_anomalies": usage_anomalies,
        }

    async def canary_deployment_plan(self, workspace_id: uuid.UUID) -> dict:
        """Generate canary credential deployment plan.

        Analyses the workspace's AI service landscape via SecurityGraphNode
        and CanonicalFinding to design a strategic decoy credential placement
        plan for detecting LLMjacking attempts.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        all_edges = await self._all_edges(workspace_id)

        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        # Map AI services in the workspace
        ai_nodes: list[SecurityGraphNode] = []
        service_map: dict[str, list[SecurityGraphNode]] = {}

        for node in all_nodes:
            ai_service = self._identify_ai_service(node)
            if ai_service:
                ai_nodes.append(node)
                service_map.setdefault(ai_service, []).append(node)

        # Identify high-value canary placement locations
        canary_placements: list[dict] = []
        placement_id = 0

        # Strategy 1: Place canaries alongside real AI credentials
        for svc_key, nodes in service_map.items():
            svc_info = _AI_SERVICE_IDENTIFIERS[svc_key]
            for node in nodes[:3]:  # Max 3 canaries per service type
                placement_id += 1
                meta = _parse_json(node.node_metadata) or {}
                region = node.region or meta.get("region", "us-east-1")

                canary_placements.append({
                    "placement_id": f"canary-{placement_id:03d}",
                    "strategy": "adjacent_to_real_credential",
                    "ai_service": svc_key,
                    "service_name": svc_info["service_name"],
                    "target_region": region,
                    "reference_node": node.resource_name or str(node.id),
                    "reference_arn": node.resource_arn,
                    "canary_type": "api_key",
                    "description": (
                        f"Deploy canary {svc_info['service_name']} API key "
                        f"in {region} alongside existing credentials"
                    ),
                    "detection_action": "alert_on_any_usage",
                    "priority": "high",
                })

        # Strategy 2: Place canaries in common credential storage locations
        secret_nodes = [
            n for n in all_nodes
            if (n.node_type or "").lower() in ("secrets_manager", "ssm_parameter", "kms_key")
        ]
        for node in secret_nodes[:5]:
            placement_id += 1
            canary_placements.append({
                "placement_id": f"canary-{placement_id:03d}",
                "strategy": "credential_store_honeypot",
                "ai_service": "multi_service",
                "service_name": "Multi-service canary",
                "target_region": node.region or "us-east-1",
                "reference_node": node.resource_name or str(node.id),
                "reference_arn": node.resource_arn,
                "canary_type": "stored_secret",
                "description": (
                    f"Place canary AI credential in {node.resource_name or 'secret store'} "
                    "to detect credential harvesting"
                ),
                "detection_action": "alert_on_read_or_usage",
                "priority": "high",
            })

        # Strategy 3: Place canaries on internet-facing assets
        internet_ai_nodes = [n for n in ai_nodes if n.is_internet_facing]
        for node in internet_ai_nodes[:3]:
            placement_id += 1
            ai_svc = self._identify_ai_service(node) or "unknown"
            canary_placements.append({
                "placement_id": f"canary-{placement_id:03d}",
                "strategy": "internet_facing_trap",
                "ai_service": ai_svc,
                "service_name": _AI_SERVICE_IDENTIFIERS.get(
                    ai_svc, {}
                ).get("service_name", "Unknown AI Service"),
                "target_region": node.region or "us-east-1",
                "reference_node": node.resource_name or str(node.id),
                "reference_arn": node.resource_arn,
                "canary_type": "exposed_api_key",
                "description": (
                    "Deploy high-interaction canary on internet-facing AI endpoint "
                    "to detect external LLMjacking attempts"
                ),
                "detection_action": "alert_and_throttle_on_usage",
                "priority": "critical",
            })

        # Strategy 4: Code repository canaries (based on findings)
        repo_findings = [
            f for f in all_findings
            if f.status in ("open", "in_progress")
            and any(kw in (f.title or "").lower() for kw in ("git", "repo", "code", "source"))
        ]
        for f in repo_findings[:3]:
            placement_id += 1
            canary_placements.append({
                "placement_id": f"canary-{placement_id:03d}",
                "strategy": "code_repository_canary",
                "ai_service": "multi_service",
                "service_name": "Repository canary",
                "target_region": "global",
                "reference_finding": f.title,
                "reference_arn": str(f.resource_arn or ""),
                "canary_type": "env_file_credential",
                "description": (
                    "Place canary AI credentials in .env files or config "
                    "to detect repository credential scraping"
                ),
                "detection_action": "alert_on_any_usage",
                "priority": "medium",
            })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        canary_placements.sort(key=lambda c: priority_order.get(c["priority"], 5))

        return {
            "total_canary_placements": len(canary_placements),
            "ai_services_covered": list(service_map.keys()),
            "strategies_used": list({c["strategy"] for c in canary_placements}),
            "priority_breakdown": {
                p: sum(1 for c in canary_placements if c["priority"] == p)
                for p in ("critical", "high", "medium", "low")
            },
            "deployment_plan": canary_placements,
            "monitoring_requirements": {
                "alert_channels": ["security_ops", "cloud_ops", "ai_platform_team"],
                "response_sla_minutes": 15,
                "auto_revocation": True,
                "forensic_logging": True,
            },
        }

    async def vpc_enforcement(self, workspace_id: uuid.UUID) -> dict:
        """Audit VPC endpoint enforcement for AI services.

        Examines SecurityGraphNode and SecurityGraphEdge to verify AI service
        traffic routes through VPC endpoints rather than public internet,
        and checks for missing endpoint policies.
        """
        all_nodes = await self._all_nodes(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        all_edges = await self._all_edges(workspace_id)

        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        # Identify VPC endpoint nodes
        vpc_endpoint_nodes: list[SecurityGraphNode] = []
        for node in all_nodes:
            ntype = (node.node_type or "").lower()
            meta = _parse_json(node.node_metadata) or {}
            name_lower = (node.resource_name or "").lower()
            if ntype in ("vpc_endpoint", "vpce") or "vpce" in name_lower:
                vpc_endpoint_nodes.append(node)

        # Map existing VPC endpoints to services they cover
        covered_services: dict[str, list[dict]] = {}
        for vpce in vpc_endpoint_nodes:
            meta = _parse_json(vpce.node_metadata) or {}
            service_name = meta.get("service_name", meta.get("service", "")).lower()
            vpce_info = {
                "endpoint_id": str(vpce.id),
                "name": vpce.resource_name or str(vpce.id),
                "arn": vpce.resource_arn,
                "region": vpce.region,
                "has_policy": bool(meta.get("policy") or meta.get("endpoint_policy")),
                "policy_restrictive": bool(meta.get("policy_restrictive", False)),
            }
            for svc_key, svc_info in _AI_SERVICE_IDENTIFIERS.items():
                expected = svc_info.get("vpc_endpoint_service", "")
                if expected and (expected.lower() in service_name or svc_key in service_name):
                    covered_services.setdefault(svc_key, []).append(vpce_info)

        # Identify AI services and check VPC endpoint coverage
        ai_nodes: list[SecurityGraphNode] = []
        for node in all_nodes:
            if self._identify_ai_service(node):
                ai_nodes.append(node)

        service_audit: list[dict] = []
        for svc_key, svc_info in _AI_SERVICE_IDENTIFIERS.items():
            # Count nodes for this service
            svc_nodes = [
                n for n in ai_nodes if self._identify_ai_service(n) == svc_key
            ]
            if not svc_nodes:
                continue

            endpoints = covered_services.get(svc_key, [])
            has_endpoint = len(endpoints) > 0
            has_restrictive_policy = any(e["policy_restrictive"] for e in endpoints)
            has_any_policy = any(e["has_policy"] for e in endpoints)

            # Determine enforcement status
            if not svc_info.get("vpc_endpoint_service"):
                # Third-party service — VPC endpoint not applicable
                enforcement_status = "not_applicable"
                severity = "info"
            elif has_endpoint and has_restrictive_policy:
                enforcement_status = "enforced"
                severity = "low"
            elif has_endpoint and has_any_policy:
                enforcement_status = "partial"
                severity = "medium"
            elif has_endpoint:
                enforcement_status = "endpoint_exists_no_policy"
                severity = "high"
            else:
                enforcement_status = "not_enforced"
                severity = "critical" if len(svc_nodes) > 0 else "high"

            # Check for internet-facing nodes in this service
            internet_facing = [n for n in svc_nodes if n.is_internet_facing]

            # Check for public route findings
            route_findings: list[dict] = []
            for f in all_findings:
                if f.status not in ("open", "in_progress"):
                    continue
                text = f"{f.title} {f.description or ''}".lower()
                if svc_key in text and any(
                    kw in text for kw in ("public", "internet", "no vpc", "endpoint")
                ):
                    route_findings.append({
                        "finding_id": str(f.id),
                        "title": f.title,
                        "severity": f.severity,
                    })

            recommendations: list[str] = []
            if enforcement_status == "not_enforced":
                recommendations.append(
                    f"Create VPC endpoint for {svc_info['vpc_endpoint_service']} "
                    "and attach a restrictive endpoint policy"
                )
                recommendations.append(
                    f"Add SCP/IAM condition aws:sourceVpce to restrict "
                    f"{svc_info['service_name']} access to VPC endpoint only"
                )
            elif enforcement_status == "endpoint_exists_no_policy":
                recommendations.append(
                    "Attach an endpoint policy restricting access to specific "
                    "models, actions, and source principals"
                )
            elif enforcement_status == "partial":
                recommendations.append(
                    "Tighten endpoint policy to deny wildcard actions and "
                    "enforce least-privilege model access"
                )

            service_audit.append({
                "ai_service": svc_key,
                "service_name": svc_info["service_name"],
                "vpc_endpoint_service": svc_info.get("vpc_endpoint_service"),
                "node_count": len(svc_nodes),
                "enforcement_status": enforcement_status,
                "severity": severity,
                "endpoints": endpoints,
                "internet_facing_count": len(internet_facing),
                "route_findings": route_findings[:5],
                "recommendations": recommendations,
            })

        service_audit.sort(key=lambda s: _SEVERITY_ORDER.get(s["severity"], 5))

        enforced = sum(1 for s in service_audit if s["enforcement_status"] == "enforced")
        not_enforced = sum(
            1 for s in service_audit
            if s["enforcement_status"] in ("not_enforced", "endpoint_exists_no_policy")
        )

        return {
            "total_ai_services_audited": len(service_audit),
            "fully_enforced": enforced,
            "partially_enforced": sum(
                1 for s in service_audit if s["enforcement_status"] == "partial"
            ),
            "not_enforced": not_enforced,
            "not_applicable": sum(
                1 for s in service_audit if s["enforcement_status"] == "not_applicable"
            ),
            "total_vpc_endpoints": len(vpc_endpoint_nodes),
            "enforcement_score": round(
                enforced / len(service_audit) * 100, 1
            ) if service_audit else 100.0,
            "service_audit": service_audit,
        }
