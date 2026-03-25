from datetime import datetime, UTC

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Liveness probe — always returns 200 if the process is alive."""
    return {
        "status": "ok",
        "service": "cloud-posture-copilot-api",
        "version": "0.2.0-phase2",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness probe — checks DB connectivity."""
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unavailable"

    ready = db_status == "ok"
    return {
        "status": "ready" if ready else "not_ready",
        "service": "cloud-posture-copilot-api",
        "checks": {"database": db_status},
    }
