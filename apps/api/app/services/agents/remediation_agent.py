"""
RemediationPlannerAgent — THINK layer agent.

Generates a step-by-step IaC remediation plan for a security finding.
Prefers Terraform > AWS CLI > Console steps (enforced by sort after LLM output).
Routes to Claude Haiku (better code generation) with Ollama fallback.

Output shape:
  {
    steps: [{step, action, command, iac_type: "terraform"|"cli"|"console"}],
    estimated_effort: "minutes"|"hours"|"days",
    auto_remediatable: bool,
    fallback_used: bool,
  }
"""

import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.agent_result import AgentResult
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.services.agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

_IAC_PRIORITY = {"terraform": 0, "cli": 1, "console": 2}
_EFFORT_VALUES = {"minutes", "hours", "days"}
_IAC_VALUES = {"terraform", "cli", "console"}


def _build_remediation_prompt(
    title: str,
    description: str | None,
    resource_type: str | None,
    remediation_hint: str | None,
    root_cause: str | None,
    compliance_frameworks: list,
) -> str:
    rc_ctx = f"\nRoot Cause: {root_cause}" if root_cause else ""
    hint_ctx = f"\nExisting Remediation Hint: {remediation_hint}" if remediation_hint else ""
    frameworks = ", ".join(compliance_frameworks[:5]) if compliance_frameworks else "None"

    return (
        "You are a cloud security remediation engineer. Generate a step-by-step remediation plan "
        "for the following AWS security finding. Prefer Terraform steps over AWS CLI over Console.\n\n"
        "Return a JSON object with EXACTLY these keys:\n"
        '- "steps": array of objects, each with: step (int), action (str, short label), '
        'command (str, exact command or HCL block), iac_type ("terraform"|"cli"|"console")\n'
        '- "estimated_effort": one of: "minutes"|"hours"|"days"\n'
        '- "auto_remediatable": true if this can be scripted without human judgment, false otherwise\n\n'
        f"Finding: {title}\n"
        f"Resource Type: {resource_type or 'Unknown'}\n"
        f"Description: {(description or '')[:600]}\n"
        f"Compliance Frameworks: {frameworks}"
        f"{rc_ctx}{hint_ctx}\n\n"
        "Provide 3-6 concrete steps. For Terraform, show the resource block. "
        "For CLI, show the exact aws command. Return ONLY valid JSON, no markdown."
    )


def _parse_remediation_response(raw: dict, model_used: str) -> tuple[dict, str]:
    raw_steps = raw.get("steps", [])
    steps = []
    for i, s in enumerate(raw_steps[:10]):
        if not isinstance(s, dict):
            continue
        iac_type = s.get("iac_type", "console")
        if iac_type not in _IAC_VALUES:
            iac_type = "console"
        steps.append({
            "step": int(s.get("step", i + 1)),
            "action": str(s.get("action", ""))[:200],
            "command": str(s.get("command", ""))[:1000],
            "iac_type": iac_type,
        })

    # Sort: terraform → cli → console
    steps.sort(key=lambda s: (_IAC_PRIORITY.get(s["iac_type"], 3), s["step"]))
    # Re-number after sort
    for idx, s in enumerate(steps, 1):
        s["step"] = idx

    effort = raw.get("estimated_effort", "hours")
    if effort not in _EFFORT_VALUES:
        effort = "hours"

    return {
        "steps": steps,
        "estimated_effort": effort,
        "auto_remediatable": bool(raw.get("auto_remediatable", False)),
        "fallback_used": False,
    }, model_used


def _fallback_output(title: str, resource_type: str | None) -> dict:
    rt = resource_type or "resource"
    return {
        "steps": [
            {
                "step": 1,
                "action": "Review finding in AWS Console",
                "command": f"Navigate to AWS Console → {rt} → Review security configuration",
                "iac_type": "console",
            },
            {
                "step": 2,
                "action": "Apply recommended fix",
                "command": "Apply the remediation guidance from the finding description",
                "iac_type": "console",
            },
        ],
        "estimated_effort": "hours",
        "auto_remediatable": False,
        "fallback_used": True,
    }


class RemediationPlannerAgent(BaseAgent):
    """
    Generates IaC remediation steps for a security finding.
    Prefers Claude Haiku for code quality; falls back to Ollama llama3.
    Loads root cause analysis if available for enriched context.
    """
    agent_name = "remediation_plan"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._finding_repo = CanonicalFindingRepository(db)

    async def _run(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> tuple[dict, str]:
        from app.core.exceptions import NotFoundError

        finding = await self._finding_repo.get_by_id_and_workspace(finding_id, workspace_id)
        if finding is None:
            raise NotFoundError(f"Finding {finding_id} not found in workspace {workspace_id}")

        # Load root cause if available (enrichment context only — no auto-chain)
        root_cause_text: str | None = None
        rc_result = await self.db.execute(
            select(AgentResult)
            .where(
                AgentResult.finding_id == finding_id,
                AgentResult.workspace_id == workspace_id,
                AgentResult.agent_name == "root_cause",
                AgentResult.status == "completed",
            )
            .order_by(AgentResult.created_at.desc())
            .limit(1)
        )
        rc_row = rc_result.scalar_one_or_none()
        if rc_row:
            root_cause_text = rc_row.output.get("root_cause")

        prompt = _build_remediation_prompt(
            title=finding.title,
            description=finding.description,
            resource_type=finding.resource_type,
            remediation_hint=finding.remediation,
            root_cause=root_cause_text,
            compliance_frameworks=list(finding.compliance_frameworks or []),
        )

        anthropic_key = getattr(settings, "anthropic_api_key", "")

        # Try Claude Haiku first (better code gen), then Ollama
        if anthropic_key:
            result, model_used = await self._call_claude(prompt, anthropic_key)
            if result is not None:
                return result, model_used

        return await self._call_ollama(prompt)

    async def _call_claude(self, prompt: str, api_key: str) -> tuple[dict | None, str]:
        try:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=api_key)
            message = await client.messages.create(
                model="claude-haiku-20240307",
                max_tokens=1024,
                system=(
                    "You are a senior cloud security engineer. Generate precise IaC remediation steps. "
                    "Return ONLY valid JSON. No markdown, no preamble."
                ),
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = message.content[0].text.strip()
            if raw_text.startswith("```"):
                raw_text = "\n".join(l for l in raw_text.splitlines() if not l.startswith("```")).strip()
            raw = json.loads(raw_text)
            output, model_used = _parse_remediation_response(raw, "claude-haiku-20240307")
            return output, model_used
        except Exception as exc:
            logger.warning("remediation_agent.claude_error", error=str(exc))
            return None, "claude-haiku-20240307"

    async def _call_ollama(self, prompt: str) -> tuple[dict, str]:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    "http://localhost:11434/api/generate",
                    json={"model": "llama3", "prompt": prompt, "stream": False, "format": "json"},
                )
                resp.raise_for_status()
                data = resp.json()
                raw_str = data.get("response", "{}")
                raw = json.loads(raw_str) if isinstance(raw_str, str) else raw_str
                output, model_used = _parse_remediation_response(raw, "ollama/llama3")
                return output, model_used
        except Exception as exc:
            logger.warning("remediation_agent.ollama_error", error=str(exc))
            return _fallback_output(prompt[:60], None), "ollama/llama3"
