"""
Graph router — Neo4j security graph API endpoints.

Sprint 31: Exposes graph query, ingest, and analytics endpoints.
"""

from __future__ import annotations
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.graph_rag_service import GraphRAGService

router = APIRouter(prefix="/graph", tags=["graph"])

_svc = GraphRAGService()


# ── Request / Response Schemas ───────────────────────────────

class ResourceNodeIn(BaseModel):
    arn: str
    type: str
    name: str
    region: str = ""
    account_id: str = ""
    risk_score: float = 0.0
    is_internet_facing: bool = False


class IdentityNodeIn(BaseModel):
    arn: str
    type: str  # iam_role | iam_user
    name: str
    permission_scope: str = ""
    has_mfa: bool = False
    policies: str = "[]"


class FindingNodeIn(BaseModel):
    finding_id: str
    title: str
    severity: str = "medium"
    status: str = "open"
    cve_id: str = ""
    epss_score: float = 0.0
    in_kev: bool = False


class EdgeIn(BaseModel):
    from_arn: str
    to_arn: str
    edge_type: str
    properties: dict = Field(default_factory=dict)


class BulkIngestIn(BaseModel):
    resources: list[ResourceNodeIn] = Field(default_factory=list)
    identities: list[IdentityNodeIn] = Field(default_factory=list)
    findings: list[FindingNodeIn] = Field(default_factory=list)
    edges: list[EdgeIn] = Field(default_factory=list)


# ── Endpoints ────────────────────────────────────────────────

@router.get("/summary")
async def graph_summary() -> dict:
    """Graph statistics — node/edge counts by type."""
    return await _svc.graph_summary()


@router.get("/attack-paths")
async def attack_paths(
    source_arn: str = Query(..., description="ARN of the source node"),
    max_depth: int = Query(6, ge=1, le=12, description="Maximum traversal depth"),
) -> list[dict]:
    """Find attack paths originating from a given resource."""
    return await _svc.find_attack_paths(source_arn, max_depth)


@router.get("/blast-radius")
async def blast_radius(
    node_arn: str = Query(..., description="ARN of the compromised node"),
    max_hops: int = Query(4, ge=1, le=10, description="Maximum hops"),
) -> dict:
    """Compute blast radius from a compromised node."""
    return await _svc.compute_blast_radius(node_arn, max_hops)


@router.get("/toxic-combinations")
async def toxic_combinations() -> list[dict]:
    """Detect toxic combinations: internet-facing resources with multiple critical findings."""
    return await _svc.detect_toxic_combinations()


@router.post("/ingest")
async def bulk_ingest(payload: BulkIngestIn) -> dict:
    """Bulk ingest resources, identities, findings, and edges into the security graph."""
    results = {
        "resources_upserted": 0,
        "identities_upserted": 0,
        "findings_upserted": 0,
        "edges_created": 0,
        "errors": [],
    }

    for resource in payload.resources:
        try:
            await _svc.upsert_resource_node(resource.model_dump())
            results["resources_upserted"] += 1
        except Exception as e:
            results["errors"].append(f"resource {resource.arn}: {e}")

    for identity in payload.identities:
        try:
            await _svc.upsert_identity_node(identity.model_dump())
            results["identities_upserted"] += 1
        except Exception as e:
            results["errors"].append(f"identity {identity.arn}: {e}")

    for finding in payload.findings:
        try:
            await _svc.upsert_finding_node(finding.model_dump())
            results["findings_upserted"] += 1
        except Exception as e:
            results["errors"].append(f"finding {finding.finding_id}: {e}")

    for edge in payload.edges:
        try:
            await _svc.create_edge(edge.from_arn, edge.to_arn, edge.edge_type, edge.properties)
            results["edges_created"] += 1
        except Exception as e:
            results["errors"].append(f"edge {edge.from_arn}->{edge.to_arn}: {e}")

    return results
