"""
Security graph schemas — request/response contracts for /api/v1/security-graph.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SecurityGraphNodeResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    node_type: str
    resource_arn: str | None
    resource_name: str | None
    region: str | None
    # Python attr is node_metadata; expose as 'metadata' in JSON
    metadata: dict = Field(validation_alias="node_metadata")
    finding_ids: list[str]
    risk_score: float | None
    is_internet_facing: bool
    is_sensitive_data: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SecurityGraphEdgeResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    edge_type: str
    is_attack_path: bool
    risk_contribution: float | None
    # Python attr is edge_metadata; expose as 'metadata' in JSON
    metadata: dict = Field(validation_alias="edge_metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class AttackPathResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    description: str | None
    severity: str
    node_path: list[str]
    edge_path: list[str]
    toxic_combo_tags: list[str]
    blast_radius: int
    entry_description: str | None
    target_description: str | None
    is_active: bool
    related_finding_ids: list[str]

    model_config = ConfigDict(from_attributes=True)


class SecurityGraphResponse(BaseModel):
    nodes: list[SecurityGraphNodeResponse]
    edges: list[SecurityGraphEdgeResponse]
    attack_paths: list[AttackPathResponse]
    stats: dict  # {"total_nodes": N, "attack_path_nodes": N, "internet_facing": N, "sensitive_data_nodes": N}

    model_config = ConfigDict(from_attributes=True)


class NodeFindingsResponse(BaseModel):
    node_id: uuid.UUID
    node_type: str
    resource_name: str | None
    findings: list  # list of CanonicalFindingResponse-compatible dicts

    model_config = ConfigDict(from_attributes=True)
