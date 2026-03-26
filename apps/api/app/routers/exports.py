"""
Export router — simulation report export endpoints.

Sprint 32: Exposes endpoints to export simulation results in multiple formats.

GET /api/v1/exports/{run_id}/json       Full JSON export
GET /api/v1/exports/{run_id}/markdown   Markdown report
GET /api/v1/exports/{run_id}/executive  Executive summary
GET /api/v1/exports/{run_id}/iac        IaC code bundle
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import NotFoundError
from app.services.export_service import ExportService

router = APIRouter(prefix="/exports", tags=["exports"])


# ── JSON Export ───────────────────────────────────────────────


@router.get("/{run_id}/json")
async def export_json(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Full JSON export of a simulation run."""
    svc = ExportService(db)
    result = await svc.export_json(run_id)
    if not result:
        raise NotFoundError("Simulation run not found")
    return result


# ── Markdown Export ───────────────────────────────────────────


@router.get("/{run_id}/markdown", response_class=PlainTextResponse)
async def export_markdown(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Markdown report of a simulation run."""
    svc = ExportService(db)
    result = await svc.export_markdown(run_id)
    if result == "# Error: Simulation not found":
        raise NotFoundError("Simulation run not found")
    return result


# ── Executive Summary ─────────────────────────────────────────


@router.get("/{run_id}/executive", response_class=PlainTextResponse)
async def export_executive_summary(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Executive summary for CISOs."""
    svc = ExportService(db)
    result = await svc.export_executive_summary(run_id)
    if result == "Simulation not found.":
        raise NotFoundError("Simulation run not found")
    return result


# ── IaC Bundle Export ─────────────────────────────────────────


@router.get("/{run_id}/iac")
async def export_iac_bundle(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Extract IaC code blocks (Terraform, CloudFormation, IAM policies, detection rules)."""
    svc = ExportService(db)
    return await svc.export_iac_bundle(run_id)
