"""
Vulns router — Vulnerability Management endpoints (Sprint 22).

GET /api/v1/vulns/summary    High-level CVE + EPSS + KEV stats
GET /api/v1/vulns/inventory  Full CVE inventory with affected resources
GET /api/v1/vulns/{cve_id}   Detail for a specific CVE
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import ForbiddenError
from app.services.vuln_service import VulnService

router = APIRouter(prefix="/vulns", tags=["vulns"])


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


@router.get(
    "/summary",
    summary="Vulnerability posture summary",
    description=(
        "Returns total CVE count, KEV count, critical-EPSS count, "
        "average EPSS score, severity breakdown, and EPSS distribution."
    ),
)
async def get_vuln_summary(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    return await VulnService(db).summary(workspace_id)


@router.get(
    "/inventory",
    summary="Full CVE inventory",
    description=(
        "Returns all CVEs detected in workspace findings, enriched with "
        "EPSS exploitation probability and CISA KEV status, sorted by risk tier."
    ),
)
async def get_vuln_inventory(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    return await VulnService(db).inventory(workspace_id)


@router.get(
    "/{cve_id}",
    summary="CVE detail",
    description="Returns full detail for a specific CVE including all affected resources.",
)
async def get_cve_detail(
    cve_id: str,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    result = await VulnService(db).cve_detail(workspace_id, cve_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"{cve_id} not found in workspace")
    return result
