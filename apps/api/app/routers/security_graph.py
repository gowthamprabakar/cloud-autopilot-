"""
Security Graph router — workspace-scoped graph API for CSPM posture visualization.

All endpoints require authentication and are scoped to the current user's workspace.
Admin-only endpoints (seed, clear) require the ADMIN or SUPER_ADMIN role.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep, require_roles
from app.core.exceptions import ForbiddenError, NotFoundError
from app.models.enums import UserRole
from app.repositories.security_graph_repository import SecurityGraphRepository
from app.schemas.security_graph import (
    AttackPathResponse,
    NodeFindingsResponse,
    SecurityGraphResponse,
)
from app.services.security_graph_service import SecurityGraphService

router = APIRouter(prefix="/security-graph", tags=["security-graph"])


def _svc(db: AsyncSession = Depends(get_db)) -> SecurityGraphService:
    return SecurityGraphService(repo=SecurityGraphRepository(db))


def _resolve_workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    return current_user.workspace_id


# ── Graph endpoints ────────────────────────────────────────────────────────────


@router.get("", response_model=SecurityGraphResponse)
async def get_graph(
    current_user: CurrentUserDep,
    svc: SecurityGraphService = Depends(_svc),
) -> SecurityGraphResponse:
    """
    Return the full security graph for the current workspace.
    Includes all nodes, edges, active attack paths, and summary stats.
    """
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.get_graph(workspace_id)


# ── Attack path endpoints ──────────────────────────────────────────────────────


@router.get("/attack-paths", response_model=list[AttackPathResponse])
async def list_attack_paths(
    current_user: CurrentUserDep,
    svc: SecurityGraphService = Depends(_svc),
    active_only: bool = Query(default=True, description="If true, return only active attack paths"),
) -> list[AttackPathResponse]:
    """
    List all attack paths for the current workspace.
    By default, only active paths are returned.
    """
    workspace_id = _resolve_workspace_id(current_user)
    paths = await svc._repo.get_attack_paths(workspace_id, active_only=active_only)
    return [AttackPathResponse.model_validate(p) for p in paths]


@router.get("/attack-paths/{path_id}", response_model=AttackPathResponse)
async def get_attack_path(
    path_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: SecurityGraphService = Depends(_svc),
) -> AttackPathResponse:
    """
    Get a single attack path by ID with full node details.
    """
    workspace_id = _resolve_workspace_id(current_user)
    path = await svc._repo.get_attack_path(path_id, workspace_id)
    if path is None:
        raise NotFoundError(f"AttackPath {path_id} not found")
    return AttackPathResponse.model_validate(path)


# ── Node endpoints ─────────────────────────────────────────────────────────────


@router.get("/nodes/{node_id}/findings", response_model=NodeFindingsResponse)
async def get_node_findings(
    node_id: uuid.UUID,
    current_user: CurrentUserDep,
    svc: SecurityGraphService = Depends(_svc),
) -> NodeFindingsResponse:
    """
    Return all canonical findings linked to a specific security graph node.
    """
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.get_node_findings(node_id, workspace_id)


# ── Admin endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/seed",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def seed_demo_graph(
    current_user: CurrentUserDep,
    aws_account_id: uuid.UUID = Query(
        ...,
        description="AWS account ID to associate demo nodes with",
    ),
    svc: SecurityGraphService = Depends(_svc),
) -> dict:
    """
    Seed a realistic 18-node, 20-edge demo security graph for the current workspace.
    This endpoint is idempotent — calling it again clears and re-seeds the graph.
    Requires ADMIN or SUPER_ADMIN role.
    """
    workspace_id = _resolve_workspace_id(current_user)
    return await svc.seed_demo_graph(workspace_id, aws_account_id)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_roles(UserRole.ADMIN, UserRole.SUPER_ADMIN)],
)
async def clear_graph(
    current_user: CurrentUserDep,
    svc: SecurityGraphService = Depends(_svc),
) -> None:
    """
    Delete all nodes, edges, and attack paths for the current workspace.
    Requires ADMIN or SUPER_ADMIN role.
    """
    workspace_id = _resolve_workspace_id(current_user)
    await svc._repo.clear_workspace_graph(workspace_id)
