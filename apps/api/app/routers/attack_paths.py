"""
Attack Path Visualization router — Sprint 27.

Workspace-scoped endpoints for attack-path listing, detail, blast-radius
traversal, and summary statistics.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.services.attack_path_service import AttackPathService

router = APIRouter(prefix="/attack-paths", tags=["attack-paths"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


def _svc(db: AsyncSession = Depends(get_db)) -> AttackPathService:
    return AttackPathService(db)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/summary")
async def attack_path_summary(
    current_user: CurrentUserDep,
    svc: AttackPathService = Depends(_svc),
) -> dict:
    """Workspace-level attack-path statistics."""
    ws = _workspace_id(current_user)
    return await svc.summary(ws)


@router.get("")
async def list_attack_paths(
    current_user: CurrentUserDep,
    svc: AttackPathService = Depends(_svc),
) -> list[dict]:
    """List all active attack paths with resolved nodes and edges."""
    ws = _workspace_id(current_user)
    return await svc.get_attack_paths(ws)


@router.get("/blast-radius/{node_id}")
async def blast_radius(
    node_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AttackPathService = Depends(_svc),
) -> dict:
    """BFS blast-radius from a given node — all reachable nodes and edges."""
    ws = _workspace_id(current_user)
    return await svc.get_blast_radius(ws, node_id)


@router.get("/{path_id}")
async def get_attack_path(
    path_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: AttackPathService = Depends(_svc),
) -> dict:
    """Single attack path with fully resolved nodes and edges."""
    ws = _workspace_id(current_user)
    result = await svc.get_path_detail(ws, path_id)
    if result is None:
        raise NotFoundError(f"AttackPath {path_id} not found")
    return result
