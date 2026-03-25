"""
Agent schemas — request/response models for THINK layer agent endpoints.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


# ── Typed output models ───────────────────────────────────────────────────────

class TriageOutput(BaseModel):
    """Structured output for the 'triage' agent."""
    suggested_severity: str
    confidence: float
    rationale: str
    mitre_tactics: list[str] = []
    fallback_used: bool = False
    original_severity: str = ""


class AttackPathOutput(BaseModel):
    """Structured output for the 'attack_path' agent."""
    blast_radius_count: int
    choke_points: list[str] = []
    path_summary: str
    attack_chain: list[str] = []


# ── Generic response (raw output dict) ───────────────────────────────────────

class AgentResultResponse(BaseModel):
    """Generic response — output is a raw dict; use typed variants when possible."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    agent_name: str
    status: str
    model_used: str
    output: dict[str, Any]
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Typed response variants ───────────────────────────────────────────────────

class TriageResultResponse(BaseModel):
    """Typed triage result with validated TriageOutput."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    agent_name: str
    status: str
    model_used: str
    output: TriageOutput
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_result(cls, result: Any) -> "TriageResultResponse":
        return cls(
            id=result.id,
            workspace_id=result.workspace_id,
            finding_id=result.finding_id,
            agent_name=result.agent_name,
            status=result.status,
            model_used=result.model_used,
            output=TriageOutput(**(result.output or {})),
            error_message=result.error_message,
            latency_ms=result.latency_ms,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )


class AttackPathResultResponse(BaseModel):
    """Typed attack path result with validated AttackPathOutput."""
    id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    agent_name: str
    status: str
    model_used: str
    output: AttackPathOutput
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_result(cls, result: Any) -> "AttackPathResultResponse":
        return cls(
            id=result.id,
            workspace_id=result.workspace_id,
            finding_id=result.finding_id,
            agent_name=result.agent_name,
            status=result.status,
            model_used=result.model_used,
            output=AttackPathOutput(**(result.output or {})),
            error_message=result.error_message,
            latency_ms=result.latency_ms,
            created_at=result.created_at,
            updated_at=result.updated_at,
        )


# ── Sprint 19 output models ───────────────────────────────────────────────────

class RootCauseOutput(BaseModel):
    """Structured output for the 'root_cause' agent."""
    root_cause: str
    contributing_factors: list[str] = []
    misconfiguration_type: str = ""
    affected_blast_radius: int = 0
    remediation_priority: Literal["immediate", "high", "medium", "low"] = "medium"
    fallback_used: bool = False


class RemediationStep(BaseModel):
    step: int
    action: str
    command: str
    iac_type: Literal["terraform", "cli", "console"] = "console"


class RemediationPlanOutput(BaseModel):
    """Structured output for the 'remediation_plan' agent."""
    steps: list[RemediationStep] = []
    estimated_effort: Literal["minutes", "hours", "days"] = "hours"
    auto_remediatable: bool = False
    fallback_used: bool = False


class NotificationOutput(BaseModel):
    """Structured output for the 'notification' agent."""
    notification_sent: bool
    channel: Literal["in_app"] = "in_app"
    severity: str
    message: str


# ── Sprint 19 response classes ────────────────────────────────────────────────

class RootCauseResultResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    agent_name: str
    status: str
    model_used: str
    output: RootCauseOutput
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_result(cls, result: Any) -> "RootCauseResultResponse":
        return cls(
            id=result.id, workspace_id=result.workspace_id, finding_id=result.finding_id,
            agent_name=result.agent_name, status=result.status, model_used=result.model_used,
            output=RootCauseOutput(**(result.output or {})),
            error_message=result.error_message, latency_ms=result.latency_ms,
            created_at=result.created_at, updated_at=result.updated_at,
        )


class RemediationPlanResultResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    agent_name: str
    status: str
    model_used: str
    output: RemediationPlanOutput
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_result(cls, result: Any) -> "RemediationPlanResultResponse":
        return cls(
            id=result.id, workspace_id=result.workspace_id, finding_id=result.finding_id,
            agent_name=result.agent_name, status=result.status, model_used=result.model_used,
            output=RemediationPlanOutput(**(result.output or {})),
            error_message=result.error_message, latency_ms=result.latency_ms,
            created_at=result.created_at, updated_at=result.updated_at,
        )


class NotificationResultResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    agent_name: str
    status: str
    model_used: str
    output: NotificationOutput
    error_message: str | None = None
    latency_ms: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_result(cls, result: Any) -> "NotificationResultResponse":
        return cls(
            id=result.id, workspace_id=result.workspace_id, finding_id=result.finding_id,
            agent_name=result.agent_name, status=result.status, model_used=result.model_used,
            output=NotificationOutput(**(result.output or {})),
            error_message=result.error_message, latency_ms=result.latency_ms,
            created_at=result.created_at, updated_at=result.updated_at,
        )


# ── Audit log response ────────────────────────────────────────────────────────

class AgentAuditLogResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID | None = None
    agent_name: str
    triggered_by: str
    input_hash: str
    output_summary: str | None = None
    model_used: str
    latency_ms: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
