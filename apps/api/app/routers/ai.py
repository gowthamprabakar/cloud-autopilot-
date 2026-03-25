"""
AI router — Cloud Posture Copilot AI Safe Layer endpoints.

All endpoints are workspace-scoped and require authentication.
AI is AUGMENTATION ONLY — no endpoint here modifies severity, risk_score,
or compliance state on any finding.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.repositories.ai_feedback_repository import AiFeedbackRepository
from app.repositories.ai_insight_repository import AiInsightRepository
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.schemas.ai import (
    AiFeedbackRequest,
    AiFeedbackResponse,
    AiInsightResponse,
    GenerateInsightRequest,
    PromptTemplateResponse,
)
from app.services.ai_service import AiService

router = APIRouter(prefix="/ai", tags=["ai"])


def _svc(db: AsyncSession = Depends(get_db)) -> AiService:
    return AiService(
        insight_repo=AiInsightRepository(db),
        feedback_repo=AiFeedbackRepository(db),
        finding_repo=CanonicalFindingRepository(db),
    )


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


# ── Prompt templates ──────────────────────────────────────────────────────────

@router.get("/prompt-templates", response_model=list[PromptTemplateResponse])
async def list_prompt_templates(
    current_user: CurrentUserDep,
    svc: AiService = Depends(_svc),
) -> list[PromptTemplateResponse]:
    """List whitelisted AI prompt templates."""
    templates = svc.list_prompt_templates()
    return [PromptTemplateResponse(**t) for t in templates]


# ── Finding insights ──────────────────────────────────────────────────────────

@router.post(
    "/findings/{finding_id}/insights",
    response_model=AiInsightResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_insight(
    finding_id: uuid.UUID,
    req: GenerateInsightRequest,
    current_user: CurrentUserDep,
    svc: AiService = Depends(_svc),
) -> AiInsightResponse:
    """
    Generate (or return cached) an AI insight for a finding.
    Idempotent: same finding + same prompt + same context → same response.
    """
    workspace_id = _workspace_id(current_user)
    insight = await svc.generate_insight(
        finding_id=finding_id,
        workspace_id=workspace_id,
        prompt_template_id=req.prompt_template_id,
    )
    return AiInsightResponse.model_validate(insight)


@router.get("/findings/{finding_id}/insights/latest", response_model=AiInsightResponse | None)
async def get_latest_insight(
    finding_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AiService = Depends(_svc),
) -> AiInsightResponse | None:
    """Get the most recent completed AI insight for a finding."""
    workspace_id = _workspace_id(current_user)
    insight = await svc.get_insight_for_finding(
        finding_id=finding_id,
        workspace_id=workspace_id,
    )
    if insight is None:
        return None
    return AiInsightResponse.model_validate(insight)


# ── Feedback ──────────────────────────────────────────────────────────────────

@router.post(
    "/insights/{insight_id}/feedback",
    response_model=AiFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    insight_id: uuid.UUID,
    req: AiFeedbackRequest,
    current_user: CurrentUserDep,
    svc: AiService = Depends(_svc),
) -> AiFeedbackResponse:
    """Submit human feedback (accepted / edited / rejected) on an AI insight."""
    workspace_id = _workspace_id(current_user)
    feedback = await svc.submit_feedback(
        insight_id=insight_id,
        workspace_id=workspace_id,
        user_id=current_user.id,
        req=req,
    )
    return AiFeedbackResponse.model_validate(feedback)
