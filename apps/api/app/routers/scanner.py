"""
Scanner router — trigger and monitor AWS ingestion scans.

Endpoints:
  POST /api/v1/scanner/trigger   — trigger async scan (returns 202 immediately)
  GET  /api/v1/scanner/status    — latest scan job for workspace
  GET  /api/v1/scanner/history   — paginated scan history
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.repositories.scan_job_repository import ScanJobRepository
from app.schemas.scanner import (
    ScanHistoryResponse,
    ScanJobResponse,
    ScanStatusResponse,
    ScanTriggerResponse,
)
from app.services.aws_scanner import IngestionEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scanner", tags=["scanner"])


# ── Background task helper ──────────────────────────────────────────────────

async def _run_scan_background(workspace_id: str, aws_account_id: Optional[str]) -> None:
    """Runs in FastAPI BackgroundTasks — gets its own DB session."""
    from app.core.database import AsyncSessionLocal  # avoid circular import

    async with AsyncSessionLocal() as db:
        engine = IngestionEngine(db, workspace_id, aws_account_id)
        result = await engine.run_full_scan(triggered_by="manual")
        logger.info(
            "Background scan complete: workspace=%s added=%d updated=%d status=%s",
            workspace_id, result.findings_added, result.findings_updated, result.status,
        )


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/trigger", status_code=202, response_model=ScanTriggerResponse)
async def trigger_scan(
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    aws_account_id: Optional[str] = Query(None, description="Scan a specific account only"),
) -> ScanTriggerResponse:
    """
    Trigger an AWS security scan for the workspace.
    Returns 202 immediately — scan runs in the background.
    """
    workspace_id = str(current_user.workspace_id)

    # Check if a scan is already running — prevent duplicates
    repo = ScanJobRepository(db)
    running = await repo.get_running(workspace_id)
    if running:
        return ScanTriggerResponse(
            job_id=str(running.id),
            status="already_running",
            message="A scan is already in progress. Check /scanner/status for updates.",
        )

    # Fire the scan in the background
    background_tasks.add_task(_run_scan_background, workspace_id, aws_account_id)

    return ScanTriggerResponse(
        job_id=None,
        status="accepted",
        message="Scan started. Check /api/v1/scanner/status for progress.",
    )


@router.get("/status", response_model=ScanStatusResponse)
async def get_scan_status(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> ScanStatusResponse:
    """Return the latest scan job for the workspace."""
    workspace_id = str(current_user.workspace_id)
    repo = ScanJobRepository(db)
    latest = await repo.get_latest(workspace_id)
    is_running = latest.status == "running" if latest else False

    if not latest:
        msg = "Never scanned — click Scan Now to start."
    elif is_running:
        msg = "Scan in progress..."
    elif latest.status == "completed":
        from datetime import datetime, timezone
        delta = datetime.now(timezone.utc) - latest.completed_at.replace(tzinfo=timezone.utc) if latest.completed_at else None
        if delta:
            mins = int(delta.total_seconds() / 60)
            msg = f"Last synced {mins} minute{'s' if mins != 1 else ''} ago — {latest.findings_added} new findings"
        else:
            msg = f"Last scan completed — {latest.findings_added} new findings"
    elif latest.status == "partial":
        msg = f"Partial scan — {latest.findings_added} new findings ({', '.join(latest.sources_failed)} failed)"
    else:
        msg = f"Last scan failed: {latest.error_message or 'unknown error'}"

    return ScanStatusResponse(
        latest_job=ScanJobResponse.model_validate(latest) if latest else None,
        is_running=is_running,
        last_sync_message=msg,
    )


@router.get("/history", response_model=ScanHistoryResponse)
async def get_scan_history(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ScanHistoryResponse:
    """Paginated scan job history for the workspace."""
    workspace_id = str(current_user.workspace_id)
    repo = ScanJobRepository(db)
    jobs = await repo.list_history(workspace_id, limit=limit, offset=offset)
    return ScanHistoryResponse(
        items=[ScanJobResponse.model_validate(j) for j in jobs],
        total=len(jobs),
    )
