"""
ExportService — Generate exportable reports from simulation results.

Sprint 32: Produces structured reports in multiple formats:
1. JSON — Machine-readable full simulation dump
2. Markdown — Human-readable report with tables and code blocks
3. Executive Summary — Brief 1-page overview for CISOs
4. IaC Bundle — Collected Terraform/CloudFormation from DEFEND-01
5. MITRE ATT&CK Map — Technique coverage from EXPLOIT-01/DEFEND-01
"""

from __future__ import annotations
import json, re, uuid
from datetime import datetime, UTC
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.simulation_run import SimulationRun
from app.models.swarm_agent import SwarmAgent
from app.models.comm_message import CommMessage
from app.models.validation_gate import ValidationGate


class ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _load_run_data(self, run_id: uuid.UUID) -> dict:
        """Load complete simulation data for export."""
        run = await self.db.get(SimulationRun, run_id)
        if not run:
            return {}

        agents_result = await self.db.execute(
            select(SwarmAgent)
            .where(SwarmAgent.simulation_run_id == run_id)
            .order_by(SwarmAgent.created_at)
        )
        agents = list(agents_result.scalars().all())

        msgs_result = await self.db.execute(
            select(CommMessage)
            .where(CommMessage.simulation_run_id == run_id)
            .order_by(CommMessage.sequence_number)
        )
        messages = list(msgs_result.scalars().all())

        gates_result = await self.db.execute(
            select(ValidationGate)
            .where(ValidationGate.simulation_run_id == run_id)
            .order_by(ValidationGate.gate_number)
        )
        gates = list(gates_result.scalars().all())

        return {"run": run, "agents": agents, "messages": messages, "gates": gates}

    # ── JSON Export ───────────────────────────────────────────────

    async def export_json(self, run_id: uuid.UUID) -> dict:
        """Full JSON export of simulation run."""
        data = await self._load_run_data(run_id)
        if not data:
            return {}
        run = data["run"]
        return {
            "export_format": "json",
            "exported_at": datetime.now(UTC).isoformat(),
            "simulation": {
                "id": str(run.id),
                "domain": run.domain,
                "status": run.status,
                "confidence_score": run.confidence_score,
                "total_tokens": run.total_tokens_used,
                "total_cost_usd": run.total_cost_usd,
                "duration_seconds": run.duration_seconds,
                "started_at": str(run.started_at) if run.started_at else None,
                "completed_at": str(run.completed_at) if run.completed_at else None,
            },
            "agents": [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "role": a.role,
                    "status": a.status,
                    "output": a.output,
                    "working_memory": json.loads(a.working_memory) if a.working_memory else {},
                    "input_tokens": a.input_tokens,
                    "output_tokens": a.output_tokens,
                    "cost_usd": a.cost_usd,
                }
                for a in data["agents"]
            ],
            "gates": [
                {
                    "gate_number": g.gate_number,
                    "name": g.name,
                    "state": g.state,
                    "score": g.score,
                    "evidence": g.evidence,
                    "is_double_weight": g.is_double_weight,
                }
                for g in data["gates"]
            ],
            "audit_trail": [
                {
                    "sequence": m.sequence_number,
                    "from": m.from_agent_id,
                    "to": m.to_agent_id,
                    "type": m.message_type,
                    "body": m.body,
                }
                for m in data["messages"]
            ],
        }

    # ── Markdown Export ───────────────────────────────────────────

    async def export_markdown(self, run_id: uuid.UUID) -> str:
        """Generate a markdown report from simulation results."""
        data = await self._load_run_data(run_id)
        if not data:
            return "# Error: Simulation not found"
        run = data["run"]

        lines: list[str] = []
        lines.append("# OmniSec Threat Simulation Report")
        lines.append(f"**Domain:** {run.domain}")
        lines.append(f"**Status:** {run.status}")
        lines.append(f"**Confidence:** {run.confidence_score:.1f}%")
        if run.duration_seconds:
            lines.append(f"**Duration:** {run.duration_seconds:.1f}s")
        lines.append(f"**Cost:** ${run.total_cost_usd:.4f}")
        lines.append(f"**Date:** {run.started_at}")
        lines.append("")

        # Validation Summary
        lines.append("## Validation Gate Results")
        lines.append("| Gate | Name | Status | Score | Evidence |")
        lines.append("|------|------|--------|-------|----------|")
        for g in data["gates"]:
            icon = (
                "PASS" if g.state == "pass"
                else "FAIL" if g.state == "fail"
                else "WARN"
            )
            dw = " [2x]" if g.is_double_weight else ""
            evidence_snippet = (g.evidence or "")[:60]
            lines.append(
                f"| {g.gate_number}{dw} | {g.name} | {icon} | {g.score:.0f}% | {evidence_snippet} |"
            )
        lines.append("")

        # Agent Outputs
        lines.append("## Agent Analysis")
        for a in data["agents"]:
            lines.append(f"### {a.agent_id} -- {a.name} ({a.role})")
            lines.append(
                f"*Status: {a.status} | Tokens: {a.input_tokens}+{a.output_tokens} | Cost: ${a.cost_usd:.4f}*"
            )
            lines.append("")
            if a.output:
                lines.append(a.output[:3000])
            lines.append("")

        # Communication Log
        lines.append("## Communication Bus Audit Trail")
        lines.append(f"*{len(data['messages'])} messages exchanged*")
        lines.append("")
        type_labels = {
            "info": "INFO",
            "solution": "SOLUTION",
            "alert": "ALERT",
            "spawn": "SPAWN",
            "wiz": "WIZ",
        }
        for m in data["messages"][:50]:
            label = type_labels.get(m.message_type, "MSG")
            lines.append(
                f"- [{label}] **{m.from_agent_id}** -> **{m.to_agent_id}**: {m.body[:100]}"
            )

        lines.append("")
        lines.append("---")
        lines.append("*Generated by OmniSec Enterprise Platform*")

        return "\n".join(lines)

    # ── Executive Summary ─────────────────────────────────────────

    async def export_executive_summary(self, run_id: uuid.UUID) -> str:
        """Generate a brief executive summary for CISOs."""
        data = await self._load_run_data(run_id)
        if not data:
            return "Simulation not found."
        run = data["run"]
        gates = data["gates"]
        passed = sum(1 for g in gates if g.state == "pass")
        failed = sum(1 for g in gates if g.state == "fail")

        report_agent = next(
            (a for a in data["agents"] if a.agent_id == "REPORT-01"), None
        )
        summary_text = (
            (report_agent.output or "No summary available.")[:1500]
            if report_agent
            else "No summary available."
        )

        recommendation = (
            "APPROVED -- Solution meets minimum 80% confidence threshold."
            if run.confidence_score >= 80
            else "REVIEW REQUIRED -- Solution below 80% confidence threshold. Address failed gates before deployment."
        )

        duration = f"{run.duration_seconds:.0f}s" if run.duration_seconds else "N/A"
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

        return (
            f"# Executive Summary -- {run.domain.upper()} Threat Simulation\n\n"
            f"**Confidence Score:** {run.confidence_score:.0f}%\n"
            f"**Gates Passed:** {passed}/{len(gates)}  |  **Failed:** {failed}\n"
            f"**Duration:** {duration}  |  **Cost:** ${run.total_cost_usd:.4f}\n\n"
            f"## Key Findings\n{summary_text}\n\n"
            f"## Recommendation\n{recommendation}\n\n"
            f"---\n*OmniSec Enterprise Platform | {timestamp}*\n"
        )

    # ── IaC Bundle Export ─────────────────────────────────────────

    async def export_iac_bundle(self, run_id: uuid.UUID) -> dict:
        """Extract IaC code blocks from DEFEND-01 output."""
        data = await self._load_run_data(run_id)
        defend = next(
            (a for a in data.get("agents", []) if a.agent_id == "DEFEND-01"), None
        )
        empty: dict[str, list] = {
            "terraform": [],
            "cloudformation": [],
            "iam_policies": [],
            "detection_rules": [],
        }
        if not defend or not defend.output:
            return empty

        output = defend.output

        # Extract fenced code blocks by language tag
        hcl_blocks = re.findall(r"```(?:hcl|terraform)\n(.*?)```", output, re.DOTALL)
        cfn_blocks = re.findall(
            r"```(?:yaml|cloudformation)\n(.*?)```", output, re.DOTALL
        )
        json_blocks = re.findall(r"```json\n(.*?)```", output, re.DOTALL)
        sql_blocks = re.findall(
            r"```(?:sql)?\n(.*?SELECT.*?)```", output, re.DOTALL | re.IGNORECASE
        )

        return {
            "terraform": hcl_blocks,
            "cloudformation": cfn_blocks,
            "iam_policies": json_blocks,
            "detection_rules": sql_blocks,
        }
