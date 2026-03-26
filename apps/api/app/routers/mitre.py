"""
MITRE ATT&CK mapping router (Sprint 33).

GET  /api/v1/mitre/techniques              List all ATT&CK techniques
GET  /api/v1/mitre/tactics                  List all ATT&CK tactics
GET  /api/v1/mitre/coverage                 Technique coverage analysis
GET  /api/v1/mitre/heatmap                  Tactic heatmap
GET  /api/v1/mitre/simulation/{run_id}      Techniques from a simulation run
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.services.mitre_service import MITREService

router = APIRouter(prefix="/mitre", tags=["mitre"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/techniques",
    summary="List all ATT&CK techniques",
    description="Return the full catalogue of MITRE ATT&CK Cloud (IaaS) techniques tracked by OmniSec.",
)
async def list_techniques(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    svc = MITREService(db)
    return svc.list_techniques()


@router.get(
    "/tactics",
    summary="List all ATT&CK tactics",
    description="Return the ordered list of MITRE ATT&CK Cloud tactics.",
)
async def list_tactics(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[str]:
    svc = MITREService(db)
    return svc.list_tactics()


@router.get(
    "/coverage",
    summary="Technique coverage analysis",
    description=(
        "Analyze which ATT&CK techniques are covered by existing detection "
        "findings in the current workspace."
    ),
)
async def get_coverage(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = MITREService(db)
    return await svc.get_technique_coverage(workspace_id)


@router.get(
    "/heatmap",
    summary="Tactic heatmap",
    description="Generate a tactic-level coverage heatmap for ATT&CK visualization.",
)
async def get_heatmap(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = MITREService(db)
    return await svc.get_tactic_heatmap(workspace_id)


@router.get(
    "/simulation/{run_id}",
    summary="Techniques from a simulation run",
    description="Extract ATT&CK techniques referenced in a simulation run's agent outputs.",
)
async def get_simulation_techniques(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    _workspace_id(current_user)  # ensure user has a workspace
    svc = MITREService(db)
    result = await svc.get_simulation_techniques(run_id)
    if result["total_techniques"] == 0:
        raise NotFoundError("No techniques found for simulation run")
    return result
