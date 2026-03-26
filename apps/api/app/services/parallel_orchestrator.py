"""
ParallelOrchestrator — Concurrent agent execution engine.

Sprint 33: Replaces the sequential pipeline with a dependency-aware
parallel executor. Agents run concurrently where dependencies allow.

Execution topology:
  Phase 1 (parallel): ORCH-01 (always first, sequential)
  Phase 2 (parallel): SCOUT-01 + any Wiz agents (WIZ-CSPM, WIZ-CIEM, etc.)
  Phase 3 (parallel): EXPLOIT-01 (depends on SCOUT-01)
  Phase 4 (parallel): DEFEND-01 (depends on EXPLOIT-01)
  Phase 5 (parallel): VALID-01 (depends on DEFEND-01)
  Phase 6 (parallel): REPORT-01 (depends on all)

For Wiz CNAPP simulations, domain-specific agents run in Phase 2
alongside SCOUT-01, feeding into the main pipeline.
"""

import asyncio
import json
import os
import random
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comm_message import CommMessage
from app.models.simulation_run import SimulationRun
from app.models.swarm_agent import SwarmAgent
from app.services.agent_executor import AgentExecutor
from app.services.agent_prompts import AGENT_PROMPTS, DOMAIN_CONTEXT
from app.services.comm_bus_service import CommBusService
from app.services.gate_service import GateService

logger = structlog.get_logger(__name__)

# Agent dependency graph: agent_id -> list of agent_ids it depends on
AGENT_DEPENDENCIES: dict[str, list[str]] = {
    "ORCH-01": [],
    "SCOUT-01": ["ORCH-01"],
    "WIZ-CSPM": ["ORCH-01"],
    "WIZ-CIEM": ["ORCH-01"],
    "WIZ-CDR": ["ORCH-01"],
    "WIZ-DSPM": ["ORCH-01"],
    "WIZ-KSPM": ["ORCH-01"],
    "WIZ-IaC": ["ORCH-01"],
    "WIZ-UVM": ["ORCH-01"],
    "WIZ-AISPM": ["ORCH-01"],
    "WIZ-ASM": ["ORCH-01"],
    "QUANT-01": ["ORCH-01"],
    "FAKE-01": ["ORCH-01"],
    "CHAIN-01": ["ORCH-01"],
    "OT-01": ["ORCH-01"],
    "LLM-01": ["ORCH-01"],
    "EXPLOIT-01": ["SCOUT-01"],
    "DEFEND-01": ["EXPLOIT-01"],
    "VALID-01": ["DEFEND-01"],
    "REPORT-01": ["VALID-01"],
}

# Domain -> which extra agents to include
DOMAIN_AGENTS: dict[str, list[str]] = {
    "cspm": ["WIZ-CSPM"],
    "ciem": ["WIZ-CIEM"],
    "cdr": ["WIZ-CDR"],
    "dspm": ["WIZ-DSPM"],
    "kspm": ["WIZ-KSPM"],
    "iac": ["WIZ-IaC"],
    "uvm": ["WIZ-UVM"],
    "ai_spm": ["WIZ-AISPM"],
    "asm": ["WIZ-ASM"],
    "cwpp": ["WIZ-CSPM", "WIZ-UVM"],  # CWPP uses CSPM + UVM
    "quantum": ["QUANT-01"],
    "deepfake": ["FAKE-01"],
    "supply_chain": ["CHAIN-01"],
    "ot_ics": ["OT-01"],
    "llmjacking": ["LLM-01"],
    "agentic_ai": ["LLM-01", "WIZ-AISPM"],
    "federated_id": ["WIZ-CIEM"],
}


class ParallelOrchestrator:
    """Dependency-aware parallel agent execution engine."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.executor = AgentExecutor(db)
        self.comm_bus = CommBusService(db)
        self.gate_svc = GateService(db)

    def _get_agent_roster(self, domain: str) -> list[str]:
        """Determine which agents to run for a given domain."""
        # Core pipeline always included
        core = ["ORCH-01", "SCOUT-01", "EXPLOIT-01", "DEFEND-01", "VALID-01", "REPORT-01"]
        # Domain-specific agents
        extras = DOMAIN_AGENTS.get(domain, [])
        # Deduplicate while preserving order
        roster: list[str] = []
        for aid in core + extras:
            if aid not in roster:
                roster.append(aid)
        return roster

    def _build_phases(self, roster: list[str]) -> list[list[str]]:
        """Build execution phases from dependency graph.

        Returns list of phases, each phase is a list of agent_ids
        that can run in parallel.
        """
        completed: set[str] = set()
        remaining: set[str] = set(roster)
        roster_set = set(roster)
        phases: list[list[str]] = []

        while remaining:
            # Find all agents whose dependencies are satisfied
            ready: list[str] = []
            for aid in remaining:
                deps = AGENT_DEPENDENCIES.get(aid, [])
                # Only consider deps that are in our roster
                relevant_deps = [d for d in deps if d in roster_set]
                if all(d in completed for d in relevant_deps):
                    ready.append(aid)

            if not ready:
                # Deadlock prevention: force remaining agents
                ready = list(remaining)

            phases.append(sorted(ready))
            completed.update(ready)
            remaining -= set(ready)

        return phases

    async def execute(self, run: SimulationRun) -> SimulationRun:
        """Execute simulation with parallel phases."""
        use_live = bool(os.getenv("ANTHROPIC_API_KEY"))

        roster = self._get_agent_roster(run.domain)
        phases = self._build_phases(roster)

        logger.info(
            "parallel_execution_start",
            run_id=str(run.id),
            domain=run.domain,
            mode="live" if use_live else "mock",
            agent_count=len(roster),
            phase_count=len(phases),
            phases=[[a for a in p] for p in phases],
        )

        # Update run
        run.status = "running"
        run.started_at = datetime.now(UTC)
        run.agent_count = len(roster)
        await self.db.flush()

        # Initialize gates
        await self.gate_svc.initialize_gates(run.id)

        # Post start message
        await self.comm_bus.post_message(
            run.id, "SYSTEM", "ALL",
            f"Simulation started: {run.domain} | {len(roster)} agents | {len(phases)} phases",
            "info",
        )

        # Create all agent records
        from app.services.spawn_service import FULL_AGENT_ROSTER

        agents_map: dict[str, SwarmAgent] = {}
        for aid in roster:
            meta = FULL_AGENT_ROSTER.get(
                aid,
                {"name": aid, "role": "specialist", "autonomy": 3, "spawn_authority": False},
            )
            agent = SwarmAgent(
                simulation_run_id=run.id,
                agent_id=aid,
                name=meta["name"],
                role=meta["role"],
                status="idle",
                progress=0,
                autonomy_level=meta["autonomy"],
                spawn_authority=meta.get("spawn_authority", False),
                system_prompt=AGENT_PROMPTS.get(aid, f"You are {meta['name']}."),
                working_memory="{}",
                episodic_memory="[]",
                goal_stack=json.dumps([f"Analyze {run.domain} threat domain"]),
                perception_feeds=json.dumps(["comm_bus", "prior_outputs"]),
            )
            self.db.add(agent)
            agents_map[aid] = agent
        await self.db.flush()

        # Execute phases
        all_outputs: dict[str, str] = {}
        total_tokens = 0
        total_cost = 0.0

        for phase_idx, phase in enumerate(phases):
            await self.comm_bus.post_message(
                run.id, "SYSTEM", "ALL",
                f"Phase {phase_idx + 1}/{len(phases)}: Running {', '.join(phase)}",
                "info",
            )

            if use_live:
                # Run agents in parallel within each phase
                prior_outputs = [
                    {"agent_id": k, "output": v} for k, v in all_outputs.items()
                ]

                async def _run_agent(aid: str, _prior: list[dict]) -> tuple[str, SwarmAgent]:
                    agent = agents_map[aid]
                    await self.executor.execute_agent(run, agent, _prior)
                    return aid, agent

                tasks = [_run_agent(aid, prior_outputs) for aid in phase]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        logger.error("agent_execution_error", error=str(result))
                        continue
                    aid, agent = result
                    if agent.output:
                        all_outputs[aid] = agent.output
                    total_tokens += (agent.input_tokens or 0) + (agent.output_tokens or 0)
                    total_cost += agent.cost_usd or 0

                    # Post completion message
                    await self.comm_bus.post_message(
                        run.id, aid, "ALL",
                        f"{agents_map[aid].name} completed analysis",
                        "solution" if aid == "REPORT-01" else "info",
                    )
            else:
                # Mock mode: simulate with delays
                for aid in phase:
                    agent = agents_map[aid]
                    agent.status = "running"
                    agent.started_at = datetime.now(UTC)
                    await self.db.flush()

                    await asyncio.sleep(0.5)  # Brief mock delay

                    agent.status = "done"
                    agent.progress = 100
                    agent.output = self._mock_output(aid, run.domain)
                    agent.working_memory = json.dumps({"mock": True, "domain": run.domain})
                    agent.completed_at = datetime.now(UTC)
                    # Mock token usage
                    agent.input_tokens = random.randint(800, 2500)
                    agent.output_tokens = random.randint(400, 1800)
                    agent.cost_usd = round(
                        (agent.input_tokens * 0.003 + agent.output_tokens * 0.015) / 1000, 4
                    )
                    total_tokens += agent.input_tokens + agent.output_tokens
                    total_cost += agent.cost_usd
                    all_outputs[aid] = agent.output
                    await self.db.flush()

                    await self.comm_bus.post_message(
                        run.id, aid, "ALL",
                        f"{agent.name} completed ({run.domain})",
                        "info",
                    )

        # Update gates from VALID-01 output
        if "VALID-01" in all_outputs:
            await self.gate_svc.update_from_validator_output(
                run.id, all_outputs["VALID-01"]
            )

        # Compute confidence
        confidence = await self.gate_svc.compute_confidence(run.id)
        msg_count = await self.comm_bus.message_count(run.id)
        gates = await self.gate_svc.get_gates(run.id)
        gates_passed = len([g for g in gates if g.state == "pass"])

        # Finalize run
        run.status = "completed"
        run.confidence_score = confidence
        run.total_tokens_used = total_tokens
        run.total_cost_usd = round(total_cost, 6)
        run.message_count = msg_count
        run.solution_count = sum(1 for a in agents_map.values() if a.output)
        run.gates_passed = gates_passed
        run.gates_total = len(gates)
        run.completed_at = datetime.now(UTC)
        run.duration_seconds = (
            (run.completed_at - run.started_at).total_seconds() if run.started_at else 0
        )

        await self.db.commit()

        await self.comm_bus.post_message(
            run.id, "SYSTEM", "ALL",
            f"Simulation complete! Confidence: {confidence:.1f}% | Cost: ${total_cost:.4f}",
            "solution",
        )

        logger.info(
            "parallel_execution_complete",
            run_id=str(run.id),
            confidence=confidence,
            gates_passed=gates_passed,
            total_tokens=total_tokens,
            total_cost=round(total_cost, 4),
            duration=run.duration_seconds,
        )

        return run

    @staticmethod
    def _mock_output(agent_id: str, domain: str) -> str:
        """Generate mock output for testing without Claude API."""
        mock_outputs = {
            "ORCH-01": (
                f"## Threat Decomposition: {domain}\n"
                f"### Attack Vectors\n"
                f"- Vector 1: Cloud misconfiguration (CRITICAL)\n"
                f"- Vector 2: Identity compromise (HIGH)\n"
                f"- Vector 3: Data exfiltration (HIGH)\n"
                f"### Risk Score: {random.randint(70, 95)}"
            ),
            "SCOUT-01": (
                f"## Reconnaissance Report\n"
                f"### Vectors Found: 5\n"
                f"- **Public S3 Bucket**: CRITICAL (T1530)\n"
                f"- **Overprivileged IAM Role**: HIGH (T1078)\n"
                f"- **Unpatched EC2**: HIGH (T1190)\n"
                f"### Exposure Score: {random.randint(60, 90)}"
            ),
            "EXPLOIT-01": (
                f"## Kill Chain Analysis\n"
                f"### Chain 1: Data Exfiltration\n"
                f"1. Initial Access: T1190 - Exploit public app\n"
                f"2. Privilege Escalation: T1078.004 - Cloud accounts\n"
                f"3. Lateral Movement: T1021 - Remote services\n"
                f"4. Impact: T1530 - Data from cloud storage\n"
                f"### Blast Radius: {random.randint(5, 20)} resources"
            ),
            "DEFEND-01": (
                f"## Defensive Architecture\n"
                f"### Controls: 8 designed\n"
                f'```hcl\n'
                f'resource "aws_s3_bucket_public_access_block" "block" {{\n'
                f"  bucket = aws_s3_bucket.data.id\n"
                f"  block_public_acls = true\n"
                f"}}\n"
                f"```\n"
                f"### Coverage: {random.randint(80, 95)}%"
            ),
            "VALID-01": "\n".join(
                [
                    f"Gate {i} {name}: {'PASS' if random.random() > 0.2 else 'PARTIAL'} "
                    f"(Score: {random.randint(70, 98)}) - Evidence: Validated"
                    for i, name in enumerate(
                        [
                            "Cryptographic Hardening",
                            "Attack Surface Reduction",
                            "IaC Policy Correctness",
                            "Detection Completeness",
                            "Automated Response Speed",
                            "Blast Radius Containment",
                            "Lateral Movement Prevention",
                            "Credential Lifecycle",
                            "Cross-Account Coverage",
                            "Continuous Monitoring",
                            "IR Playbook Completeness",
                            "Red-Team Pass Rate",
                        ],
                        1,
                    )
                ]
            )
            + f"\n\nOverall Confidence: {random.randint(75, 95)}%",
            "REPORT-01": (
                f"## Executive Summary\n"
                f"The {domain} threat simulation achieved high confidence. "
                f"Key controls validated across 12 gates.\n"
                f"## Recommendation\n"
                f"Solution meets deployment criteria."
            ),
        }
        # For Wiz/domain agents, generate domain-specific mock
        if agent_id.startswith("WIZ-") or agent_id in {
            "QUANT-01",
            "FAKE-01",
            "CHAIN-01",
            "OT-01",
            "LLM-01",
        }:
            return (
                f"## {agent_id} Analysis -- {domain}\n"
                f"### Findings: {random.randint(3, 12)}\n"
                f"- Finding 1: Configuration gap detected (HIGH)\n"
                f"- Finding 2: Policy violation (MEDIUM)\n"
                f"### Score: {random.randint(60, 95)}/100"
            )
        return mock_outputs.get(
            agent_id, f"## {agent_id} Output\nAnalysis complete for {domain}."
        )
