"""
Prompt Registry router — Sprint 26 AI Prompt Registry.

CRUD + seed endpoints for versioned AI prompt templates
with workspace-level overrides.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.services.prompt_registry_service import PromptRegistryService

router = APIRouter(prefix="/prompts", tags=["prompt-registry"])


# ── Helpers ───────────────────────────────────────────────────


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


def _svc(db: AsyncSession = Depends(get_db)) -> PromptRegistryService:
    return PromptRegistryService(db)


# ── Schemas ───────────────────────────────────────────────────


class PromptCreateRequest(BaseModel):
    name: str
    template: str
    model_id: str = "bedrock/claude-3-sonnet"
    category: str = "general"
    version: int = 1
    is_active: bool = True
    workspace_id: uuid.UUID | None = None


class PromptUpdateRequest(BaseModel):
    template: str | None = None
    model_id: str | None = None
    category: str | None = None
    is_active: bool | None = None


class PromptResponse(BaseModel):
    id: str
    workspace_id: str | None = None
    name: str
    version: int
    template: str
    model_id: str
    category: str
    is_active: bool
    created_at: str | None = None
    updated_at: str | None = None


# ── Endpoints ─────────────────────────────────────────────────


@router.get("", response_model=list[PromptResponse])
async def list_prompts(
    current_user: CurrentUserDep,
    svc: PromptRegistryService = Depends(_svc),
) -> list[dict]:
    """List all active prompts (global + workspace-specific)."""
    ws_id = _workspace_id(current_user)
    return await svc.list_prompts(workspace_id=ws_id)


@router.get("/{name}", response_model=PromptResponse | None)
async def get_prompt(
    name: str,
    current_user: CurrentUserDep,
    svc: PromptRegistryService = Depends(_svc),
) -> dict | None:
    """Get prompt by name (workspace-specific takes priority over global)."""
    ws_id = _workspace_id(current_user)
    prompt = await svc.get_prompt(name=name, workspace_id=ws_id)
    if prompt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return prompt


@router.post("", response_model=PromptResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    req: PromptCreateRequest,
    current_user: CurrentUserDep,
    svc: PromptRegistryService = Depends(_svc),
) -> dict:
    """Create a new prompt template."""
    ws_id = _workspace_id(current_user)
    data = req.model_dump()
    # Scope to user's workspace unless explicitly global (None)
    if data.get("workspace_id") is None:
        data["workspace_id"] = ws_id
    return await svc.create_prompt(data)


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: uuid.UUID,
    req: PromptUpdateRequest,
    current_user: CurrentUserDep,
    svc: PromptRegistryService = Depends(_svc),
) -> dict:
    """Update an existing prompt (bumps version if template changes)."""
    _workspace_id(current_user)  # auth gate
    data = req.model_dump(exclude_unset=True)
    result = await svc.update_prompt(prompt_id, data)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
    return result


@router.post("/seed", status_code=status.HTTP_200_OK)
async def seed_defaults(
    current_user: CurrentUserDep,
    svc: PromptRegistryService = Depends(_svc),
) -> dict[str, Any]:
    """Seed default prompt templates for the workspace (no-op if prompts exist)."""
    ws_id = _workspace_id(current_user)
    count = await svc.seed_defaults(workspace_id=ws_id)
    return {"seeded": count}
