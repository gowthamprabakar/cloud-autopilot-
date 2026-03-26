"""
KSPMModule — Kubernetes Security Posture Management simulation.

Sprint 33: Simulates K8s security:
1. RBAC audit (ClusterRole wildcards, escalation)
2. Network policy coverage
3. Admission controller assessment
4. Pod-to-cloud pivot paths
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

_K8S_NODE_TYPES = {
    "eks_cluster", "eks_nodegroup", "eks_pod", "eks_service",
    "eks_namespace", "eks_service_account", "eks_role",
    "eks_clusterrole", "eks_network_policy",
}

_K8S_RESOURCE_PREFIXES = [
    "AWS::EKS%", "AWS::Kubernetes%", "AWS::K8s%",
]

# RBAC wildcards and over-privilege patterns
_RBAC_WILDCARD_KEYWORDS = [
    "wildcard", "cluster-admin", "clusterrole *",
    "resources: *", "verbs: *", "apiGroups: *",
    "system:masters", "cluster-admin binding",
]

_RBAC_ESCALATION_KEYWORDS = [
    "escalate", "bind", "impersonate",
    "create clusterrolebinding", "create rolebinding",
    "secrets access", "get secrets", "list secrets",
    "privileged", "hostPID", "hostNetwork",
]

# Network policy gap indicators
_NETPOL_KEYWORDS = [
    "network policy", "networkpolicy", "ingress", "egress",
    "default deny", "allow all", "unprotected",
]

# Admission controller assessment keywords
_ADMISSION_KEYWORDS = [
    "admission controller", "opa", "gatekeeper", "kyverno",
    "pod security", "pod security policy", "psp",
    "pod security standard", "restricted", "baseline", "privileged",
    "securitycontext", "runasnonroot", "readonlyrootfilesystem",
]

# Pod-to-cloud pivot indicators
_PIVOT_KEYWORDS = [
    "imds", "instance metadata", "169.254.169.254",
    "iam role", "service account annotation",
    "irsa", "eks pod identity", "aws-auth",
    "cloud credential", "env credential",
    "mounted secret", "aws_access_key",
]

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
    """Return list of matched keywords found in text."""
    lower = text.lower()
    return [kw for kw in keywords if kw.lower() in lower]


# ── Service ───────────────────────────────────────────────────────────────────

class KSPMModule:
    """Kubernetes Security Posture Management — audits RBAC, network policies,
    admission controllers, and pod-to-cloud pivot paths."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _k8s_nodes(
        self, workspace_id: uuid.UUID,
    ) -> list[SecurityGraphNode]:
        q = select(SecurityGraphNode).where(
            SecurityGraphNode.workspace_id == workspace_id,
            SecurityGraphNode.node_type.in_(list(_K8S_NODE_TYPES)),
        )
        return list((await self.db.execute(q)).scalars().all())

    async def _k8s_findings(
        self, workspace_id: uuid.UUID,
    ) -> list[CanonicalFinding]:
        """Fetch findings related to EKS/Kubernetes resources."""
        conditions = [
            CanonicalFinding.resource_type.like(p) for p in _K8S_RESOURCE_PREFIXES
        ]
        # Also match by title keywords
        conditions.append(CanonicalFinding.title.ilike("%kubernetes%"))
        conditions.append(CanonicalFinding.title.ilike("%eks%"))
        conditions.append(CanonicalFinding.title.ilike("%k8s%"))
        conditions.append(CanonicalFinding.title.ilike("%pod%"))
        conditions.append(CanonicalFinding.title.ilike("%container%"))

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

    def _node_finding_text(
        self,
        node: SecurityGraphNode,
        findings_by_arn: dict[str, list[CanonicalFinding]],
        all_findings: list[CanonicalFinding],
    ) -> tuple[str, list[CanonicalFinding]]:
        """Aggregate text from all findings linked to a node."""
        matched: list[CanonicalFinding] = []
        arn = node.resource_arn or ""
        matched.extend(findings_by_arn.get(arn, []))

        finding_ids = {str(fid) for fid in (_parse_json(node.finding_ids) or [])}
        for f in all_findings:
            if str(f.id) in finding_ids and f not in matched:
                matched.append(f)

        combined_text = " ".join(
            f"{f.title} {f.description or ''}" for f in matched
        )
        return combined_text, matched

    # ── Public API ───────────────────────────────────────────────────────

    async def rbac_audit(self, workspace_id: uuid.UUID) -> dict:
        """Audit Kubernetes RBAC for over-privileged roles.

        Detects wildcard permissions, cluster-admin bindings, privilege
        escalation verbs (bind/escalate/impersonate), and secrets access.
        """
        k8s_nodes = await self._k8s_nodes(workspace_id)
        k8s_findings = await self._k8s_findings(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        edges = await self._all_edges(workspace_id)

        # Index findings by ARN
        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in k8s_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        rbac_nodes = [
            n for n in k8s_nodes
            if n.node_type in ("eks_role", "eks_clusterrole", "eks_service_account")
        ]

        audit_results: list[dict] = []

        for node in rbac_nodes:
            meta = _parse_json(node.node_metadata) or {}
            combined_text, matched_findings = self._node_finding_text(
                node, findings_by_arn, all_findings,
            )

            # Also include metadata in text scan
            meta_text = json.dumps(meta)
            full_text = f"{combined_text} {meta_text} {node.resource_name or ''}"

            wildcard_matches = _match_keywords(full_text, _RBAC_WILDCARD_KEYWORDS)
            escalation_matches = _match_keywords(full_text, _RBAC_ESCALATION_KEYWORDS)

            has_wildcard = len(wildcard_matches) > 0
            has_escalation = len(escalation_matches) > 0

            # Determine severity
            if has_wildcard and has_escalation:
                severity = "critical"
            elif has_wildcard or (has_escalation and len(escalation_matches) >= 2):
                severity = "high"
            elif has_escalation:
                severity = "medium"
            else:
                severity = "low"

            # Count edges that involve this node (role bindings, etc.)
            binding_count = sum(
                1 for e in edges
                if (e.source_node_id == node.id or e.target_node_id == node.id)
                and e.edge_type in ("assumes_role", "has_access_to", "USES_ADMIN_ROLE")
            )

            open_finding_count = sum(
                1 for f in matched_findings
                if f.status in ("open", "in_progress")
            )

            audit_results.append({
                "id": str(node.id),
                "name": node.resource_name or node.resource_arn or str(node.id),
                "node_type": node.node_type,
                "resource_arn": node.resource_arn,
                "has_wildcard_permissions": has_wildcard,
                "wildcard_patterns": wildcard_matches[:5],
                "has_escalation_risk": has_escalation,
                "escalation_patterns": escalation_matches[:5],
                "severity": severity,
                "binding_count": binding_count,
                "open_findings": open_finding_count,
                "risk_score": node.risk_score,
                "namespace": meta.get("namespace", "cluster-wide"),
            })

        # Sort: critical first, then by risk score
        audit_results.sort(key=lambda r: (
            _SEVERITY_ORDER.get(r["severity"], 5),
            -(r["risk_score"] or 0),
        ))

        return {
            "total_rbac_entities": len(audit_results),
            "wildcard_roles": sum(1 for r in audit_results if r["has_wildcard_permissions"]),
            "escalation_risk_roles": sum(1 for r in audit_results if r["has_escalation_risk"]),
            "severity_breakdown": {
                sev: sum(1 for r in audit_results if r["severity"] == sev)
                for sev in ("critical", "high", "medium", "low")
            },
            "rbac_entities": audit_results,
        }

    async def network_policy_audit(self, workspace_id: uuid.UUID) -> dict:
        """Assess network policy coverage across namespaces.

        Identifies namespaces without default-deny policies, pods without
        network policy coverage, and overly permissive ingress/egress rules.
        """
        k8s_nodes = await self._k8s_nodes(workspace_id)
        k8s_findings = await self._k8s_findings(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in k8s_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        namespaces = [n for n in k8s_nodes if n.node_type == "eks_namespace"]
        netpol_nodes = [n for n in k8s_nodes if n.node_type == "eks_network_policy"]
        pods = [n for n in k8s_nodes if n.node_type == "eks_pod"]

        # Build namespace -> network policies map
        netpol_by_namespace: dict[str, list[SecurityGraphNode]] = {}
        for np in netpol_nodes:
            meta = _parse_json(np.node_metadata) or {}
            ns = meta.get("namespace", "default")
            netpol_by_namespace.setdefault(ns, []).append(np)

        namespace_results: list[dict] = []

        for ns_node in namespaces:
            meta = _parse_json(ns_node.node_metadata) or {}
            ns_name = ns_node.resource_name or meta.get("name", "unknown")
            ns_policies = netpol_by_namespace.get(ns_name, [])

            # Check for default-deny via findings or policy metadata
            has_default_deny = False
            overly_permissive = False
            for pol in ns_policies:
                pol_meta = _parse_json(pol.node_metadata) or {}
                pol_text = json.dumps(pol_meta).lower()
                if "default-deny" in pol_text or "deny-all" in pol_text:
                    has_default_deny = True
                if "allow-all" in pol_text or "0.0.0.0/0" in pol_text:
                    overly_permissive = True

            # Check findings for netpol issues
            combined_text, matched = self._node_finding_text(
                ns_node, findings_by_arn, all_findings,
            )
            netpol_matches = _match_keywords(combined_text, _NETPOL_KEYWORDS)

            # Count pods in this namespace
            ns_pods = [
                p for p in pods
                if (_parse_json(p.node_metadata) or {}).get("namespace") == ns_name
            ]

            # Determine coverage status
            if not ns_policies:
                coverage_status = "no_policies"
                severity = "high"
            elif not has_default_deny:
                coverage_status = "no_default_deny"
                severity = "medium"
            elif overly_permissive:
                coverage_status = "overly_permissive"
                severity = "medium"
            else:
                coverage_status = "covered"
                severity = "low"

            namespace_results.append({
                "namespace": ns_name,
                "node_id": str(ns_node.id),
                "policy_count": len(ns_policies),
                "pod_count": len(ns_pods),
                "has_default_deny": has_default_deny,
                "overly_permissive": overly_permissive,
                "coverage_status": coverage_status,
                "severity": severity,
                "finding_matches": netpol_matches[:5],
            })

        namespace_results.sort(key=lambda r: _SEVERITY_ORDER.get(r["severity"], 5))

        return {
            "total_namespaces": len(namespace_results),
            "namespaces_without_policies": sum(
                1 for r in namespace_results if r["coverage_status"] == "no_policies"
            ),
            "namespaces_without_default_deny": sum(
                1 for r in namespace_results if r["coverage_status"] == "no_default_deny"
            ),
            "total_network_policies": len(netpol_nodes),
            "namespace_assessments": namespace_results,
        }

    async def admission_controller_assessment(self, workspace_id: uuid.UUID) -> dict:
        """Evaluate admission controller coverage.

        Checks for OPA/Gatekeeper/Kyverno presence, Pod Security Standards
        enforcement, and security context configuration gaps.
        """
        k8s_nodes = await self._k8s_nodes(workspace_id)
        k8s_findings = await self._k8s_findings(workspace_id)
        all_findings = await self._all_findings(workspace_id)

        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in k8s_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        # Scan all K8s nodes for admission controller evidence
        admission_signals: dict[str, bool] = {
            "opa_gatekeeper": False,
            "kyverno": False,
            "pod_security_standards": False,
            "pod_security_policies": False,
        }

        all_admission_findings: list[dict] = []
        security_context_issues: list[dict] = []

        for node in k8s_nodes:
            meta = _parse_json(node.node_metadata) or {}
            meta_text = json.dumps(meta).lower()
            combined_text, matched_findings = self._node_finding_text(
                node, findings_by_arn, all_findings,
            )
            full_text = f"{combined_text} {meta_text} {node.resource_name or ''}"

            # Detect admission controller types
            if "gatekeeper" in full_text.lower() or "opa" in full_text.lower():
                admission_signals["opa_gatekeeper"] = True
            if "kyverno" in full_text.lower():
                admission_signals["kyverno"] = True
            if "pod security standard" in full_text.lower() or "pss" in meta_text:
                admission_signals["pod_security_standards"] = True
            if "podsecuritypolicy" in full_text.lower() or "psp" in meta_text:
                admission_signals["pod_security_policies"] = True

            admission_matches = _match_keywords(full_text, _ADMISSION_KEYWORDS)
            if admission_matches:
                for f in matched_findings:
                    if f.status in ("open", "in_progress"):
                        all_admission_findings.append({
                            "finding_id": str(f.id),
                            "title": f.title,
                            "severity": f.severity,
                            "resource_arn": f.resource_arn,
                            "matched_patterns": admission_matches[:3],
                        })

            # Check pods for security context issues
            if node.node_type == "eks_pod":
                issues: list[str] = []
                if meta.get("privileged", False):
                    issues.append("privileged_container")
                if not meta.get("runAsNonRoot", False):
                    issues.append("runs_as_root")
                if not meta.get("readOnlyRootFilesystem", False):
                    issues.append("writable_root_filesystem")
                if meta.get("hostPID", False):
                    issues.append("host_pid_access")
                if meta.get("hostNetwork", False):
                    issues.append("host_network_access")

                if issues:
                    security_context_issues.append({
                        "pod_id": str(node.id),
                        "pod_name": node.resource_name or str(node.id),
                        "namespace": meta.get("namespace", "default"),
                        "issues": issues,
                        "issue_count": len(issues),
                        "severity": "critical" if "privileged_container" in issues else "high",
                    })

        # Deduplicate admission findings by finding_id
        seen_ids: set[str] = set()
        unique_findings: list[dict] = []
        for af in all_admission_findings:
            if af["finding_id"] not in seen_ids:
                seen_ids.add(af["finding_id"])
                unique_findings.append(af)

        has_any_controller = any(admission_signals.values())

        # Overall assessment
        if not has_any_controller:
            overall_status = "no_admission_controllers"
            overall_severity = "critical"
        elif len(security_context_issues) > 5:
            overall_status = "significant_gaps"
            overall_severity = "high"
        elif security_context_issues:
            overall_status = "minor_gaps"
            overall_severity = "medium"
        else:
            overall_status = "adequate"
            overall_severity = "low"

        security_context_issues.sort(key=lambda i: (
            _SEVERITY_ORDER.get(i["severity"], 5),
            -i["issue_count"],
        ))

        return {
            "overall_status": overall_status,
            "overall_severity": overall_severity,
            "admission_controllers_detected": admission_signals,
            "has_admission_controller": has_any_controller,
            "total_admission_findings": len(unique_findings),
            "admission_findings": unique_findings[:20],
            "total_security_context_issues": len(security_context_issues),
            "security_context_issues": security_context_issues[:20],
        }

    async def pod_cloud_pivots(self, workspace_id: uuid.UUID) -> dict:
        """Identify pod-to-cloud pivot paths (IMDS, service accounts).

        Detects paths where a compromised pod can access cloud credentials
        via IMDS, IRSA, mounted secrets, or environment variables.
        """
        k8s_nodes = await self._k8s_nodes(workspace_id)
        all_nodes = await self._all_nodes(workspace_id)
        k8s_findings = await self._k8s_findings(workspace_id)
        all_findings = await self._all_findings(workspace_id)
        edges = await self._all_edges(workspace_id)

        findings_by_arn: dict[str, list[CanonicalFinding]] = {}
        for f in k8s_findings:
            findings_by_arn.setdefault(f.resource_arn or "", []).append(f)

        node_map: dict[uuid.UUID, SecurityGraphNode] = {n.id: n for n in all_nodes}

        # Build adjacency from K8s nodes to cloud nodes
        pods = [n for n in k8s_nodes if n.node_type in ("eks_pod", "eks_service_account")]

        pivot_paths: list[dict] = []

        for pod in pods:
            meta = _parse_json(pod.node_metadata) or {}
            combined_text, matched_findings = self._node_finding_text(
                pod, findings_by_arn, all_findings,
            )
            meta_text = json.dumps(meta)
            full_text = f"{combined_text} {meta_text} {pod.resource_name or ''}"

            pivot_matches = _match_keywords(full_text, _PIVOT_KEYWORDS)
            if not pivot_matches:
                continue

            # Find outgoing edges from this pod to IAM/cloud resources
            cloud_targets: list[dict] = []
            for edge in edges:
                if edge.source_node_id != pod.id:
                    continue
                target = node_map.get(edge.target_node_id)
                if not target:
                    continue
                # Check if target is a cloud resource (not K8s)
                if target.node_type not in _K8S_NODE_TYPES:
                    cloud_targets.append({
                        "target_id": str(target.id),
                        "target_name": target.resource_name or str(target.id),
                        "target_type": target.node_type,
                        "edge_type": edge.edge_type,
                        "is_attack_path": bool(edge.is_attack_path),
                        "risk_contribution": edge.risk_contribution,
                    })

            # Determine pivot type
            pivot_types: list[str] = []
            lower_text = full_text.lower()
            if "imds" in lower_text or "169.254.169.254" in lower_text:
                pivot_types.append("IMDS")
            if "irsa" in lower_text or "service account annotation" in lower_text:
                pivot_types.append("IRSA")
            if "eks pod identity" in lower_text:
                pivot_types.append("EKS_POD_IDENTITY")
            if "mounted secret" in lower_text or "aws_access_key" in lower_text:
                pivot_types.append("CREDENTIAL_IN_POD")
            if "env credential" in lower_text:
                pivot_types.append("ENV_CREDENTIAL")
            if not pivot_types:
                pivot_types.append("UNKNOWN")

            severity = "critical" if cloud_targets else "high"
            if any(ct["is_attack_path"] for ct in cloud_targets):
                severity = "critical"

            pivot_paths.append({
                "pod_id": str(pod.id),
                "pod_name": pod.resource_name or str(pod.id),
                "pod_type": pod.node_type,
                "namespace": meta.get("namespace", "default"),
                "pivot_types": pivot_types,
                "pivot_indicators": pivot_matches[:5],
                "cloud_targets": cloud_targets,
                "cloud_target_count": len(cloud_targets),
                "severity": severity,
                "risk_score": pod.risk_score,
                "is_internet_facing": bool(pod.is_internet_facing),
            })

        # Sort: internet-facing + critical first
        pivot_paths.sort(key=lambda p: (
            _SEVERITY_ORDER.get(p["severity"], 5),
            not p["is_internet_facing"],
            -(p["risk_score"] or 0),
        ))

        return {
            "total_pivot_paths": len(pivot_paths),
            "critical_pivots": sum(1 for p in pivot_paths if p["severity"] == "critical"),
            "pivot_type_breakdown": {
                pt: sum(1 for p in pivot_paths if pt in p["pivot_types"])
                for pt in ["IMDS", "IRSA", "EKS_POD_IDENTITY", "CREDENTIAL_IN_POD", "ENV_CREDENTIAL"]
            },
            "pivot_paths": pivot_paths,
        }
