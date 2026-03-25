"""
Intelligence router — Finding Intelligence API (causal analysis + RAG scoring + Ollama narratives).

All endpoints are workspace-scoped and require authentication.
The intelligence engine is augmentation only — it never modifies severity,
risk_score, or compliance state on any finding.

Endpoints:
  POST /api/v1/intelligence/findings/{finding_id}         — trigger analysis
  GET  /api/v1/intelligence/findings/{finding_id}         — fetch existing result
  GET  /api/v1/intelligence/workspace/summary             — RAG counts + top RED findings
  POST /api/v1/intelligence/workspace/batch-analyze       — queue top N findings
  GET  /api/v1/intelligence/health                        — Ollama availability + model list
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.finding_intelligence import FindingIntelligence
from app.repositories.finding_intelligence_repository import FindingIntelligenceRepository
from app.schemas.intelligence import (
    BatchAnalyzeRequest,
    FindingIntelligenceResponse,
    IntelligenceHealthResponse,
    RAGCountSchema,
    WorkspaceIntelligenceSummary,
)
from app.services.finding_intelligence_service import FindingIntelligenceService
from app.services.ollama_service import OllamaService

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


# ── Dependency helpers ────────────────────────────────────────────────────────

def _get_ollama() -> OllamaService:
    return OllamaService()


def _svc(
    db: AsyncSession = Depends(get_db),
    ollama: OllamaService = Depends(_get_ollama),
) -> FindingIntelligenceService:
    return FindingIntelligenceService(db=db, ollama_svc=ollama)


def _intel_repo(db: AsyncSession = Depends(get_db)) -> FindingIntelligenceRepository:
    return FindingIntelligenceRepository(db)


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


def _model_to_response(obj: FindingIntelligence) -> FindingIntelligenceResponse:
    return FindingIntelligenceResponse.model_validate(obj)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/findings/{finding_id}",
    response_model=FindingIntelligenceResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger intelligence analysis for a finding",
)
async def trigger_finding_analysis(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: FindingIntelligenceService = Depends(_svc),
) -> FindingIntelligenceResponse:
    """
    Trigger or re-run the full intelligence pipeline for a single finding.

    Runs:
      1. Multi-factor causal analysis (CausalEngine)
      2. RAG priority scoring (RAGPriorityService)
      3. Ollama descriptive analysis + RCA narrative (or template fallback)

    Idempotent — safe to call multiple times; each call updates the stored result.
    """
    workspace_id = _workspace_id(current_user)
    result = await svc.analyze_finding(finding_id, workspace_id)
    # Reload from DB to return the persisted model
    intel_repo = FindingIntelligenceRepository(svc.db)
    stored = await intel_repo.get_by_finding_id(finding_id, workspace_id)
    if stored is None:
        # Fallback: construct response directly from result
        return FindingIntelligenceResponse(
            id=uuid.uuid4(),
            finding_id=result.finding_id,
            workspace_id=workspace_id,
            what_is_it=result.descriptive.what_is_it,
            current_state=result.descriptive.current_state,
            expected_state=result.descriptive.expected_state,
            business_impact=result.descriptive.business_impact,
            attack_scenario=result.descriptive.attack_scenario,
            composite_score=result.causal_analysis.composite_score,
            primary_root_cause=result.causal_analysis.primary_root_cause,
            causal_factors=[f.to_dict() for f in result.causal_analysis.factors],
            causal_chain=result.causal_analysis.causal_chain,
            toxic_combinations=[tc.to_dict() for tc in result.causal_analysis.toxic_combinations],
            blast_radius_count=result.causal_analysis.blast_radius.sensitive_node_count,
            confidence=result.causal_analysis.confidence,
            rag_level=result.rag_score.level,
            rag_composite_score=result.rag_score.composite_score,
            rag_primary_reason=result.rag_score.primary_reason,
            sla_days=result.rag_score.sla_days,
            escalation_required=result.rag_score.escalation_required,
            stakeholders=result.rag_score.stakeholders,
            immediate_actions=[a.to_dict() for a in result.rag_score.immediate_actions],
            sprint_actions=[a.to_dict() for a in result.rag_score.sprint_actions],
            quarterly_actions=[a.to_dict() for a in result.rag_score.quarterly_actions],
            ollama_model=result.ollama_model,
            fallback_used=result.fallback_used,
            generation_status="completed",
            created_at=result.generated_at,
            updated_at=result.generated_at,
        )
    return _model_to_response(stored)


@router.get(
    "/findings/{finding_id}",
    response_model=FindingIntelligenceResponse,
    summary="Get existing intelligence result for a finding",
)
async def get_finding_intelligence(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    repo: FindingIntelligenceRepository = Depends(_intel_repo),
) -> FindingIntelligenceResponse:
    """
    Retrieve the most recent persisted intelligence result for a finding.
    Returns 404 if analysis has not been run yet.
    """
    workspace_id = _workspace_id(current_user)
    intel = await repo.get_by_finding_id(finding_id, workspace_id)
    if intel is None:
        raise NotFoundError(
            f"No intelligence result found for finding {finding_id}. "
            "Run POST /intelligence/findings/{finding_id} first."
        )
    return _model_to_response(intel)


@router.get(
    "/workspace/summary",
    response_model=WorkspaceIntelligenceSummary,
    summary="RAG counts and top RED findings for the workspace",
)
async def get_workspace_summary(
    current_user: CurrentUserDep,
    repo: FindingIntelligenceRepository = Depends(_intel_repo),
) -> WorkspaceIntelligenceSummary:
    """
    Returns:
      - RAG level counts (RED / AMBER / GREEN)
      - Top 5 RED findings (ordered by rag_composite_score descending)
      - Total number of analyzed findings
    """
    workspace_id = _workspace_id(current_user)
    counts = await repo.count_by_rag(workspace_id)
    top_red = await repo.list_by_workspace(
        workspace_id=workspace_id,
        rag_level="RED",
        page=1,
        page_size=5,
    )
    total = await repo.count_by_workspace(workspace_id)

    return WorkspaceIntelligenceSummary(
        workspace_id=workspace_id,
        rag_counts=RAGCountSchema(
            RED=counts.get("RED", 0),
            AMBER=counts.get("AMBER", 0),
            GREEN=counts.get("GREEN", 0),
        ),
        top_red_findings=[_model_to_response(r) for r in top_red],
        total_analyzed=total,
    )


@router.post(
    "/workspace/batch-analyze",
    response_model=list[FindingIntelligenceResponse],
    status_code=status.HTTP_200_OK,
    summary="Batch analyze top N findings in the workspace",
)
async def batch_analyze(
    req: BatchAnalyzeRequest,
    current_user: CurrentUserDep,
    svc: FindingIntelligenceService = Depends(_svc),
) -> list[FindingIntelligenceResponse]:
    """
    Trigger intelligence analysis for the top N findings ordered by risk_score.

    Skips individual findings that fail analysis (errors are logged).
    Returns the persisted intelligence results for all successfully analyzed findings.

    Default: limit=10. Max: 100.
    """
    workspace_id = _workspace_id(current_user)
    results = await svc.batch_analyze(workspace_id, limit=req.limit)

    # Reload from DB to get the persisted records with IDs
    repo = FindingIntelligenceRepository(svc.db)
    responses: list[FindingIntelligenceResponse] = []
    for result in results:
        stored = await repo.get_by_finding_id(result.finding_id, workspace_id)
        if stored:
            responses.append(_model_to_response(stored))
    return responses


@router.get(
    "/health",
    response_model=IntelligenceHealthResponse,
    summary="Check Ollama availability and available models",
)
async def intelligence_health(
    current_user: CurrentUserDep,
    ollama: OllamaService = Depends(_get_ollama),
) -> IntelligenceHealthResponse:
    """
    Health check for the intelligence subsystem.

    Returns:
      - ollama_available: whether Ollama is reachable at the configured URL
      - models: list of models available in local Ollama installation
      - model_in_use: the model the service is configured to use
    """
    _workspace_id(current_user)  # ensure auth
    available = await ollama.is_available()
    models: list[str] = []
    if available:
        models = await ollama.list_models()

    return IntelligenceHealthResponse(
        ollama_available=available,
        ollama_url=ollama.base_url,
        models=models,
        model_in_use=ollama.model,
    )
