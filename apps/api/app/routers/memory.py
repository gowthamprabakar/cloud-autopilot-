"""
Agent Memory router (Sprint 31).

GET    /api/v1/memory/{agent_id}            Get agent memory summary
GET    /api/v1/memory/{agent_id}/recall     Recall memories with filters
POST   /api/v1/memory/{agent_id}/store      Store a memory entry
POST   /api/v1/memory/learn/{run_id}        Learn from completed simulation
POST   /api/v1/memory/decay                 Trigger relevance decay
DELETE /api/v1/memory/{agent_id}/working     Clear working memory
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import BadRequestError, ForbiddenError
from app.services.memory_service import VALID_MEMORY_TYPES, MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


# ── Request Schemas ──────────────────────────────────────────────────────────


class StoreMemoryRequest(BaseModel):
    memory_type: str = Field(
        ...,
        description="Memory type: working | episodic | semantic | procedural",
        examples=["semantic"],
    )
    key: str = Field(..., description="Memory key", examples=["cspm_best_practice_01"])
    value: Any = Field(..., description="Memory value (any JSON-serializable)")
    relevance: float = Field(default=1.0, ge=0.0, le=1.0, description="Initial relevance score")
    ttl_hours: float | None = Field(default=None, description="Time-to-live in hours (optional)")
    run_id: uuid.UUID | None = Field(default=None, description="Associated simulation run ID")
    metadata: dict | None = Field(default=None, description="Additional context metadata")


class DecayRequest(BaseModel):
    half_life_days: float = Field(
        default=7.0,
        gt=0,
        description="Half-life for relevance decay in days",
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/{agent_id}",
    summary="Get agent memory summary",
    description="Returns memory stats: count by type, average relevance, oldest/newest.",
)
async def get_memory_summary(
    agent_id: str,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = MemoryService(db)
    return await svc.get_agent_memory_summary(workspace_id, agent_id)


@router.get(
    "/{agent_id}/recall",
    summary="Recall agent memories",
    description=(
        "Recall memories for an agent with optional type and relevance filters. "
        "Updates access count and last_accessed_at for returned memories."
    ),
)
async def recall_memories(
    agent_id: str,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    memory_type: str | None = Query(default=None, alias="type", description="Filter by memory type"),
    key: str | None = Query(default=None, description="Filter by exact key"),
    min_relevance: float = Query(default=0.1, ge=0.0, le=1.0, description="Minimum relevance"),
    limit: int = Query(default=50, ge=1, le=200, description="Max memories to return"),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)

    if memory_type and memory_type not in VALID_MEMORY_TYPES:
        raise BadRequestError(
            f"Invalid memory type '{memory_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_MEMORY_TYPES))}"
        )

    svc = MemoryService(db)
    memories = await svc.recall(
        workspace_id=workspace_id,
        agent_id=agent_id,
        memory_type=memory_type,
        key=key,
        min_relevance=min_relevance,
        limit=limit,
    )
    await db.commit()
    return memories


@router.post(
    "/{agent_id}/store",
    summary="Store a memory",
    description="Store or upsert a memory entry for the given agent.",
    status_code=201,
)
async def store_memory(
    agent_id: str,
    body: StoreMemoryRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)

    if body.memory_type not in VALID_MEMORY_TYPES:
        raise BadRequestError(
            f"Invalid memory type '{body.memory_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_MEMORY_TYPES))}"
        )

    svc = MemoryService(db)
    mem = await svc.store(
        workspace_id=workspace_id,
        agent_id=agent_id,
        memory_type=body.memory_type,
        key=body.key,
        value=body.value,
        relevance=body.relevance,
        ttl_hours=body.ttl_hours,
        run_id=body.run_id,
        metadata=body.metadata,
    )
    await db.commit()
    await db.refresh(mem)

    return {
        "id": str(mem.id),
        "agent_id": mem.agent_id,
        "memory_type": mem.memory_type,
        "key": mem.key,
        "relevance_score": mem.relevance_score,
        "created_at": mem.created_at.isoformat() if mem.created_at else None,
    }


@router.post(
    "/learn/{run_id}",
    summary="Learn from completed simulation",
    description=(
        "Extract semantic memories from a completed simulation's agent outputs. "
        "Scans agent outputs for key patterns and stores as semantic memories."
    ),
)
async def learn_from_simulation(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = MemoryService(db)
    count = await svc.learn_from_simulation(workspace_id, run_id)
    await db.commit()
    return {"run_id": str(run_id), "memories_created": count}


@router.post(
    "/decay",
    summary="Trigger relevance decay",
    description=(
        "Apply exponential relevance decay to all non-procedural memories. "
        "Memories older than half_life_days have their relevance halved."
    ),
)
async def trigger_decay(
    body: DecayRequest,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = MemoryService(db)
    decayed = await svc.decay_relevance(workspace_id, half_life_days=body.half_life_days)
    evicted = await svc.evict_expired(workspace_id)
    await db.commit()
    return {
        "decayed": decayed,
        "evicted": evicted,
        "half_life_days": body.half_life_days,
    }


@router.delete(
    "/{agent_id}/working",
    summary="Clear working memory",
    description="Clear all working memory for an agent, optionally scoped to a simulation run.",
)
async def clear_working_memory(
    agent_id: str,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    run_id: uuid.UUID | None = Query(default=None, description="Scope to a specific simulation run"),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = MemoryService(db)
    cleared = await svc.clear_working_memory(workspace_id, agent_id, run_id=run_id)
    await db.commit()
    return {"agent_id": agent_id, "cleared": cleared}
