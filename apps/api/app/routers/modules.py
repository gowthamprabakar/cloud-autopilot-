"""
CSPM + CWPP Simulation Module router (Sprint 33).

GET  /api/v1/modules/cspm/posture                 CSPM posture evaluation
GET  /api/v1/modules/cspm/remediation/{finding_id} Generate IaC fix
GET  /api/v1/modules/cwpp/workloads                Workload assessment
GET  /api/v1/modules/cwpp/sbom                     SBOM analysis
GET  /api/v1/modules/cwpp/runtime                  Runtime security assessment
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError, NotFoundError
from app.services.modules.cspm_module import CSPMModule
from app.services.modules.cwpp_module import CWPPModule

router = APIRouter(prefix="/modules", tags=["simulation-modules"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


# ── CSPM Endpoints ──────────────────────────────────────────────────────────


@router.get(
    "/cspm/posture",
    summary="CSPM posture evaluation",
    description=(
        "Run Cloud Security Posture Management evaluation across all findings. "
        "Returns rule pass/fail by category, compliance framework scores, "
        "and an overall posture score."
    ),
)
async def cspm_posture(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CSPMModule(db)
    return await svc.evaluate_posture(workspace_id)


@router.get(
    "/cspm/remediation/{finding_id}",
    summary="Generate IaC remediation",
    description=(
        "Generate Terraform remediation code for a specific finding. "
        "Produces auto-generated IaC blocks for common misconfiguration types."
    ),
)
async def cspm_remediation(
    finding_id: str,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CSPMModule(db)
    result = await svc.generate_remediation(workspace_id, finding_id)
    if "error" in result:
        raise NotFoundError(result["error"])
    return result


# ── CWPP Endpoints ──────────────────────────────────────────────────────────


@router.get(
    "/cwpp/workloads",
    summary="Workload security assessment",
    description=(
        "Assess workload security posture across VM, container, and serverless. "
        "Includes CVE correlation, malware detection, and severity breakdown."
    ),
)
async def cwpp_workloads(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CWPPModule(db)
    return await svc.assess_workloads(workspace_id)


@router.get(
    "/cwpp/sbom",
    summary="SBOM analysis",
    description=(
        "Analyze software bill of materials across workloads. "
        "Aggregates CVE data, maps to workload types, and identifies "
        "critical cross-workload dependencies."
    ),
)
async def cwpp_sbom(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CWPPModule(db)
    return await svc.sbom_analysis(workspace_id)


@router.get(
    "/cwpp/runtime",
    summary="Runtime security assessment",
    description=(
        "Assess runtime security posture for containers and serverless workloads. "
        "Checks image security, syscall policies, secrets management, and network segmentation."
    ),
)
async def cwpp_runtime(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = CWPPModule(db)
    return await svc.runtime_assessment(workspace_id)
