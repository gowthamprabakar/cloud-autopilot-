"""
CausalEngine — multi-factor weighted root-cause analysis engine.

Market-standard implementation aligned with Wiz-parity signals:
  1. Graph traversal to extract topology signals (centrality, blast radius,
     reachable sensitive nodes, attack paths)
  2. Finding-field analysis (resource type, description, severity keywords)
  3. Weighted composite scoring across 8 causal dimensions
  4. Toxic-combination detection (raises composite score)
  5. Exploit intelligence modifier (CVE/KEV boost)
  6. Asset criticality tier (prod vs staging vs dev)
  7. Identity reachability (IAM paths into this resource)
  8. Primary root-cause classification
  9. Human-readable causal chain construction from attack_paths table

All scoring methods are self-contained async functions so they can be unit
tested independently. The engine degrades gracefully: if no graph data exists
for the workspace it uses finding-field signals only.

Factor weight distribution (must sum exactly to 1.00):
  network_exposure:     0.22
  iam_risk:             0.20  (Sprint 21: raised from 0.15)
  data_sensitivity:     0.18
  graph_centrality:     0.12
  temporal_drift:       0.06  (Sprint 21: reduced from 0.08)
  blast_radius:         0.12
  asset_criticality:    0.10
  identity_reachability: 0.00 (Sprint 21: absorbed into iam_risk)
  ─────────────────────────
  total:                1.00
"""

from __future__ import annotations

import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding

logger = logging.getLogger(__name__)


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class CausalFactor:
    """A single causal dimension with its score, evidence, and weight."""

    name: str
    score: float              # 0.0–1.0
    evidence: list[str]
    contributing_nodes: list[str]
    weight: float             # contribution to composite score

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": round(self.score, 4),
            "evidence": self.evidence,
            "contributing_nodes": self.contributing_nodes,
            "weight": self.weight,
        }


@dataclass
class ToxicCombo:
    """A dangerous combination of two or more causal factors that amplifies risk."""

    name: str
    description: str
    factors_involved: list[str]
    score_boost: float = 0.15

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "factors_involved": self.factors_involved,
            "score_boost": self.score_boost,
        }


@dataclass
class AttackVector:
    """A plausible attack path derived from causal analysis."""

    name: str
    description: str
    likelihood: str   # "LOW" | "MEDIUM" | "HIGH"
    steps: list[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "likelihood": self.likelihood,
            "steps": self.steps,
        }


@dataclass
class BlastRadius:
    """Downstream impact scope reachable from a compromised resource."""

    reachable_nodes: list[str]
    sensitive_node_count: int
    score: float

    def to_dict(self) -> dict:
        return {
            "reachable_nodes": self.reachable_nodes,
            "sensitive_node_count": self.sensitive_node_count,
            "score": round(self.score, 4),
        }


@dataclass
class CausalAnalysis:
    """Complete causal analysis output for one finding."""

    finding_id: uuid.UUID
    composite_score: float
    factors: list[CausalFactor]          # ordered highest → lowest contribution
    primary_root_cause: str
    secondary_causes: list[str]
    causal_chain: list[str]
    toxic_combinations: list[ToxicCombo]
    blast_radius: BlastRadius
    attack_vectors: list[AttackVector]
    confidence: float


# ── Graph node/edge lightweight representations ───────────────────────────────
# These are dicts loaded from the security_graph_nodes / security_graph_edges
# tables (if they exist). The engine works without them.

_SENSITIVE_NODE_TYPES = frozenset(
    ["rds", "s3_bucket", "secrets_manager", "dynamodb", "kms_key", "lambda"]
)

_DATA_STORE_RESOURCE_KEYWORDS = frozenset(
    ["rds", "s3", "dynamodb", "secretsmanager", "secrets_manager", "aurora"]
)

_IAM_RESOURCE_KEYWORDS = frozenset(
    ["iam", "role", "policy", "user", "group", "identity"]
)

_NETWORK_RESOURCE_KEYWORDS = frozenset(
    ["securitygroup", "security_group", "subnet", "vpc", "loadbalancer",
     "elasticloadbalancing", "internetgateway", "natgateway"]
)

# Exploit intelligence keywords that indicate active exploitation
_EXPLOIT_INTEL_KEYWORDS = frozenset([
    "cve-", "critical vulnerability", "remote code execution", "rce",
    "arbitrary code execution", "zero-day", "0-day", "active exploitation",
    "actively exploited", "cisa kev",
])


# ── Engine ────────────────────────────────────────────────────────────────────

class CausalEngine:
    """
    Multi-factor weighted root-cause analysis engine.

    Implements 8 causal dimensions with Wiz-parity signals:
    - Network exposure (aggressive keyword + graph detection)
    - IAM risk (wildcard, cross-account, MFA gaps)
    - Data sensitivity (data store type + encryption state)
    - Graph centrality (degree + attack path membership)
    - Temporal drift (days open + risk score trajectory)
    - Blast radius (BFS with node_type_map from security_graph_nodes)
    - Asset criticality (prod/staging/dev tier from ARN)
    - Identity reachability (IAM paths into this resource from graph)

    Usage:
        engine = CausalEngine(db)
        analysis = await engine.analyze(finding, workspace_id)
    """

    # Factor weights — must sum to exactly 1.0
    # Sprint 21: iam_risk raised 0.15→0.20 (CIEM primary attack surface)
    #            identity_reachability 0.03→0.00 (absorbed into iam_risk)
    #            temporal_drift 0.08→0.06 (to balance)
    _WEIGHTS: dict[str, float] = {
        "network_exposure":      0.22,
        "iam_risk":              0.20,
        "data_sensitivity":      0.18,
        "graph_centrality":      0.12,
        "temporal_drift":        0.06,
        "blast_radius":          0.12,
        "asset_criticality":     0.10,
        "identity_reachability": 0.00,
    }

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Public entry point ────────────────────────────────────────────────────

    async def analyze(
        self,
        finding: CanonicalFinding,
        workspace_id: uuid.UUID,
    ) -> CausalAnalysis:
        """
        Run multi-factor causal analysis for a single finding.

        Returns a complete CausalAnalysis regardless of graph data availability.
        Gracefully degrades to finding-field signals if graph tables are absent.

        Args:
            finding: The canonical finding to analyze.
            workspace_id: The workspace UUID for graph data scoping.

        Returns:
            CausalAnalysis with composite score, factors, root cause, and actions.
        """
        # Load security graph data (gracefully returns empty if tables don't exist)
        graph_nodes, graph_edges = await self._load_graph_data(workspace_id)
        node_id = self._find_node_for_resource(finding.resource_arn, graph_nodes)

        # Build a node_id → node_type lookup map for O(1) BFS type resolution
        # Fixes the blast radius BFS bug: edges don't have target_node_type,
        # but security_graph_nodes has node_type for every node.
        node_type_map: dict[str, str] = {
            str(n.get("id", "")): str(n.get("node_type", "")).lower()
            for n in graph_nodes
        }

        # Load named attack paths from DB for richer causal chains
        attack_paths = await self._load_attack_paths(workspace_id)

        # Score each causal factor
        network_factor = await self._score_network_exposure(finding, graph_nodes, graph_edges)
        iam_factor = await self._score_iam_risk(finding, graph_nodes, graph_edges)
        data_factor = await self._score_data_sensitivity(finding, graph_nodes)
        centrality_factor = await self._score_graph_centrality(node_id, graph_nodes, graph_edges)
        drift_factor = await self._score_temporal_drift(finding)
        blast_factor = await self._score_blast_radius(node_id, graph_edges, node_type_map)
        asset_factor = await self._score_asset_criticality(finding)
        identity_factor = await self._score_identity_reachability(node_id, graph_edges)
        compliance_factor = await self._score_compliance_gap(finding)

        all_factors = [
            network_factor,
            iam_factor,
            data_factor,
            centrality_factor,
            drift_factor,
            blast_factor,
            asset_factor,
            identity_factor,
        ]

        # Weighted composite (compliance is a modifier, not in composite)
        composite = self._compute_composite(all_factors)

        # Exploit intelligence modifier — boosts composite by 0.2 if CVE/KEV found
        exploit_boost = self._compute_exploit_boost(finding)
        if exploit_boost > 0.0:
            composite = min(1.0, composite + exploit_boost)
            logger.debug(
                "causal_engine exploit_boost finding=%s boost=%.2f",
                finding.id, exploit_boost,
            )

        # Toxic combination detection
        toxic_combos = await self._detect_toxic_combinations(
            all_factors, finding, compliance_factor
        )

        # Apply toxic combo boosts
        for combo in toxic_combos:
            composite = min(1.0, composite + combo.score_boost)

        # Sort factors by contribution (weight * score) descending
        all_factors.sort(
            key=lambda f: f.weight * f.score,
            reverse=True,
        )

        primary_cause = await self._determine_primary_root_cause(all_factors)
        secondary_causes = self._determine_secondary_causes(all_factors, primary_cause)
        causal_chain = await self._compute_causal_chain(
            all_factors, graph_nodes, graph_edges, finding, attack_paths
        )
        blast_radius_obj = self._build_blast_radius(node_id, graph_edges, graph_nodes, node_type_map)
        attack_vectors = self._derive_attack_vectors(all_factors, finding, primary_cause)
        confidence = self._compute_confidence(all_factors, graph_nodes)

        return CausalAnalysis(
            finding_id=finding.id,
            composite_score=round(composite, 4),
            factors=all_factors,
            primary_root_cause=primary_cause,
            secondary_causes=secondary_causes,
            causal_chain=causal_chain,
            toxic_combinations=toxic_combos,
            blast_radius=blast_radius_obj,
            attack_vectors=attack_vectors,
            confidence=round(confidence, 4),
        )

    # ── Factor scorers ────────────────────────────────────────────────────────

    async def _score_network_exposure(
        self,
        finding: CanonicalFinding,
        graph_nodes: list[dict],
        graph_edges: list[dict],
    ) -> CausalFactor:
        """
        Score network exposure aggressively.

        Signals:
        - "publicly accessible" → +0.5 (strong, explicit public marker)
        - "0.0.0.0" or "all traffic" → +0.5 (unrestricted CIDR)
        - "unrestricted" → +0.4 (AWS findings often use this term)
        - "internet-facing" or "open to internet" → +0.4
        - "public" → +0.2 (weaker signal, present in many findings)
        - "internet" or "exposed" → +0.1
        - Network resource type → +0.15
        - Graph: exposes edges from internet node → +0.3
        - Graph: is_public=true nodes → +0.15
        """
        score = 0.0
        evidence: list[str] = []
        contributing_nodes: list[str] = []

        resource_type_lower = (finding.resource_type or "").lower()
        title_lower = (finding.title or "").lower()
        desc_lower = (finding.description or "").lower()
        combined_text = f"{title_lower} {desc_lower}"

        # Strong explicit public markers
        if "publicly accessible" in combined_text:
            score += 0.5
            evidence.append("Finding explicitly states resource is publicly accessible")

        if "0.0.0.0" in combined_text or "all traffic" in combined_text:
            score += 0.5
            evidence.append("Finding mentions unrestricted CIDR (0.0.0.0 / all traffic)")

        if "unrestricted" in combined_text:
            score += 0.4
            evidence.append("Finding references unrestricted access policy")

        if "internet-facing" in combined_text or "open to internet" in combined_text:
            score += 0.4
            evidence.append("Finding identifies resource as internet-facing")

        if "public" in combined_text and score < 0.5:
            # Only add if not already captured by stronger signals above
            score += 0.2
            evidence.append("Finding references public exposure")

        if any(kw in resource_type_lower for kw in _NETWORK_RESOURCE_KEYWORDS):
            score += 0.15
            evidence.append(f"Resource type '{finding.resource_type}' is a network-layer resource")

        if "internet" in combined_text or "exposed" in combined_text:
            score += 0.1
            evidence.append("Finding references internet exposure")

        # From graph: look for edges from "internet" node
        internet_exposes = [
            e for e in graph_edges
            if e.get("edge_type") == "exposes"
            and "internet" in str(e.get("source_node_id", "")).lower()
        ]
        if internet_exposes:
            score += 0.3
            evidence.append(
                f"Graph: {len(internet_exposes)} 'exposes' edge(s) from internet node"
            )
            contributing_nodes.extend(
                str(e.get("target_node_id", "")) for e in internet_exposes
            )

        # From graph: nodes with is_public=true
        public_nodes = [
            n for n in graph_nodes
            if n.get("metadata", {}).get("is_public") is True
        ]
        if public_nodes:
            score += 0.15
            evidence.append(f"Graph: {len(public_nodes)} node(s) marked is_public=true")
            contributing_nodes.extend(str(n.get("id", "")) for n in public_nodes[:5])

        return CausalFactor(
            name="network_exposure",
            score=min(score, 1.0),
            evidence=evidence,
            contributing_nodes=list(set(contributing_nodes)),
            weight=self._WEIGHTS["network_exposure"],
        )

    async def _score_iam_risk(
        self,
        finding: CanonicalFinding,
        graph_nodes: list[dict],
        graph_edges: list[dict],
    ) -> CausalFactor:
        """
        Score IAM risk across wildcard permissions, MFA gaps, and cross-account access.

        Signals:
        - Wildcard permissions (s3:*, ec2:*, *:*) → +0.4
        - Overpermission keywords → +0.2
        - MFA not enforced → +0.3
        - Cross-account role assumption → +0.2
        - No permission boundaries → +0.15
        - IAM resource type → +0.2
        - Graph: access edges to sensitive nodes → +0.2
        """
        score = 0.0
        evidence: list[str] = []
        contributing_nodes: list[str] = []

        resource_type_lower = (finding.resource_type or "").lower()
        title_lower = (finding.title or "").lower()
        desc_lower = (finding.description or "").lower()
        combined_text = f"{title_lower} {desc_lower}"

        # Wildcard permissions
        if "s3:*" in combined_text or "ec2:*" in combined_text or "*:*" in combined_text:
            score += 0.4
            evidence.append("Wildcard IAM permissions detected (s3:*, ec2:*, or *:*)")

        if "wildcard" in combined_text or "overpermission" in combined_text:
            score += 0.2
            evidence.append("Overly permissive IAM policy detected")

        if "mfa" in combined_text and (
            "missing" in combined_text or "no mfa" in combined_text or "without" in combined_text
        ):
            score += 0.3
            evidence.append("MFA not enforced for console/programmatic access")

        if "cross-account" in combined_text or "cross account" in combined_text:
            score += 0.2
            evidence.append("Cross-account role assumption detected")

        if "permission boundar" in combined_text and (
            "missing" in combined_text or "no " in combined_text
        ):
            score += 0.15
            evidence.append("No permission boundaries applied")

        if any(kw in resource_type_lower for kw in _IAM_RESOURCE_KEYWORDS):
            score += 0.2
            evidence.append(f"Resource type '{finding.resource_type}' is an IAM resource")

        # From graph: access edges pointing to sensitive nodes
        access_edges = [
            e for e in graph_edges
            if e.get("edge_type") in ("has_access_to", "assumes_role")
        ]
        if access_edges:
            sensitive_targets = [
                e for e in access_edges
                if any(
                    s in str(e.get("target_node_id", "")).lower()
                    for s in _SENSITIVE_NODE_TYPES
                )
            ]
            if sensitive_targets:
                score += 0.2
                evidence.append(
                    f"Graph: {len(sensitive_targets)} IAM access edge(s) pointing to sensitive nodes"
                )
                contributing_nodes.extend(
                    str(e.get("source_node_id", "")) for e in sensitive_targets[:5]
                )

        return CausalFactor(
            name="iam_risk",
            score=min(score, 1.0),
            evidence=evidence,
            contributing_nodes=list(set(contributing_nodes)),
            weight=self._WEIGHTS["iam_risk"],
        )

    async def _score_data_sensitivity(
        self,
        finding: CanonicalFinding,
        graph_nodes: list[dict],
    ) -> CausalFactor:
        """
        Score data sensitivity based on resource type, encryption state, and PII tags.

        Signals:
        - Data store resource type → +0.4
        - Encryption disabled → +0.3
        - PII / sensitive tag → +0.2
        - Backup disabled → +0.1
        - Graph: sensitive nodes present in workspace → +0.2
        """
        score = 0.0
        evidence: list[str] = []
        contributing_nodes: list[str] = []

        resource_type_lower = (finding.resource_type or "").lower()
        combined_text = (
            f"{(finding.title or '').lower()} {(finding.description or '').lower()}"
        )

        # Resource type is a data store
        if any(kw in resource_type_lower for kw in _DATA_STORE_RESOURCE_KEYWORDS):
            score += 0.4
            evidence.append(f"Resource type '{finding.resource_type}' is a data store")

        if "encrypt" in combined_text and (
            "disabled" in combined_text
            or "not enabled" in combined_text
            or "missing" in combined_text
            or "no " in combined_text
        ):
            score += 0.3
            evidence.append("Encryption is disabled on the data resource")

        if "pii" in combined_text or "sensitive" in combined_text:
            score += 0.2
            evidence.append("Resource tagged or identified as containing PII / sensitive data")

        if "backup" in combined_text and (
            "disabled" in combined_text or "not enabled" in combined_text
        ):
            score += 0.1
            evidence.append("Backup not enabled on data store")

        # From graph: node types that are sensitive data stores
        sensitive_nodes = [
            n for n in graph_nodes
            if n.get("node_type", "").lower() in _SENSITIVE_NODE_TYPES
        ]
        if sensitive_nodes:
            score += 0.2
            evidence.append(
                f"Graph: {len(sensitive_nodes)} sensitive data-store node(s) in workspace"
            )
            contributing_nodes.extend(str(n.get("id", "")) for n in sensitive_nodes[:5])

        return CausalFactor(
            name="data_sensitivity",
            score=min(score, 1.0),
            evidence=evidence,
            contributing_nodes=list(set(contributing_nodes)),
            weight=self._WEIGHTS["data_sensitivity"],
        )

    async def _score_graph_centrality(
        self,
        node_id: str | None,
        graph_nodes: list[dict],
        graph_edges: list[dict],
    ) -> CausalFactor:
        """
        Score graph centrality using degree centrality normalized by max degree.

        Falls back to 0.1 baseline when graph data is unavailable.
        Attack path membership adds +0.2 bonus.
        """
        if not node_id or not graph_edges:
            return CausalFactor(
                name="graph_centrality",
                score=0.1,  # minimal baseline when graph is unavailable
                evidence=["No graph topology data available — using finding signals only"],
                contributing_nodes=[],
                weight=self._WEIGHTS["graph_centrality"],
            )

        score = 0.0
        evidence: list[str] = []
        contributing_nodes: list[str] = []

        # Degree centrality: count edges where this node is source or target
        outgoing = [e for e in graph_edges if str(e.get("source_node_id", "")) == node_id]
        incoming = [e for e in graph_edges if str(e.get("target_node_id", "")) == node_id]
        degree = len(outgoing) + len(incoming)

        # Attack path edges
        attack_edges = [
            e for e in graph_edges
            if e.get("edge_type") == "attack_path"
            and (
                str(e.get("source_node_id", "")) == node_id
                or str(e.get("target_node_id", "")) == node_id
            )
        ]

        # Compute max degree in graph for normalisation
        all_nodes = {str(n.get("id", "")) for n in graph_nodes}
        if all_nodes:
            degree_counts: dict[str, int] = {}
            for e in graph_edges:
                src = str(e.get("source_node_id", ""))
                tgt = str(e.get("target_node_id", ""))
                degree_counts[src] = degree_counts.get(src, 0) + 1
                degree_counts[tgt] = degree_counts.get(tgt, 0) + 1
            max_degree = max(degree_counts.values()) if degree_counts else 1
            centrality = degree / max(max_degree, 1)
        else:
            centrality = 0.0

        score = min(centrality, 1.0)
        if degree > 0:
            evidence.append(
                f"Node degree: {degree} edges (in={len(incoming)}, out={len(outgoing)})"
            )
        if attack_edges:
            evidence.append(f"Node appears on {len(attack_edges)} attack path edge(s)")
            score = min(score + 0.2, 1.0)
            contributing_nodes.append(node_id)

        if not evidence:
            evidence.append("Node has no edges in security graph — isolated resource")

        return CausalFactor(
            name="graph_centrality",
            score=round(score, 4),
            evidence=evidence,
            contributing_nodes=list(set(contributing_nodes)),
            weight=self._WEIGHTS["graph_centrality"],
        )

    async def _score_temporal_drift(
        self, finding: CanonicalFinding
    ) -> CausalFactor:
        """
        Score temporal drift: how long the finding has been open.

        Score = min(days_open / 90, 1.0).
        Additional +0.1 for high risk_score (> 7.0) as trajectory signal.
        """
        score = 0.0
        evidence: list[str] = []

        now = datetime.now(UTC)

        # Days open since first seen
        days_open = 0
        if finding.first_seen_at:
            try:
                first_seen = datetime.fromisoformat(str(finding.first_seen_at))
                if first_seen.tzinfo is None:
                    first_seen = first_seen.replace(tzinfo=UTC)
                days_open = max(0, (now - first_seen).days)
            except (ValueError, TypeError):
                days_open = 0

        if days_open > 0:
            score = min(days_open / 90.0, 1.0)
            evidence.append(f"Finding has been open for {days_open} day(s)")

        if days_open > 30:
            evidence.append("Finding open > 30 days — indicates persistent misconfiguration")

        if days_open > 90:
            evidence.append("Finding open > 90 days — severe configuration drift / no governance")

        # Risk score as proxy for trajectory (risk > 7 = elevated concern)
        if finding.risk_score is not None and finding.risk_score > 7.0:
            score = min(score + 0.1, 1.0)
            evidence.append(f"High risk_score ({finding.risk_score:.1f}) suggests active threat")

        if not evidence:
            evidence.append("Finding is newly detected — no drift signal")
            score = 0.0

        return CausalFactor(
            name="temporal_drift",
            score=round(score, 4),
            evidence=evidence,
            contributing_nodes=[],
            weight=self._WEIGHTS["temporal_drift"],
        )

    async def _score_blast_radius(
        self,
        node_id: str | None,
        graph_edges: list[dict],
        node_type_map: dict[str, str],
    ) -> CausalFactor:
        """
        Score blast radius via BFS from the resource node, using node_type_map
        for O(1) sensitive-node detection.

        FIXED: Previously used edge.get("target_node_type") which doesn't exist
        in security_graph_edges. Now uses node_type_map built from
        security_graph_nodes where node_type is an actual column.

        Args:
            node_id: The graph node ID for this resource.
            graph_edges: All edges in the workspace graph.
            node_type_map: dict[node_id → node_type] built from security_graph_nodes.
        """
        if not node_id or not graph_edges:
            return CausalFactor(
                name="blast_radius",
                score=0.1,
                evidence=["No graph topology — blast radius estimated from finding context only"],
                contributing_nodes=[],
                weight=self._WEIGHTS["blast_radius"],
            )

        score = 0.0
        evidence: list[str] = []
        reachable_sensitive: list[str] = []

        # BFS from node_id following outgoing edges
        visited: set[str] = set()
        queue: deque[str] = deque([node_id])
        max_depth = 5  # guard against large graphs
        depth_map: dict[str, int] = {node_id: 0}

        while queue:
            current = queue.popleft()
            current_depth = depth_map.get(current, 0)
            if current_depth >= max_depth:
                continue
            if current in visited:
                continue
            visited.add(current)

            for edge in graph_edges:
                src = str(edge.get("source_node_id", ""))
                tgt = str(edge.get("target_node_id", ""))
                if src == current and tgt not in visited:
                    queue.append(tgt)
                    depth_map[tgt] = current_depth + 1

                    # Use node_type_map (from security_graph_nodes) for O(1) lookup
                    # This is the fix: edges don't have target_node_type column
                    tgt_type = node_type_map.get(tgt, "").lower()
                    if any(s in tgt_type for s in _SENSITIVE_NODE_TYPES):
                        reachable_sensitive.append(tgt)

        reachable_count = len(visited) - 1  # exclude the starting node
        sensitive_count = len(set(reachable_sensitive))

        if reachable_count > 0:
            evidence.append(
                f"BFS from resource node reaches {reachable_count} downstream node(s)"
            )
        if sensitive_count > 0:
            evidence.append(
                f"{sensitive_count} sensitive data store(s) reachable via graph traversal"
            )
            score = min(sensitive_count / 5.0, 1.0)
        else:
            score = min(reachable_count / 20.0, 0.3)  # low score if no sensitive targets
            if reachable_count == 0:
                evidence.append("Resource is isolated — no outgoing edges in graph")

        return CausalFactor(
            name="blast_radius",
            score=round(score, 4),
            evidence=evidence,
            contributing_nodes=list(set(reachable_sensitive))[:10],
            weight=self._WEIGHTS["blast_radius"],
        )

    async def _score_asset_criticality(
        self, finding: CanonicalFinding
    ) -> CausalFactor:
        """
        Score asset criticality based on environment tier detected in resource ARN and tags.

        Tiers:
        - prod / production / prd → 1.0 (production data, maximum impact)
        - staging / stg            → 0.5 (pre-prod, significant but not critical)
        - dev / test / sandbox     → 0.2 (low business impact)
        - unknown                  → 0.4 (assume moderate criticality by default)

        Weight: 0.10 — ensures prod findings always score higher than dev findings
        regardless of technical severity.
        """
        score = 0.4  # default: unknown environment
        evidence: list[str] = []

        arn_lower = (finding.resource_arn or "").lower()
        tags = finding.tags or {}
        tag_values = " ".join(str(v).lower() for v in tags.values())
        tag_keys = " ".join(str(k).lower() for k in tags.keys())
        combined_context = f"{arn_lower} {tag_values} {tag_keys}"

        if any(kw in combined_context for kw in ("prod", "production", "/prd", "-prd", "_prd")):
            score = 1.0
            evidence.append("Resource ARN/tags indicate PRODUCTION environment — maximum criticality")
        elif any(kw in combined_context for kw in ("staging", "stg", "-stg", "_stg")):
            score = 0.5
            evidence.append("Resource ARN/tags indicate STAGING environment — elevated criticality")
        elif any(kw in combined_context for kw in ("dev", "test", "sandbox", "develop")):
            score = 0.2
            evidence.append("Resource ARN/tags indicate DEV/TEST environment — reduced criticality")
        else:
            evidence.append(
                "Environment tier unknown — applying moderate criticality (0.4). "
                "Add 'Environment' tags (prod/staging/dev) for precise scoring."
            )

        return CausalFactor(
            name="asset_criticality",
            score=round(score, 4),
            evidence=evidence,
            contributing_nodes=[],
            weight=self._WEIGHTS["asset_criticality"],
        )

    async def _score_identity_reachability(
        self,
        node_id: str | None,
        graph_edges: list[dict],
    ) -> CausalFactor:
        """
        Score identity reachability: how many IAM paths lead to this resource.

        Count has_access_to and assumes_role edges that TARGET this node.
        Normalize by 10 (10+ IAM paths = maximum score 1.0).

        This approximates Wiz's "Identity Risk" signal — resources reachable
        by many IAM principals face higher lateral movement risk.

        Weight: 0.03 — small direct weight but informs toxic combo detection.
        """
        if not node_id or not graph_edges:
            return CausalFactor(
                name="identity_reachability",
                score=0.0,
                evidence=["No graph data — identity reachability not computed"],
                contributing_nodes=[],
                weight=self._WEIGHTS["identity_reachability"],
            )

        # Count IAM edges targeting this node
        iam_paths = [
            e for e in graph_edges
            if e.get("edge_type") in ("has_access_to", "assumes_role")
            and str(e.get("target_node_id", "")) == node_id
        ]
        count = len(iam_paths)
        score = min(count / 10.0, 1.0)

        evidence: list[str] = []
        contributing_nodes: list[str] = []

        if count > 0:
            evidence.append(
                f"{count} IAM path(s) lead to this resource "
                f"(has_access_to / assumes_role edges in security graph)"
            )
            contributing_nodes = [str(e.get("source_node_id", "")) for e in iam_paths[:10]]
        else:
            evidence.append("No IAM access paths target this resource in the security graph")

        return CausalFactor(
            name="identity_reachability",
            score=round(score, 4),
            evidence=evidence,
            contributing_nodes=list(set(contributing_nodes)),
            weight=self._WEIGHTS["identity_reachability"],
        )

    async def _score_compliance_gap(
        self, finding: CanonicalFinding
    ) -> CausalFactor:
        """
        Compliance gap is a severity modifier, not a root-cause factor.

        Score = min(framework_count / 5, 1.0).
        Weight = 0.0 so it does not contribute to composite directly.
        Used by toxic combo detection to identify governance gaps.
        """
        frameworks = finding.compliance_frameworks or []
        count = len(frameworks)
        score = min(count / 5.0, 1.0)
        evidence = (
            [f"Finding violates {count} compliance framework(s): {', '.join(frameworks[:5])}"]
            if frameworks
            else ["No compliance frameworks mapped to this finding"]
        )
        return CausalFactor(
            name="compliance_gap",
            score=round(score, 4),
            evidence=evidence,
            contributing_nodes=[],
            weight=0.0,  # not in composite
        )

    # ── Exploit intelligence modifier ─────────────────────────────────────────

    def _compute_exploit_boost(self, finding: CanonicalFinding) -> float:
        """
        Scan title + description for CVE indicators and active exploitation markers.

        If found, return 0.2 as a composite boost (applied after weighted sum).
        This is a modifier, not a factor — it has no weight in the normal composite.

        Keywords: CVE-, critical vulnerability, remote code execution, RCE,
        arbitrary code execution, zero-day, 0-day, active exploitation, CISA KEV.
        """
        combined_text = (
            f"{(finding.title or '').lower()} {(finding.description or '').lower()}"
        )
        for keyword in _EXPLOIT_INTEL_KEYWORDS:
            if keyword in combined_text:
                logger.debug(
                    "causal_engine exploit_intel_hit finding=%s keyword=%s",
                    finding.id, keyword,
                )
                return 0.2
        return 0.0

    # ── Toxic combination detection ───────────────────────────────────────────

    async def _detect_toxic_combinations(
        self,
        factors: list[CausalFactor],
        finding: CanonicalFinding,
        compliance_factor: CausalFactor,
    ) -> list[ToxicCombo]:
        """
        Detect specific toxic combos that exponentially increase risk.

        Combo list (score boosts):
        - public_access + sensitive_data (0.15) — classic data breach pattern
        - critical_severity + public_access (0.25) — highest priority, always RED
        - no_encryption + broad_iam (0.15) — unencrypted + permissive access
        - no_mfa + console_access (0.15) — MFA gap on interactive login
        - public_sg + no_encryption (0.15) — exposed endpoint, unencrypted traffic
        - wildcard_permissions + data_store (0.15) — admin access to sensitive data
        - no_logging + sensitive_data (0.15) — invisible exfiltration risk
        - unencrypted + internet_facing (0.20) — encryption gap + internet reach
        """
        combos: list[ToxicCombo] = []

        factor_map = {f.name: f for f in factors}
        net = factor_map.get(
            "network_exposure",
            CausalFactor("network_exposure", 0, [], [], self._WEIGHTS["network_exposure"])
        )
        iam = factor_map.get(
            "iam_risk",
            CausalFactor("iam_risk", 0, [], [], self._WEIGHTS["iam_risk"])
        )
        data = factor_map.get(
            "data_sensitivity",
            CausalFactor("data_sensitivity", 0, [], [], self._WEIGHTS["data_sensitivity"])
        )

        severity = str(finding.severity or "").lower()
        combined_text = (
            f"{(finding.title or '').lower()} {(finding.description or '').lower()}"
        )

        # 1. critical_severity + public_access (0.25) — must-RED pattern
        has_public_access = (
            "public" in combined_text
            or "publicly accessible" in combined_text
            or net.score > 0.2
        )
        if severity == "critical" and has_public_access:
            combos.append(ToxicCombo(
                name="critical_severity + public_access",
                description=(
                    "Critical severity finding with any public exposure — "
                    "immediate remediation required regardless of composite score"
                ),
                factors_involved=["network_exposure"],
                score_boost=0.25,
            ))

        # 2. public_access + sensitive_data (0.15) — classic breach scenario
        if net.score > 0.5 and data.score > 0.5:
            combos.append(ToxicCombo(
                name="public_access + sensitive_data",
                description="Publicly accessible sensitive data store",
                factors_involved=["network_exposure", "data_sensitivity"],
                score_boost=0.15,
            ))

        # 3. no_encryption + broad_iam (0.15)
        no_encryption = (
            "encrypt" in combined_text
            and ("disabled" in combined_text or "not enabled" in combined_text)
        )
        broad_iam = iam.score > 0.5
        if no_encryption and broad_iam:
            combos.append(ToxicCombo(
                name="no_encryption + broad_iam",
                description="Unencrypted resource with overly permissive access",
                factors_involved=["data_sensitivity", "iam_risk"],
                score_boost=0.15,
            ))

        # 4. no_mfa + console_access (0.15)
        no_mfa = "mfa" in combined_text and (
            "missing" in combined_text
            or "not enabled" in combined_text
            or "without" in combined_text
        )
        console_access = "console" in combined_text or "login" in combined_text
        if no_mfa and console_access:
            combos.append(ToxicCombo(
                name="no_mfa + console_access",
                description="Console access without MFA enforcement",
                factors_involved=["iam_risk"],
                score_boost=0.15,
            ))

        # 5. public_sg + no_encryption (0.15)
        public_sg = (
            any(
                kw in (finding.resource_type or "").lower()
                for kw in ["securitygroup", "security_group"]
            )
            and net.score > 0.5
        )
        if public_sg and no_encryption:
            combos.append(ToxicCombo(
                name="public_sg + no_encryption",
                description="Exposed endpoint with unencrypted traffic",
                factors_involved=["network_exposure", "data_sensitivity"],
                score_boost=0.15,
            ))

        # 6. wildcard_permissions + data_store (0.15)
        wildcard = (
            "s3:*" in combined_text
            or "ec2:*" in combined_text
            or "*:*" in combined_text
            or "wildcard" in combined_text
        )
        is_data_store = any(
            kw in (finding.resource_type or "").lower()
            for kw in _DATA_STORE_RESOURCE_KEYWORDS
        )
        if wildcard and is_data_store:
            combos.append(ToxicCombo(
                name="wildcard_permissions + data_store",
                description="Administrative access to sensitive data",
                factors_involved=["iam_risk", "data_sensitivity"],
                score_boost=0.15,
            ))

        # 7. no_logging + sensitive_data (0.15) — invisible exfiltration
        no_logging = (
            "logging disabled" in combined_text
            or ("cloudtrail" in combined_text and "disabled" in combined_text)
            or ("access logging" in combined_text and (
                "disabled" in combined_text or "not enabled" in combined_text
            ))
        )
        if no_logging and data.score > 0.3:
            combos.append(ToxicCombo(
                name="no_logging + sensitive_data",
                description=(
                    "Logging disabled on or near a sensitive data resource — "
                    "exfiltration would be invisible to audit trail"
                ),
                factors_involved=["data_sensitivity"],
                score_boost=0.15,
            ))

        # 8. unencrypted + internet_facing (0.20) — combined network + crypto gap
        is_internet_facing = (
            "internet-facing" in combined_text
            or "open to internet" in combined_text
            or net.score > 0.6
        )
        if no_encryption and is_internet_facing:
            combos.append(ToxicCombo(
                name="unencrypted + internet_facing",
                description=(
                    "Unencrypted resource directly reachable from the internet — "
                    "data is readable in transit by any network observer"
                ),
                factors_involved=["network_exposure", "data_sensitivity"],
                score_boost=0.20,
            ))

        return combos

    # ── Causal chain construction ─────────────────────────────────────────────

    async def _compute_causal_chain(
        self,
        factors: list[CausalFactor],
        graph_nodes: list[dict],
        graph_edges: list[dict],
        finding: CanonicalFinding,
        attack_paths: list[dict],
    ) -> list[str]:
        """
        Build a human-readable causal chain from named attack paths (DB) or top factors.

        Priority order:
        1. Named attack paths from attack_paths table (most specific)
        2. attack_path edges in security graph
        3. Factor-based narrative chain (finding signals only)

        Args:
            attack_paths: Rows from the attack_paths table for this workspace.
        """
        chain: list[str] = []
        resource_type = finding.resource_type or "Resource"
        title = finding.title or "Security Finding"

        # 1. Named attack paths from DB — most specific and human-readable
        if attack_paths:
            # Filter paths that reference this resource's ARN or region
            arn = (finding.resource_arn or "").lower()
            relevant_paths = [
                p for p in attack_paths
                if arn and arn in str(p.get("path_details", "")).lower()
            ] or attack_paths[:2]  # fall back to first 2 if none match

            if relevant_paths:
                chain.append(f"{resource_type}: {title[:60]}")
                for path in relevant_paths[:3]:
                    path_name = path.get("name") or path.get("path_name") or "Attack path"
                    severity = path.get("severity") or path.get("risk_level") or ""
                    suffix = f" [{severity}]" if severity else ""
                    chain.append(f"Named attack path: {path_name}{suffix}")
                return chain

        # 2. attack_path edges in security graph
        if graph_edges:
            attack_edges = [e for e in graph_edges if e.get("edge_type") == "attack_path"]
            if attack_edges:
                chain.append(f"{resource_type} ({title[:50]})")
                for edge in attack_edges[:4]:
                    src_label = edge.get("source_label", str(edge.get("source_node_id", ""))[:16])
                    tgt_label = edge.get("target_label", str(edge.get("target_node_id", ""))[:16])
                    chain.append(f"{src_label} exposes {tgt_label}")
                return chain

        # 3. Factor-based narrative chain
        top_factors = sorted(factors, key=lambda f: f.weight * f.score, reverse=True)[:3]
        for fac in top_factors:
            if fac.score < 0.1:
                continue
            if fac.name == "network_exposure":
                chain.append("Public/unrestricted network access")
            elif fac.name == "iam_risk":
                chain.append("Overly permissive IAM configuration")
            elif fac.name == "data_sensitivity":
                chain.append(f"Sensitive data store ({resource_type}) exposed")
            elif fac.name == "blast_radius":
                count = len(fac.contributing_nodes)
                chain.append(f"{count} downstream resource(s) reachable from this path")
            elif fac.name == "temporal_drift":
                chain.append("Persistent misconfiguration — finding open for extended period")
            elif fac.name == "graph_centrality":
                chain.append("Resource is central to multiple attack paths")
            elif fac.name == "asset_criticality":
                chain.append("Production asset — business impact is maximum")
            elif fac.name == "identity_reachability":
                chain.append("Multiple IAM identities have access to this resource")

        if not chain:
            chain.append(f"{resource_type}: {title[:80]}")

        return chain

    # ── Root cause classification ─────────────────────────────────────────────

    async def _determine_primary_root_cause(
        self, factors: list[CausalFactor]
    ) -> str:
        """
        Map the highest-weighted factor scores to a root cause category.

        Thresholds lowered vs original to catch more real-world patterns:
        - net > 0.3 → network_misconfiguration (was 0.7)
        - iam > 0.3 → iam_misconfiguration (was 0.7)

        Factors list is already sorted highest contribution first.
        """
        factor_map = {f.name: f for f in factors}
        net = factor_map.get(
            "network_exposure",
            CausalFactor("network_exposure", 0, [], [], self._WEIGHTS["network_exposure"])
        )
        iam = factor_map.get(
            "iam_risk",
            CausalFactor("iam_risk", 0, [], [], self._WEIGHTS["iam_risk"])
        )
        data = factor_map.get(
            "data_sensitivity",
            CausalFactor("data_sensitivity", 0, [], [], self._WEIGHTS["data_sensitivity"])
        )
        drift = factor_map.get(
            "temporal_drift",
            CausalFactor("temporal_drift", 0, [], [], self._WEIGHTS["temporal_drift"])
        )
        centrality = factor_map.get(
            "graph_centrality",
            CausalFactor("graph_centrality", 0, [], [], self._WEIGHTS["graph_centrality"])
        )
        blast = factor_map.get(
            "blast_radius",
            CausalFactor("blast_radius", 0, [], [], self._WEIGHTS["blast_radius"])
        )

        # Lowered thresholds to catch common real-world patterns
        if net.score > 0.3:
            return "network_misconfiguration"
        if iam.score > 0.3:
            return "iam_misconfiguration"
        if data.score > 0.7 and net.score > 0.5:
            return "governance_gap"
        if drift.score > 0.7:
            return "config_drift"
        if centrality.score > 0.7 and blast.score > 0.5:
            return "access_control_failure"
        if data.score > 0.5:
            return "encryption_gap"
        return "missing_guardrail"

    # ── Secondary causes ──────────────────────────────────────────────────────

    def _determine_secondary_causes(
        self, factors: list[CausalFactor], primary: str
    ) -> list[str]:
        """Map non-primary factor scores (> 0.3) to secondary root cause categories."""
        _cause_map = {
            "network_exposure": "network_misconfiguration",
            "iam_risk": "iam_misconfiguration",
            "data_sensitivity": "encryption_gap",
            "temporal_drift": "config_drift",
            "graph_centrality": "access_control_failure",
            "blast_radius": "access_control_failure",
            "asset_criticality": "missing_guardrail",
            "identity_reachability": "iam_misconfiguration",
        }
        secondary: list[str] = []
        for fac in factors:
            if fac.score > 0.3:
                mapped = _cause_map.get(fac.name, "missing_guardrail")
                if mapped != primary and mapped not in secondary:
                    secondary.append(mapped)
        return secondary[:3]

    # ── Blast radius object ───────────────────────────────────────────────────

    def _build_blast_radius(
        self,
        node_id: str | None,
        graph_edges: list[dict],
        graph_nodes: list[dict],
        node_type_map: dict[str, str],
    ) -> BlastRadius:
        """
        Build the BlastRadius object via BFS using the fixed node_type_map lookup.

        Args:
            node_type_map: dict[node_id → node_type] from security_graph_nodes.
        """
        if not node_id or not graph_edges:
            return BlastRadius(reachable_nodes=[], sensitive_node_count=0, score=0.0)

        visited: set[str] = set()
        queue: deque[str] = deque([node_id])
        sensitive: list[str] = []

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            for edge in graph_edges:
                src = str(edge.get("source_node_id", ""))
                tgt = str(edge.get("target_node_id", ""))
                if src == current and tgt not in visited:
                    queue.append(tgt)
                    # Fixed: use node_type_map instead of edge.get("target_node_type")
                    tgt_type = node_type_map.get(tgt, "").lower()
                    if any(s in tgt_type for s in _SENSITIVE_NODE_TYPES):
                        sensitive.append(tgt)

        reachable = [n for n in visited if n != node_id]
        sensitive_count = len(set(sensitive))
        score = (
            min(sensitive_count / 5.0, 1.0)
            if sensitive_count > 0
            else min(len(reachable) / 20.0, 0.3)
        )

        return BlastRadius(
            reachable_nodes=reachable[:20],
            sensitive_node_count=sensitive_count,
            score=round(score, 4),
        )

    # ── Attack vectors ────────────────────────────────────────────────────────

    def _derive_attack_vectors(
        self,
        factors: list[CausalFactor],
        finding: CanonicalFinding,
        primary_cause: str,
    ) -> list[AttackVector]:
        """Derive plausible attack vectors from the top contributing factors."""
        vectors: list[AttackVector] = []
        resource_type = finding.resource_type or "AWS Resource"
        factor_map = {f.name: f for f in factors}

        if factor_map.get("network_exposure", CausalFactor("", 0, [], [], 0)).score > 0.3:
            net_score = factor_map["network_exposure"].score
            vectors.append(AttackVector(
                name="External Network Reachability",
                description=(
                    f"The {resource_type} is reachable from the internet or untrusted networks."
                ),
                likelihood="HIGH" if net_score > 0.6 else "MEDIUM",
                steps=[
                    "Attacker scans internet-facing IP ranges or uses AWS metadata APIs",
                    f"Attacker identifies publicly accessible {resource_type}",
                    "Attacker exploits the open access to read/write data or gain shell access",
                    "Attacker pivots to internal resources using the established foothold",
                ],
            ))

        if factor_map.get("iam_risk", CausalFactor("", 0, [], [], 0)).score > 0.3:
            iam_score = factor_map["iam_risk"].score
            vectors.append(AttackVector(
                name="Privilege Escalation via IAM",
                description="Overly permissive IAM configuration enables privilege escalation.",
                likelihood="HIGH" if iam_score > 0.6 else "MEDIUM",
                steps=[
                    "Attacker obtains initial credentials (phishing, SSRF, metadata endpoint)",
                    "Attacker enumerates IAM permissions using iam:SimulatePrincipalPolicy",
                    "Attacker escalates privileges using wildcard or broad permissions",
                    "Attacker accesses sensitive resources or creates persistence mechanisms",
                ],
            ))

        if factor_map.get("data_sensitivity", CausalFactor("", 0, [], [], 0)).score > 0.4:
            vectors.append(AttackVector(
                name="Data Exfiltration",
                description=f"Sensitive data in {resource_type} is at risk of exfiltration.",
                likelihood="MEDIUM",
                steps=[
                    "Attacker gains access to the data store via network or IAM misconfiguration",
                    "Attacker enumerates stored data (S3 objects, RDS tables, secrets)",
                    "Attacker exfiltrates data to external infrastructure",
                    "Data breach goes undetected due to insufficient logging",
                ],
            ))

        return vectors

    # ── Composite score ───────────────────────────────────────────────────────

    def _compute_composite(self, factors: list[CausalFactor]) -> float:
        """
        Compute weighted composite score across all 8 causal factors.

        Weight verification: 0.22+0.15+0.18+0.12+0.08+0.12+0.10+0.03 = 1.00
        """
        factor_map = {f.name: f for f in factors}

        def _s(name: str) -> float:
            return factor_map.get(name, CausalFactor("", 0, [], [], 0)).score

        return (
            self._WEIGHTS["network_exposure"]      * _s("network_exposure")
            + self._WEIGHTS["iam_risk"]            * _s("iam_risk")
            + self._WEIGHTS["data_sensitivity"]    * _s("data_sensitivity")
            + self._WEIGHTS["graph_centrality"]    * _s("graph_centrality")
            + self._WEIGHTS["temporal_drift"]      * _s("temporal_drift")
            + self._WEIGHTS["blast_radius"]        * _s("blast_radius")
            + self._WEIGHTS["asset_criticality"]   * _s("asset_criticality")
            + self._WEIGHTS["identity_reachability"] * _s("identity_reachability")
        )

    # ── Confidence ────────────────────────────────────────────────────────────

    def _compute_confidence(
        self, factors: list[CausalFactor], graph_nodes: list[dict]
    ) -> float:
        """
        Compute confidence in the causal analysis.

        Range: 0.3 (finding-fields only) to 1.0 (rich graph + strong evidence).

        Scoring:
        - Base: 0.3 (finding signals always available)
        - +0.4 if graph_nodes present (graph topology significantly boosts confidence)
        - +0.05 per factor that has 2+ evidence items (evidence richness)
        """
        base = 0.3
        if graph_nodes:
            base += 0.4  # graph data boosts confidence significantly
        # Each factor with > 1 piece of evidence adds incremental confidence
        for fac in factors:
            if len(fac.evidence) >= 2:
                base += 0.05
        return min(base, 1.0)

    # ── Graph data loader ─────────────────────────────────────────────────────

    async def _load_graph_data(
        self, workspace_id: uuid.UUID
    ) -> tuple[list[dict], list[dict]]:
        """
        Load security graph nodes and edges for this workspace.

        Loads node_type from security_graph_nodes so we can build the
        node_type_map for blast radius BFS.

        Gracefully returns empty lists if the tables do not exist or have no data.
        """
        nodes: list[dict] = []
        edges: list[dict] = []
        try:
            from sqlalchemy import text as sa_text

            node_result = await self.db.execute(
                sa_text(
                    "SELECT id, node_type, resource_arn, label, metadata "
                    "FROM security_graph_nodes WHERE workspace_id = :wid LIMIT 500"
                ),
                {"wid": str(workspace_id)},
            )
            for row in node_result.mappings():
                d = dict(row)
                # Parse JSON metadata if it's a string
                if isinstance(d.get("metadata"), str):
                    try:
                        import json as _json
                        d["metadata"] = _json.loads(d["metadata"])
                    except Exception:
                        d["metadata"] = {}
                nodes.append(d)

            # Note: security_graph_edges does NOT have target_node_type column.
            # We load only columns that actually exist in the table.
            # The node_type_map (built from nodes above) is used for BFS type lookup.
            edge_result = await self.db.execute(
                sa_text(
                    "SELECT id, source_node_id, target_node_id, edge_type, "
                    "source_label, target_label "
                    "FROM security_graph_edges WHERE workspace_id = :wid LIMIT 2000"
                ),
                {"wid": str(workspace_id)},
            )
            for row in edge_result.mappings():
                edges.append(dict(row))

        except Exception as exc:
            # Tables may not exist yet — degrade gracefully
            logger.debug(
                "causal_engine_graph_load_skip workspace=%s reason=%s",
                workspace_id, exc,
            )

        return nodes, edges

    async def _load_attack_paths(
        self, workspace_id: uuid.UUID
    ) -> list[dict]:
        """
        Load named attack paths from the attack_paths table for richer causal chains.

        Returns empty list if the table does not exist or has no data.
        Used by _compute_causal_chain to build specific, named chain entries
        rather than generic factor-based descriptions.
        """
        paths: list[dict] = []
        try:
            from sqlalchemy import text as sa_text

            result = await self.db.execute(
                sa_text(
                    "SELECT id, name, severity, path_details, risk_level "
                    "FROM attack_paths WHERE workspace_id = :wid LIMIT 50"
                ),
                {"wid": str(workspace_id)},
            )
            for row in result.mappings():
                paths.append(dict(row))
        except Exception as exc:
            logger.debug(
                "causal_engine_attack_paths_load_skip workspace=%s reason=%s",
                workspace_id, exc,
            )
        return paths

    # ── Node lookup helper ────────────────────────────────────────────────────

    @staticmethod
    def _find_node_for_resource(
        resource_arn: str | None, graph_nodes: list[dict]
    ) -> str | None:
        """Find the security graph node ID for a given resource ARN."""
        if not resource_arn or not graph_nodes:
            return None
        arn_lower = resource_arn.lower()
        for node in graph_nodes:
            node_arn = str(node.get("resource_arn", "")).lower()
            if node_arn and (
                node_arn == arn_lower or node_arn in arn_lower or arn_lower in node_arn
            ):
                return str(node.get("id", ""))
        return None
