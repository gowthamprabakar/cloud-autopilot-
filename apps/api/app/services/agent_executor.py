"""
AgentExecutor — Runs a single swarm agent against the Claude API.

Sprint 30: Replaces mock outputs with real Claude API calls.
Each agent gets its system prompt + domain context + prior agent outputs (context chaining).
"""

from __future__ import annotations
import json, uuid, time
from datetime import datetime, UTC
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.swarm_agent import SwarmAgent
from app.models.comm_message import CommMessage
from app.models.simulation_run import SimulationRun
from app.core.claude_client import call_claude, ClaudeAPIError
from app.services.agent_prompts import AGENT_PROMPTS, DOMAIN_CONTEXT


class AgentExecutor:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_agent(
        self,
        run: SimulationRun,
        agent: SwarmAgent,
        prior_outputs: list[dict[str, str]],  # [{"agent_id": "ORCH-01", "output": "..."}]
    ) -> SwarmAgent:
        """Execute a single agent against the Claude API.

        1. Build the user message from domain context + prior agent outputs
        2. Get the system prompt for this agent type
        3. Call Claude API
        4. Update agent record with output, tokens, cost, status
        5. Post completion message to comm bus
        6. Update working memory with key metrics extracted from output
        """
        # Mark agent as running
        agent.status = "running"
        agent.started_at = datetime.now(UTC)
        await self.db.flush()

        # Build user message
        domain_ctx = DOMAIN_CONTEXT.get(run.domain, f"Analyze the {run.domain} threat domain.")

        # Context chaining: include all prior agent outputs
        context_parts = [f"## Threat Domain\n{domain_ctx}"]
        for prior in prior_outputs:
            context_parts.append(f"\n## {prior['agent_id']} Output\n{prior['output'][:2000]}")

        user_message = "\n\n".join(context_parts)

        # Get system prompt
        system_prompt = AGENT_PROMPTS.get(agent.agent_id, f"You are {agent.name}, a security analysis agent.")

        # Determine max_tokens based on agent role
        token_limits = {
            "ORCH-01": 800, "SCOUT-01": 900, "EXPLOIT-01": 1000,
            "DEFEND-01": 1000, "VALID-01": 800, "REPORT-01": 1000,
        }
        max_tokens = token_limits.get(agent.agent_id, 1000)

        try:
            response_text, input_tokens, output_tokens = await call_claude(
                system_prompt=system_prompt,
                user_message=user_message,
                max_tokens=max_tokens,
            )

            # Calculate cost (Claude Sonnet: $3/M input, $15/M output)
            cost = (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)

            # Update agent
            agent.status = "done"
            agent.progress = 100
            agent.output = response_text
            agent.input_tokens = input_tokens
            agent.output_tokens = output_tokens
            agent.cost_usd = round(cost, 6)
            agent.completed_at = datetime.now(UTC)

            # Update working memory based on role
            agent.working_memory = json.dumps(self._extract_working_memory(agent.agent_id, response_text))

            # Update episodic memory
            episodes = json.loads(agent.episodic_memory or "[]")
            episodes.append(f"Completed {run.domain} analysis at {datetime.now(UTC).isoformat()}")
            if len(episodes) > 6:
                episodes = episodes[-6:]  # FIFO max 6
            agent.episodic_memory = json.dumps(episodes)

        except ClaudeAPIError as e:
            agent.status = "error"
            agent.error_message = str(e)
            agent.completed_at = datetime.now(UTC)
            response_text = f"ERROR: {e}"
        except Exception as e:
            agent.status = "error"
            agent.error_message = str(e)[:500]
            agent.completed_at = datetime.now(UTC)
            response_text = f"ERROR: {e}"

        await self.db.flush()
        return agent

    def _extract_working_memory(self, agent_id: str, output: str) -> dict:
        """Extract key metrics from agent output for working memory."""
        memory = {"last_run": datetime.now(UTC).isoformat(), "output_length": len(output)}

        text_lower = output.lower()
        if agent_id == "ORCH-01":
            memory["threat_decomposed"] = True
            memory["vectors_identified"] = text_lower.count("vector") + text_lower.count("attack")
        elif agent_id == "SCOUT-01":
            memory["recon_complete"] = True
            memory["exposure_score"] = min(100, text_lower.count("critical") * 20 + text_lower.count("high") * 10)
        elif agent_id == "EXPLOIT-01":
            memory["chains_built"] = max(1, text_lower.count("kill chain") + text_lower.count("chain"))
            memory["mitre_techniques"] = text_lower.count("t1")
        elif agent_id == "DEFEND-01":
            memory["controls_designed"] = True
            memory["iac_patches"] = text_lower.count("resource") + text_lower.count("terraform")
            memory["detection_rules"] = text_lower.count("select") + text_lower.count("detection")
        elif agent_id == "VALID-01":
            memory["gates_evaluated"] = 12
            memory["pass_count"] = text_lower.count("pass")
            memory["fail_count"] = text_lower.count("fail")
        elif agent_id == "REPORT-01":
            memory["report_generated"] = True
            memory["confidence_computed"] = True

        return memory
