"""
AI schemas — request/response models for the AI Safe Layer.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Insight ──────────────────────────────────────────────────────────────────

class AiInsightResponse(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    finding_id: uuid.UUID
    prompt_template_id: str
    input_context_hash: str
    model_id: str
    generation_status: str
    summary: str | None
    suggested_actions: list[str]
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GenerateInsightRequest(BaseModel):
    """Trigger AI generation for a finding."""
    prompt_template_id: str = Field(
        default="finding_summary_v1",
        description="Must be a whitelisted key in PROMPT_REGISTRY",
    )


# ── Feedback ─────────────────────────────────────────────────────────────────

FeedbackVerdict = Literal["accepted", "edited", "rejected"]


class AiFeedbackRequest(BaseModel):
    verdict: FeedbackVerdict
    edited_text: str | None = None


class AiFeedbackResponse(BaseModel):
    id: uuid.UUID
    insight_id: uuid.UUID
    user_id: uuid.UUID | None
    verdict: str
    edited_text: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Prompt templates (read-only list) ────────────────────────────────────────

class PromptTemplateResponse(BaseModel):
    id: str
    description: str
