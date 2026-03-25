"""
Domains & Agents router — list threat domains and agent types.

GET  /api/v1/domains       — List all 17 threat domains
GET  /api/v1/agents        — List all 15 agent types with metadata
POST /api/v1/agents/spawn  — Spawn specialist agent into running simulation
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import BadRequestError, NotFoundError
from app.services.simulation_service import THREAT_DOMAINS
from app.services.spawn_service import SpawnService

router = APIRouter(tags=["domains"])

# ── Categorise domains ──────────────────────────────────────────────────────

WIZ_CNAPP_KEYS = {
    "cspm", "cwpp", "ciem", "dspm", "kspm",
    "cdr", "iac", "uvm", "ai_spm", "asm",
}


# ── Request / Response schemas ──────────────────────────────────────────────

class SpawnRequest(BaseModel):
    run_id: uuid.UUID = Field(..., description="ID of the running simulation")
    agent_type: str = Field("DEEP-XX", description="Agent roster key to spawn")
    custom_prompt: str | None = Field(None, description="Optional custom system prompt")


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/domains", summary="List all 17 threat domains")
async def list_domains() -> list[dict[str, Any]]:
    """Return every threat domain with key, name, and category."""
    return [
        {
            "key": key,
            "name": name,
            "category": "wiz_cnapp" if key in WIZ_CNAPP_KEYS else "gap_domain",
        }
        for key, name in THREAT_DOMAINS.items()
    ]


@router.get("/agents", summary="List all 15 agent types")
async def list_agents() -> list[dict[str, Any]]:
    """Return the full agent roster with metadata."""
    svc = SpawnService.__new__(SpawnService)  # no db needed for static list
    return svc.list_agent_types()


@router.post("/agents/spawn", summary="Spawn specialist agent")
async def spawn_agent(
    body: SpawnRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Spawn a specialist agent into an active simulation run."""
    svc = SpawnService(db)
    try:
        agent = await svc.spawn_agent(
            run_id=body.run_id,
            agent_type=body.agent_type,
            custom_prompt=body.custom_prompt,
        )
    except Exception as exc:
        raise BadRequestError(str(exc)) from exc

    await db.commit()

    return {
        "id": str(agent.id),
        "agent_id": agent.agent_id,
        "name": agent.name,
        "role": agent.role,
        "status": agent.status,
        "simulation_run_id": str(agent.simulation_run_id),
    }
