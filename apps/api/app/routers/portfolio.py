"""
Portfolio router — MSP/vCISO multi-workspace endpoints (Sprint 24).

GET /api/v1/portfolio/summary     Cross-workspace portfolio overview
GET /api/v1/portfolio/workspaces  List all accessible workspaces
GET /api/v1/portfolio/sla-breaches  SLA breaches across all workspaces
"""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.services.portfolio_service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/summary", summary="Cross-workspace portfolio summary")
async def get_portfolio_summary(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await PortfolioService(db).portfolio_summary()

@router.get("/workspaces", summary="List all workspaces")
async def get_workspaces(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await PortfolioService(db).list_workspaces()

@router.get("/sla-breaches", summary="SLA breaches across portfolio")
async def get_sla_breaches(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    return await PortfolioService(db).sla_breaches()
