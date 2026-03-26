"""
SpawnService — On-demand specialist agent spawning.

Sprint 30: Allows spawning DeepDiver agents mid-simulation for focused analysis.
"""

from __future__ import annotations
import uuid, json
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.swarm_agent import SwarmAgent
from app.models.simulation_run import SimulationRun
from app.models.comm_message import CommMessage


# Full 15-agent roster with metadata
FULL_AGENT_ROSTER = {
    # Core 6
    "ORCH-01": {"name": "SwarmMaster", "role": "orchestrator", "autonomy": 5, "spawn_authority": True, "domain": "cross-domain", "sigil": "\U0001f441", "color": "#FF6B35"},
    "SCOUT-01": {"name": "PathFinder", "role": "recon", "autonomy": 4, "spawn_authority": False, "domain": "reconnaissance", "sigil": "\U0001f50d", "color": "#00D4FF"},
    "EXPLOIT-01": {"name": "ExploitSynth", "role": "exploit", "autonomy": 4, "spawn_authority": True, "domain": "exploitation", "sigil": "\u26a1", "color": "#FF3366"},
    "DEFEND-01": {"name": "ShieldWeaver", "role": "defend", "autonomy": 4, "spawn_authority": False, "domain": "defense", "sigil": "\U0001f6e1", "color": "#00FF88"},
    "VALID-01": {"name": "GateKeeper", "role": "validate", "autonomy": 5, "spawn_authority": False, "domain": "certification", "sigil": "\u2713", "color": "#FFD700"},
    "REPORT-01": {"name": "ReportAgent", "role": "report", "autonomy": 3, "spawn_authority": False, "domain": "synthesis", "sigil": "\U0001f4cb", "color": "#9B59B6"},
    # Wiz CNAPP Agents
    "WIZ-CSPM": {"name": "CSPMAgent", "role": "cspm_simulation", "autonomy": 3, "spawn_authority": False, "domain": "posture", "sigil": "\U0001f527", "color": "#3498DB"},
    "WIZ-CIEM": {"name": "CIEMAgent", "role": "ciem_simulation", "autonomy": 3, "spawn_authority": False, "domain": "identity", "sigil": "\U0001f511", "color": "#E67E22"},
    "WIZ-CDR": {"name": "CDRAgent", "role": "cdr_simulation", "autonomy": 3, "spawn_authority": False, "domain": "detection", "sigil": "\U0001f4e1", "color": "#E74C3C"},
    # Gap Domain Specialists
    "QUANT-01": {"name": "QuantumSage", "role": "quantum_specialist", "autonomy": 4, "spawn_authority": False, "domain": "quantum", "sigil": "\u269b", "color": "#8E44AD"},
    "FAKE-01": {"name": "DeepFakeHunter", "role": "deepfake_specialist", "autonomy": 4, "spawn_authority": False, "domain": "deepfake", "sigil": "\U0001f3ad", "color": "#D35400"},
    "CHAIN-01": {"name": "ChainBreaker", "role": "supply_chain_specialist", "autonomy": 4, "spawn_authority": False, "domain": "supply_chain", "sigil": "\U0001f517", "color": "#27AE60"},
    "OT-01": {"name": "SCADAGuard", "role": "ot_ics_specialist", "autonomy": 4, "spawn_authority": False, "domain": "ot_ics", "sigil": "\U0001f3ed", "color": "#95A5A6"},
    "LLM-01": {"name": "LLMShield", "role": "llmjacking_specialist", "autonomy": 4, "spawn_authority": False, "domain": "llmjacking", "sigil": "\U0001f916", "color": "#1ABC9C"},
    # Wiz CNAPP Agents (extended)
    "WIZ-DSPM": {"name": "DSPMAgent", "role": "dspm_simulation", "autonomy": 3, "spawn_authority": False, "domain": "data_security", "sigil": "\U0001f5c4", "color": "#2ECC71"},
    "WIZ-KSPM": {"name": "KSPMAgent", "role": "kspm_simulation", "autonomy": 3, "spawn_authority": False, "domain": "kubernetes", "sigil": "\u2638", "color": "#326CE5"},
    "WIZ-IaC": {"name": "IaCAgent", "role": "iac_simulation", "autonomy": 3, "spawn_authority": False, "domain": "code_security", "sigil": "\U0001f4dd", "color": "#F39C12"},
    "WIZ-UVM": {"name": "UVMAgent", "role": "uvm_simulation", "autonomy": 3, "spawn_authority": False, "domain": "vulnerability", "sigil": "\U0001f50d", "color": "#E74C3C"},
    "WIZ-AISPM": {"name": "AISPMAgent", "role": "aispm_simulation", "autonomy": 3, "spawn_authority": False, "domain": "ai_security", "sigil": "\U0001f9e0", "color": "#9B59B6"},
    "WIZ-ASM": {"name": "ASMAgent", "role": "asm_simulation", "autonomy": 3, "spawn_authority": False, "domain": "attack_surface", "sigil": "\U0001f310", "color": "#1ABC9C"},
    # Spawnable
    "DEEP-XX": {"name": "DeepDiver", "role": "deep_analysis", "autonomy": 3, "spawn_authority": False, "domain": "ad-hoc", "sigil": "\U0001f52c", "color": "#BDC3C7"},
}


class SpawnService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def spawn_agent(
        self,
        run_id: uuid.UUID,
        agent_type: str = "DEEP-XX",
        custom_prompt: str | None = None,
    ) -> SwarmAgent:
        """Spawn a new specialist agent into a running simulation."""
        roster_entry = FULL_AGENT_ROSTER.get(agent_type, FULL_AGENT_ROSTER["DEEP-XX"])

        # Generate unique agent_id for spawned agents
        existing = await self.db.execute(
            select(func.count(SwarmAgent.id))
            .where(SwarmAgent.simulation_run_id == run_id)
        )
        count = existing.scalar() or 0

        if agent_type == "DEEP-XX":
            agent_id = f"DEEP-{count + 1:02d}"
        else:
            agent_id = agent_type

        agent = SwarmAgent(
            simulation_run_id=run_id,
            agent_id=agent_id,
            name=roster_entry["name"],
            role=roster_entry["role"],
            status="spawning",
            progress=0,
            autonomy_level=roster_entry["autonomy"],
            spawn_authority=roster_entry["spawn_authority"],
            system_prompt=custom_prompt,
            working_memory=json.dumps({"spawned": True, "spawn_time": datetime.now(UTC).isoformat()}),
            episodic_memory="[]",
            goal_stack=json.dumps(["Perform deep analysis on assigned topic"]),
            perception_feeds=json.dumps(["comm_bus", "prior_agent_outputs"]),
        )
        self.db.add(agent)

        # Post spawn message to comm bus
        msg_seq = await self.db.execute(
            select(func.coalesce(func.max(CommMessage.sequence_number), 0))
            .where(CommMessage.simulation_run_id == run_id)
        )
        next_seq = msg_seq.scalar() + 1

        spawn_msg = CommMessage(
            simulation_run_id=run_id,
            from_agent_id="ORCH-01",
            to_agent_id=agent_id,
            message_type="spawn",
            body=f"Spawning specialist agent {agent_id} ({roster_entry['name']}) for deep-dive analysis",
            sequence_number=next_seq,
        )
        self.db.add(spawn_msg)

        # Update simulation run agent count
        run = await self.db.get(SimulationRun, run_id)
        if run:
            run.agent_count = (run.agent_count or 0) + 1
            run.message_count = (run.message_count or 0) + 1

        await self.db.flush()

        # Transition to idle (ready for execution)
        agent.status = "idle"
        await self.db.flush()

        return agent

    def list_agent_types(self) -> list[dict]:
        """List all available agent types with metadata."""
        return [
            {
                "agent_id": aid,
                "name": info["name"],
                "role": info["role"],
                "autonomy": info["autonomy"],
                "spawn_authority": info["spawn_authority"],
                "domain": info["domain"],
                "sigil": info["sigil"],
                "color": info["color"],
            }
            for aid, info in FULL_AGENT_ROSTER.items()
        ]
