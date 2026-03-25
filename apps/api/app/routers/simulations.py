"""
OmniSec Simulation Engine router (Sprint 29).

POST   /api/v1/simulations              Launch new simulation
GET    /api/v1/simulations              List simulation runs
GET    /api/v1/simulations/{run_id}     Get simulation status + agents + gates
GET    /api/v1/simulations/{run_id}/gates    Get 12-gate results
GET    /api/v1/simulations/{run_id}/solution Get final solution text
GET    /api/v1/simulations/{run_id}/audit    Get comm bus messages
DELETE /api/v1/simulations/{run_id}     Delete a run
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUserDep
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.services.simulation_service import (
    THREAT_DOMAINS,
    SimulationService,
)

router = APIRouter(prefix="/simulations", tags=["simulations"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _workspace_id(current_user) -> uuid.UUID:
    if current_user.workspace_id is None:
        raise ForbiddenError("User has no workspace assigned")
    wid = current_user.workspace_id
    return uuid.UUID(str(wid)) if not isinstance(wid, uuid.UUID) else wid


def _run_to_dict(run) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "workspace_id": str(run.workspace_id),
        "user_id": str(run.user_id),
        "domain": run.domain,
        "domain_label": THREAT_DOMAINS.get(run.domain, run.domain),
        "status": run.status,
        "agent_count": run.agent_count,
        "message_count": run.message_count,
        "solution_count": run.solution_count,
        "gates_passed": run.gates_passed,
        "gates_total": run.gates_total,
        "confidence_score": run.confidence_score,
        "total_tokens_used": run.total_tokens_used,
        "total_cost_usd": run.total_cost_usd,
        "duration_seconds": run.duration_seconds,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


def _agent_to_dict(agent) -> dict[str, Any]:
    return {
        "id": str(agent.id),
        "agent_id": agent.agent_id,
        "name": agent.name,
        "role": agent.role,
        "status": agent.status,
        "progress": agent.progress,
        "autonomy_level": agent.autonomy_level,
        "spawn_authority": agent.spawn_authority,
        "output": json.loads(agent.output) if agent.output else None,
        "input_tokens": agent.input_tokens,
        "output_tokens": agent.output_tokens,
        "cost_usd": agent.cost_usd,
        "started_at": agent.started_at.isoformat() if agent.started_at else None,
        "completed_at": agent.completed_at.isoformat() if agent.completed_at else None,
    }


def _gate_to_dict(gate) -> dict[str, Any]:
    return {
        "id": str(gate.id),
        "gate_number": gate.gate_number,
        "name": gate.name,
        "state": gate.state,
        "score": gate.score,
        "evidence": gate.evidence,
        "is_double_weight": gate.is_double_weight,
        "coverage": gate.coverage,
    }


def _message_to_dict(msg) -> dict[str, Any]:
    return {
        "id": str(msg.id),
        "from_agent_id": msg.from_agent_id,
        "to_agent_id": msg.to_agent_id,
        "message_type": msg.message_type,
        "body": msg.body,
        "sequence_number": msg.sequence_number,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


# ── Request / Response schemas ───────────────────────────────────────────────


class LaunchSimulationRequest(BaseModel):
    domain: str = Field(
        ...,
        description="Threat domain key (e.g. 'cspm', 'quantum', 'cdr')",
        examples=["cspm", "quantum", "cdr"],
    )
    sim_config: dict | None = Field(
        default=None,
        description="Optional simulation configuration overrides",
    )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "",
    summary="Launch new simulation",
    description=(
        "Creates a new OmniSec simulation run for the given threat domain "
        "and starts executing the 6-agent swarm pipeline in the background."
    ),
    status_code=201,
)
async def launch_simulation(
    body: LaunchSimulationRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)

    if body.domain not in THREAT_DOMAINS:
        raise BadRequestError(
            f"Unknown threat domain '{body.domain}'. "
            f"Valid domains: {', '.join(sorted(THREAT_DOMAINS.keys()))}"
        )

    svc = SimulationService(db)
    run = await svc.create_run(
        workspace_id=workspace_id,
        user_id=current_user.id,
        domain=body.domain,
        sim_config=body.sim_config,
    )
    await db.commit()
    await db.refresh(run)

    # Execute simulation in the background so the POST returns immediately
    background_tasks.add_task(_run_simulation_bg, str(run.id))

    return _run_to_dict(run)


async def _run_simulation_bg(run_id_str: str) -> None:
    """Background task that executes the simulation in its own DB session."""
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        svc = SimulationService(db)
        try:
            await svc.execute_simulation(uuid.UUID(run_id_str))
        except Exception:
            # Error already persisted by execute_simulation
            pass


@router.get(
    "",
    summary="List simulation runs",
    description="List simulation runs for the current workspace, newest first.",
)
async def list_simulations(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    svc = SimulationService(db)
    runs = await svc.list_runs(workspace_id, limit=limit)
    return [_run_to_dict(r) for r in runs]


@router.get(
    "/{run_id}",
    summary="Get simulation details",
    description="Get simulation run status with agents and gate results.",
)
async def get_simulation(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = SimulationService(db)
    run = await svc.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise NotFoundError("Simulation run not found")

    agents = await svc.get_agents(run_id)
    gates = await svc.get_gates(run_id)

    return {
        **_run_to_dict(run),
        "agents": [_agent_to_dict(a) for a in agents],
        "gates": [_gate_to_dict(g) for g in gates],
    }


@router.get(
    "/{run_id}/gates",
    summary="Get 12-gate results",
    description="Get the 12 validation gate results for a simulation run.",
)
async def get_simulation_gates(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    svc = SimulationService(db)
    run = await svc.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise NotFoundError("Simulation run not found")

    gates = await svc.get_gates(run_id)
    return [_gate_to_dict(g) for g in gates]


@router.get(
    "/{run_id}/solution",
    summary="Get final solution text",
    description=(
        "Get the compiled solution output from all agents. "
        "Includes the executive summary from the REPORT-01 agent."
    ),
)
async def get_simulation_solution(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = SimulationService(db)
    run = await svc.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise NotFoundError("Simulation run not found")

    agents = await svc.get_agents(run_id)
    solution: dict[str, Any] = {
        "run_id": str(run_id),
        "domain": run.domain,
        "domain_label": THREAT_DOMAINS.get(run.domain, run.domain),
        "status": run.status,
        "confidence_score": run.confidence_score,
        "agents": {},
    }
    for agent in agents:
        parsed = json.loads(agent.output) if agent.output else None
        solution["agents"][agent.agent_id] = {
            "name": agent.name,
            "role": agent.role,
            "output": parsed,
        }

    return solution


@router.get(
    "/{run_id}/audit",
    summary="Get comm bus messages",
    description="Get all inter-agent communication messages for audit trail.",
)
async def get_simulation_audit(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    workspace_id = _workspace_id(current_user)
    svc = SimulationService(db)
    run = await svc.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise NotFoundError("Simulation run not found")

    messages = await svc.get_messages(run_id)
    return [_message_to_dict(m) for m in messages]


@router.delete(
    "/{run_id}",
    summary="Delete a simulation run",
    description="Delete a simulation run and all associated agents, gates, and messages.",
)
async def delete_simulation(
    run_id: uuid.UUID,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_db),
) -> dict:
    workspace_id = _workspace_id(current_user)
    svc = SimulationService(db)
    run = await svc.get_run(run_id)
    if run is None or run.workspace_id != workspace_id:
        raise NotFoundError("Simulation run not found")

    deleted = await svc.delete_run(run_id)
    return {"deleted": deleted, "run_id": str(run_id)}
