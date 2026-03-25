"""
Agent router — REST endpoints for the THINK layer agents.

Endpoints:
  POST /findings/{finding_id}/triage            Trigger TriageAgent
  GET  /findings/{finding_id}/triage            Fetch latest triage result
  POST /findings/{finding_id}/attack-path       Trigger AttackPathAnalyzerAgent
  GET  /findings/{finding_id}/attack-path       Fetch latest attack path result
  GET  /findings/{finding_id}/agent-audit-logs  List all audit logs for a finding

All endpoints require authentication. Workspace-scoped via current_user.workspace_id.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.agent_audit_log import AgentAuditLog
from app.models.agent_result import AgentResult
from app.schemas.agent import (
    AgentAuditLogResponse,
    AttackPathResultResponse,
    NotificationResultResponse,
    RemediationPlanResultResponse,
    RootCauseResultResponse,
    TriageResultResponse,
)
from app.services.agents.attack_path_agent import AttackPathAnalyzerAgent
from app.services.agents.notification_agent import NotificationAgent
from app.services.agents.remediation_agent import RemediationPlannerAgent
from app.services.agents.root_cause_agent import RootCauseAnalyzerAgent
from app.services.agents.triage_agent import TriageAgent

router = APIRouter(prefix="/findings", tags=["agents"])


def _workspace_id(current_user) -> uuid.UUID:
    """Extract and validate workspace_id from current user."""
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


# ── Triage ─────────────────────────────────────────────────────────────────

@router.post(
    "/{finding_id}/triage",
    response_model=TriageResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger AI triage for a finding",
    description=(
        "Routes to Ollama llama3 (fast) or Claude Haiku (complex findings) based on "
        "description length and risk score. Stores result and writes audit log. "
        "Returns the completed triage result."
    ),
)
async def trigger_triage(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> TriageResultResponse:
    workspace_id = _workspace_id(current_user)
    agent = TriageAgent(db)
    result = await agent.execute(
        finding_id=finding_id,
        workspace_id=workspace_id,
        triggered_by="api_user",
    )
    if result.status == "failed":
        raise NotFoundError(f"Triage failed: {result.error_message}")
    return TriageResultResponse.from_orm_result(result)


@router.get(
    "/{finding_id}/triage",
    response_model=TriageResultResponse,
    summary="Get latest triage result for a finding",
    description="Returns the most recent completed triage result for this finding.",
)
async def get_triage(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> TriageResultResponse:
    workspace_id = _workspace_id(current_user)
    result = await db.execute(
        select(AgentResult)
        .where(
            AgentResult.finding_id == finding_id,
            AgentResult.workspace_id == workspace_id,
            AgentResult.agent_name == "triage",
            AgentResult.status == "completed",
        )
        .order_by(AgentResult.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(
            f"No triage result found for finding {finding_id}. "
            "POST to /triage to run analysis first."
        )
    return TriageResultResponse.from_orm_result(row)


# ── Attack Path ────────────────────────────────────────────────────────────

@router.post(
    "/{finding_id}/attack-path",
    response_model=AttackPathResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger attack path analysis for a finding",
    description=(
        "BFS traversal up to 3 hops from nodes linked to this finding. "
        "Identifies blast radius and choke points. Generates NL summary via Ollama llama3."
    ),
)
async def trigger_attack_path(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> AttackPathResultResponse:
    workspace_id = _workspace_id(current_user)
    agent = AttackPathAnalyzerAgent(db)
    result = await agent.execute(
        finding_id=finding_id,
        workspace_id=workspace_id,
        triggered_by="api_user",
    )
    if result.status == "failed":
        raise NotFoundError(f"Attack path analysis failed: {result.error_message}")
    return AttackPathResultResponse.from_orm_result(result)


@router.get(
    "/{finding_id}/attack-path",
    response_model=AttackPathResultResponse,
    summary="Get latest attack path result for a finding",
    description="Returns the most recent completed attack path analysis for this finding.",
)
async def get_attack_path(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> AttackPathResultResponse:
    workspace_id = _workspace_id(current_user)
    result = await db.execute(
        select(AgentResult)
        .where(
            AgentResult.finding_id == finding_id,
            AgentResult.workspace_id == workspace_id,
            AgentResult.agent_name == "attack_path",
            AgentResult.status == "completed",
        )
        .order_by(AgentResult.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(
            f"No attack path result found for finding {finding_id}. "
            "POST to /attack-path to run analysis first."
        )
    return AttackPathResultResponse.from_orm_result(row)


# ── Root Cause ─────────────────────────────────────────────────────────────

@router.post(
    "/{finding_id}/root-cause",
    response_model=RootCauseResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger root cause analysis for a finding",
    description="Auto-chains TriageAgent if no triage result exists. Uses Ollama llama3.",
)
async def trigger_root_cause(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> RootCauseResultResponse:
    workspace_id = _workspace_id(current_user)
    result = await RootCauseAnalyzerAgent(db).execute(
        finding_id=finding_id, workspace_id=workspace_id, triggered_by="api_user"
    )
    if result.status == "failed":
        raise NotFoundError(f"Root cause analysis failed: {result.error_message}")
    return RootCauseResultResponse.from_orm_result(result)


@router.get(
    "/{finding_id}/root-cause",
    response_model=RootCauseResultResponse,
    summary="Get latest root cause analysis for a finding",
)
async def get_root_cause(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> RootCauseResultResponse:
    workspace_id = _workspace_id(current_user)
    result = await db.execute(
        select(AgentResult)
        .where(
            AgentResult.finding_id == finding_id,
            AgentResult.workspace_id == workspace_id,
            AgentResult.agent_name == "root_cause",
            AgentResult.status == "completed",
        )
        .order_by(AgentResult.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"No root cause result for finding {finding_id}. POST first.")
    return RootCauseResultResponse.from_orm_result(row)


# ── Remediation Plan ────────────────────────────────────────────────────────

@router.post(
    "/{finding_id}/remediation-plan",
    response_model=RemediationPlanResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate IaC remediation plan for a finding",
    description="Uses Claude Haiku (code generation) with Ollama fallback. Sorts steps: Terraform > CLI > Console.",
)
async def trigger_remediation_plan(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> RemediationPlanResultResponse:
    workspace_id = _workspace_id(current_user)
    result = await RemediationPlannerAgent(db).execute(
        finding_id=finding_id, workspace_id=workspace_id, triggered_by="api_user"
    )
    if result.status == "failed":
        raise NotFoundError(f"Remediation planning failed: {result.error_message}")
    return RemediationPlanResultResponse.from_orm_result(result)


@router.get(
    "/{finding_id}/remediation-plan",
    response_model=RemediationPlanResultResponse,
    summary="Get latest remediation plan for a finding",
)
async def get_remediation_plan(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> RemediationPlanResultResponse:
    workspace_id = _workspace_id(current_user)
    result = await db.execute(
        select(AgentResult)
        .where(
            AgentResult.finding_id == finding_id,
            AgentResult.workspace_id == workspace_id,
            AgentResult.agent_name == "remediation_plan",
            AgentResult.status == "completed",
        )
        .order_by(AgentResult.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"No remediation plan for finding {finding_id}. POST first.")
    return RemediationPlanResultResponse.from_orm_result(row)


# ── Notification (ACT layer) ────────────────────────────────────────────────

@router.post(
    "/{finding_id}/notify",
    response_model=NotificationResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger notification agent for a finding",
    description="Sends in-app notification if triage severity is critical. Idempotent.",
)
async def trigger_notification(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> NotificationResultResponse:
    workspace_id = _workspace_id(current_user)
    result = await NotificationAgent(db).execute(
        finding_id=finding_id, workspace_id=workspace_id, triggered_by="api_user"
    )
    return NotificationResultResponse.from_orm_result(result)


@router.get(
    "/{finding_id}/notify",
    response_model=NotificationResultResponse,
    summary="Get latest notification result for a finding",
)
async def get_notification_result(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> NotificationResultResponse:
    workspace_id = _workspace_id(current_user)
    result = await db.execute(
        select(AgentResult)
        .where(
            AgentResult.finding_id == finding_id,
            AgentResult.workspace_id == workspace_id,
            AgentResult.agent_name == "notification",
            AgentResult.status == "completed",
        )
        .order_by(AgentResult.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError(f"No notification result for finding {finding_id}. POST first.")
    return NotificationResultResponse.from_orm_result(row)


# ── Audit Logs ─────────────────────────────────────────────────────────────

@router.get(
    "/{finding_id}/agent-audit-logs",
    response_model=list[AgentAuditLogResponse],
    summary="List all agent audit logs for a finding",
    description=(
        "Returns all audit log entries for every agent invocation on this finding, "
        "ordered newest first. Provides full traceability of AI decisions."
    ),
)
async def list_agent_audit_logs(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[AgentAuditLogResponse]:
    workspace_id = _workspace_id(current_user)
    result = await db.execute(
        select(AgentAuditLog)
        .where(
            AgentAuditLog.finding_id == finding_id,
            AgentAuditLog.workspace_id == workspace_id,
        )
        .order_by(AgentAuditLog.created_at.desc())
    )
    rows = list(result.scalars().all())
    return [AgentAuditLogResponse.model_validate(r) for r in rows]
