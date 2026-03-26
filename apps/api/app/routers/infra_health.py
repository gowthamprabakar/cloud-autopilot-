"""
Infrastructure Health Router — Sprint 31.

GET /api/v1/infra/health — Full infrastructure health check
GET /api/v1/infra/metrics — Platform metrics (agent runs, gate scores, costs)
"""

import os
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import CurrentUserDep

router = APIRouter(prefix="/infra", tags=["infrastructure"])


@router.get("/health", summary="Full infrastructure health check")
async def infra_health(db: AsyncSession = Depends(get_db)) -> dict:
    """Check health of all infrastructure components."""
    health = {"status": "ok", "components": {}}

    # 1. Database
    try:
        from sqlalchemy import text
        await db.execute(text("SELECT 1"))
        health["components"]["database"] = {"status": "ok", "type": os.getenv("DATABASE_URL", "sqlite")[:10]}
    except Exception as e:
        health["components"]["database"] = {"status": "error", "error": str(e)[:100]}
        health["status"] = "degraded"

    # 2. Redis
    try:
        from app.core.redis_client import redis_health
        redis_status = await redis_health()
        health["components"]["redis"] = redis_status
        if not redis_status.get("connected"):
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["redis"] = {"status": "unavailable", "error": str(e)[:100]}

    # 3. Neo4j
    try:
        from app.core.neo4j_client import neo4j_health
        neo4j_status = await neo4j_health()
        health["components"]["neo4j"] = neo4j_status
        if not neo4j_status.get("connected"):
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["neo4j"] = {"status": "unavailable", "error": str(e)[:100]}

    # 4. Claude API
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        health["components"]["claude_api"] = {
            "status": "configured" if api_key else "not_configured",
            "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        }
    except Exception as e:
        health["components"]["claude_api"] = {"status": "error", "error": str(e)[:100]}

    # 5. Event Bus
    try:
        from app.services.event_bus import get_event_bus
        bus = await get_event_bus()
        health["components"]["event_bus"] = {"status": "ok", "mode": bus._mode}
    except Exception as e:
        health["components"]["event_bus"] = {"status": "unavailable", "error": str(e)[:100]}

    return health


@router.get("/metrics", summary="Platform operational metrics")
async def infra_metrics(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return operational metrics for the OmniSec platform."""
    from app.models.simulation_run import SimulationRun
    from app.models.swarm_agent import SwarmAgent
    from app.models.validation_gate import ValidationGate
    from app.models.comm_message import CommMessage

    # Simulation metrics
    sim_count = await db.execute(select(func.count(SimulationRun.id)))
    total_sims = sim_count.scalar() or 0

    completed = await db.execute(
        select(func.count(SimulationRun.id)).where(SimulationRun.status == "completed")
    )
    completed_sims = completed.scalar() or 0

    # Cost metrics
    cost_result = await db.execute(
        select(func.coalesce(func.sum(SimulationRun.total_cost_usd), 0))
    )
    total_cost = round(float(cost_result.scalar() or 0), 4)

    # Token metrics
    token_result = await db.execute(
        select(func.coalesce(func.sum(SimulationRun.total_tokens_used), 0))
    )
    total_tokens = int(token_result.scalar() or 0)

    # Agent metrics
    agent_count = await db.execute(select(func.count(SwarmAgent.id)))
    total_agents = agent_count.scalar() or 0

    # Gate metrics
    gate_pass = await db.execute(
        select(func.count(ValidationGate.id)).where(ValidationGate.state == "pass")
    )
    gates_passed = gate_pass.scalar() or 0

    gate_total = await db.execute(select(func.count(ValidationGate.id)))
    gates_total = gate_total.scalar() or 0

    # Message metrics
    msg_count = await db.execute(select(func.count(CommMessage.id)))
    total_messages = msg_count.scalar() or 0

    # Average confidence
    avg_conf = await db.execute(
        select(func.avg(SimulationRun.confidence_score))
        .where(SimulationRun.status == "completed")
    )
    avg_confidence = round(float(avg_conf.scalar() or 0), 2)

    return {
        "simulations": {
            "total": total_sims,
            "completed": completed_sims,
            "success_rate": round(completed_sims / total_sims * 100, 1) if total_sims > 0 else 0,
            "avg_confidence": avg_confidence,
        },
        "agents": {
            "total_executions": total_agents,
        },
        "gates": {
            "total_evaluated": gates_total,
            "passed": gates_passed,
            "pass_rate": round(gates_passed / gates_total * 100, 1) if gates_total > 0 else 0,
        },
        "communication": {
            "total_messages": total_messages,
        },
        "cost": {
            "total_usd": total_cost,
            "total_tokens": total_tokens,
            "monthly_budget": 500.0,
            "budget_used_pct": round(total_cost / 500.0 * 100, 2),
        },
    }
