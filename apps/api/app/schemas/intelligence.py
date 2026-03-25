"""
Pydantic schemas for the Finding Intelligence API.

All schemas are read-only response models — the intelligence layer is always
written by backend services, never directly by the API consumer.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _parse_json_field(v: Any) -> Any:
    """Coerce a JSON string to a Python object (list/dict). Pass through if already parsed."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return v
    return v


# ── Low-level building blocks ─────────────────────────────────────────────────

class CausalFactorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    score: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    contributing_nodes: list[str]
    weight: float = Field(ge=0.0, le=1.0)


class ToxicComboSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str
    factors_involved: list[str]
    score_boost: float


class AttackVectorSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str
    likelihood: str  # "LOW" | "MEDIUM" | "HIGH"
    steps: list[str]


class BlastRadiusSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    reachable_nodes: list[str]
    sensitive_node_count: int
    score: float = Field(ge=0.0, le=1.0)


class PrioritizedActionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    effort: str  # "LOW" | "MEDIUM" | "HIGH"
    impact: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    cli_command: str | None = None
    console_url: str | None = None
    rag_color: str  # "RED" | "AMBER" | "GREEN"


# ── RAG Score ─────────────────────────────────────────────────────────────────

class RAGScoreSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    level: str  # "RED" | "AMBER" | "GREEN"
    composite_score: float
    primary_reason: str
    immediate_actions: list[PrioritizedActionSchema]
    sprint_actions: list[PrioritizedActionSchema]
    quarterly_actions: list[PrioritizedActionSchema]
    sla_days: int
    escalation_required: bool
    stakeholders: list[str]


# ── Causal Analysis ───────────────────────────────────────────────────────────

class CausalAnalysisSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: uuid.UUID
    composite_score: float
    factors: list[CausalFactorSchema]
    primary_root_cause: str
    secondary_causes: list[str]
    causal_chain: list[str]
    toxic_combinations: list[ToxicComboSchema]
    blast_radius: BlastRadiusSchema
    attack_vectors: list[AttackVectorSchema]
    confidence: float


# ── Full intelligence response ────────────────────────────────────────────────

class FindingIntelligenceResponse(BaseModel):
    """
    Complete intelligence result returned from GET/POST
    /api/v1/intelligence/findings/{finding_id}.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    finding_id: uuid.UUID
    workspace_id: uuid.UUID

    # Descriptive layer
    what_is_it: str | None = None
    current_state: str | None = None
    expected_state: str | None = None
    business_impact: str | None = None
    attack_scenario: str | None = None

    # Causal layer (flattened for easy consumption)
    composite_score: float | None = None
    primary_root_cause: str | None = None
    causal_factors: list[Any] = Field(default_factory=list)
    causal_chain: list[Any] = Field(default_factory=list)
    toxic_combinations: list[Any] = Field(default_factory=list)
    blast_radius_count: int | None = None
    confidence: float | None = None

    # RAG layer
    rag_level: str | None = None
    rag_composite_score: float | None = None
    rag_primary_reason: str | None = None
    sla_days: int | None = None
    escalation_required: bool = False
    stakeholders: list[str] = Field(default_factory=list)

    # Actions
    immediate_actions: list[Any] = Field(default_factory=list)
    sprint_actions: list[Any] = Field(default_factory=list)
    quarterly_actions: list[Any] = Field(default_factory=list)

    # Metadata
    ollama_model: str | None = None
    fallback_used: bool = False
    generation_status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    # ── JSON-string coercions (SQLite stores JSON as TEXT) ──────────────────
    @field_validator(
        "causal_factors", "causal_chain", "toxic_combinations",
        "stakeholders", "immediate_actions", "sprint_actions", "quarterly_actions",
        mode="before",
    )
    @classmethod
    def _parse_json(cls, v: Any) -> Any:
        return _parse_json_field(v)


# ── Workspace summary ─────────────────────────────────────────────────────────

class RAGCountSchema(BaseModel):
    RED: int = 0
    AMBER: int = 0
    GREEN: int = 0


class WorkspaceIntelligenceSummary(BaseModel):
    """Returned from GET /api/v1/intelligence/workspace/summary."""

    workspace_id: uuid.UUID
    rag_counts: RAGCountSchema
    top_red_findings: list[FindingIntelligenceResponse]
    total_analyzed: int


# ── Health ────────────────────────────────────────────────────────────────────

class IntelligenceHealthResponse(BaseModel):
    """Returned from GET /api/v1/intelligence/health."""

    ollama_available: bool
    ollama_url: str
    models: list[str]
    model_in_use: str


# ── Request schemas ───────────────────────────────────────────────────────────

class BatchAnalyzeRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)
