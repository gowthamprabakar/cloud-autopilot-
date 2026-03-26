"""
Audit Trail & Session History router (Sprint 34).

GET  /api/v1/audit-trail/{run_id}              Audit trail for a run
GET  /api/v1/audit-trail/workspace             Workspace-wide audit trail
GET  /api/v1/audit-trail/export/{run_id}       Compliance export
GET  /api/v1/audit-trail/search                Search audit entries

GET  /api/v1/session-history                   Simulation history with trends
GET  /api/v1/session-history/trends            Domain trend analysis
GET  /api/v1/session-history/costs             Cost analysis
GET  /api/v1/session-history/compare           Compare two runs
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import BadRequestError, ForbiddenError
from app.services.audit_trail_service import AuditTrailService
from app.services.session_history_service import SessionHistoryService

# ── Helpers ──────────────────────────────────────────────────────────────────


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


# ═══════════════════════════════════════════════════════════════════════════
# Audit Trail endpoints
# ═══════════════════════════════════════════════════════════════════════════

audit_router = APIRouter(prefix="/audit-trail", tags=["audit-trail"])


@audit_router.get("/workspace")
async def get_workspace_trail(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(1000, ge=1, le=5000),
):
    """Get all audit entries for the current workspace within a time window."""
    ws_id = _workspace_id(current_user)
    svc = AuditTrailService(db)
    return await svc.get_workspace_trail(ws_id, days=days, limit=limit)


@audit_router.get("/search")
async def search_trail(
    current_user: CurrentUserDep,
    q: str = Query(..., min_length=1, max_length=256),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
):
    """Search audit entries by action text, actor, or event type."""
    ws_id = _workspace_id(current_user)
    svc = AuditTrailService(db)
    return await svc.search_trail(ws_id, query=q, limit=limit)


@audit_router.get("/export/{run_id}")
async def export_compliance_report(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Export audit trail in SOC2/ISO27001 compliance-ready format."""
    ws_id = _workspace_id(current_user)
    svc = AuditTrailService(db)
    return await svc.export_compliance_report(ws_id, run_id=run_id)


@audit_router.get("/{run_id}")
async def get_run_trail(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    event_type: str | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
):
    """Get the full audit trail for a specific simulation run."""
    _workspace_id(current_user)  # auth guard
    svc = AuditTrailService(db)
    return await svc.get_trail(run_id, event_type=event_type, limit=limit)


# ═══════════════════════════════════════════════════════════════════════════
# Session History endpoints
# ═══════════════════════════════════════════════════════════════════════════

history_router = APIRouter(prefix="/session-history", tags=["session-history"])


@history_router.get("")
async def get_history(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    domain: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """Get simulation history with trend data."""
    ws_id = _workspace_id(current_user)
    svc = SessionHistoryService(db)
    return await svc.get_history(ws_id, domain=domain, limit=limit)


@history_router.get("/trends")
async def get_domain_trends(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
):
    """Analyze trends per threat domain across simulation runs."""
    ws_id = _workspace_id(current_user)
    svc = SessionHistoryService(db)
    return await svc.get_domain_trends(ws_id)


@history_router.get("/costs")
async def get_cost_analysis(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Analyze API cost trends over a time window."""
    ws_id = _workspace_id(current_user)
    svc = SessionHistoryService(db)
    return await svc.get_cost_analysis(ws_id, days=days)


@history_router.get("/compare")
async def compare_runs(
    current_user: CurrentUserDep,
    run1: uuid.UUID = Query(...),
    run2: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Compare two simulation runs side-by-side."""
    _workspace_id(current_user)  # auth guard
    if run1 == run2:
        raise BadRequestError("Cannot compare a run with itself")
    svc = SessionHistoryService(db)
    return await svc.compare_runs(run1, run2)


# ── Combined router for main.py registration ────────────────────────────────

router = APIRouter()
router.include_router(audit_router)
router.include_router(history_router)
