"""
RootCauseAnalyzerAgent — THINK layer agent.

Identifies the root cause of a finding using:
  - Finding metadata (title, description, resource_type, risk_score, compliance_frameworks)
  - Triage result (auto-runs TriageAgent if not yet completed)
  - Ollama llama3 for structured root cause analysis

Output shape:
  {
    root_cause: str,
    contributing_factors: list[str],
    misconfiguration_type: str,
    affected_blast_radius: int,
    remediation_priority: "immediate"|"high"|"medium"|"low",
    fallback_used: bool,
  }
"""

import json
import uuid

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_result import AgentResult
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.services.agents.base_agent import BaseAgent

logger = structlog.get_logger(__name__)

_OLLAMA_URL = "http://localhost:11434"
_PRIORITY_VALUES = {"immediate", "high", "medium", "low"}


def _build_root_cause_prompt(
    title: str,
    description: str | None,
    resource_type: str | None,
    risk_score: float | None,
    compliance_frameworks: list,
    region: str | None,
    triage_severity: str | None,
    triage_rationale: str | None,
) -> str:
    triage_ctx = ""
    if triage_severity:
        triage_ctx = (
            f"\nAI Triage Result: severity={triage_severity}"
            + (f", rationale={triage_rationale}" if triage_rationale else "")
        )
    frameworks = ", ".join(compliance_frameworks[:5]) if compliance_frameworks else "None"

    return (
        "You are a cloud security root cause analyst. Analyze the following AWS security finding "
        "and identify its root cause.\n\n"
        "Return a JSON object with EXACTLY these keys:\n"
        '- "root_cause": 2-3 sentence explanation of WHY this vulnerability exists\n'
        '- "contributing_factors": list of 2-5 short strings (e.g. "Missing IAM boundary")\n'
        '- "misconfiguration_type": one of: IAM|Network|Encryption|Logging|Patching|Configuration|Data|Other\n'
        '- "affected_blast_radius": estimated number of additional resources at risk (integer 0-100)\n'
        '- "remediation_priority": one of: immediate|high|medium|low\n\n'
        f"Finding: {title}\n"
        f"Description: {(description or '')[:800]}\n"
        f"Resource Type: {resource_type or 'Unknown'}\n"
        f"Risk Score: {risk_score or 'N/A'}\n"
        f"Region: {region or 'Unknown'}\n"
        f"Compliance Frameworks: {frameworks}"
        f"{triage_ctx}\n\n"
        "Return ONLY valid JSON, no markdown."
    )


def _parse_root_cause_response(raw: dict) -> dict:
    priority = raw.get("remediation_priority", "medium")
    if priority not in _PRIORITY_VALUES:
        priority = "medium"

    blast_radius = raw.get("affected_blast_radius", 0)
    try:
        blast_radius = max(0, int(blast_radius))
    except (TypeError, ValueError):
        blast_radius = 0

    factors = raw.get("contributing_factors", [])
    if not isinstance(factors, list):
        factors = []

    return {
        "root_cause": raw.get("root_cause", "Root cause could not be determined."),
        "contributing_factors": factors[:8],
        "misconfiguration_type": raw.get("misconfiguration_type", "Other"),
        "affected_blast_radius": blast_radius,
        "remediation_priority": priority,
        "fallback_used": False,
    }


def _fallback_output(title: str, risk_score: float | None) -> dict:
    priority = "immediate" if (risk_score or 0) >= 9 else "high" if (risk_score or 0) >= 7 else "medium"
    return {
        "root_cause": f"Automated root cause analysis unavailable for: {title}. Manual review required.",
        "contributing_factors": ["LLM unavailable — manual analysis needed"],
        "misconfiguration_type": "Other",
        "affected_blast_radius": 0,
        "remediation_priority": priority,
        "fallback_used": True,
    }


class RootCauseAnalyzerAgent(BaseAgent):
    """
    Analyzes the root cause of a security finding.
    Auto-runs TriageAgent first if no triage result exists.
    Uses Ollama llama3 for structured analysis.
    """
    agent_name = "root_cause"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._finding_repo = CanonicalFindingRepository(db)

    async def _run(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> tuple[dict, str]:
        from app.core.exceptions import NotFoundError

        # Load finding
        finding = await self._finding_repo.get_by_id_and_workspace(finding_id, workspace_id)
        if finding is None:
            raise NotFoundError(f"Finding {finding_id} not found in workspace {workspace_id}")

        # Load most recent triage result (auto-run if missing)
        triage_severity: str | None = None
        triage_rationale: str | None = None

        triage_result = await self.db.execute(
            select(AgentResult)
            .where(
                AgentResult.finding_id == finding_id,
                AgentResult.workspace_id == workspace_id,
                AgentResult.agent_name == "triage",
                AgentResult.status == "completed",
            )
            .order_by(AgentResult.created_at.desc())
            .limit(1)
        )
        triage_row = triage_result.scalar_one_or_none()

        if triage_row is None:
            # Auto-chain: run triage first
            logger.info("root_cause.auto_triage", finding_id=str(finding_id))
            from app.services.agents.triage_agent import TriageAgent
            triage_agent_result = await TriageAgent(self.db).execute(
                finding_id=finding_id,
                workspace_id=workspace_id,
                triggered_by="root_cause_agent",
            )
            if triage_agent_result.status == "completed":
                triage_severity = triage_agent_result.output.get("suggested_severity")
                triage_rationale = triage_agent_result.output.get("rationale")
        else:
            triage_severity = triage_row.output.get("suggested_severity")
            triage_rationale = triage_row.output.get("rationale")

        # Build prompt and call Ollama
        prompt = _build_root_cause_prompt(
            title=finding.title,
            description=finding.description,
            resource_type=finding.resource_type,
            risk_score=finding.risk_score,
            compliance_frameworks=list(finding.compliance_frameworks or []),
            region=finding.region,
            triage_severity=triage_severity,
            triage_rationale=triage_rationale,
        )

        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{_OLLAMA_URL}/api/generate",
                    json={"model": "llama3", "prompt": prompt, "stream": False, "format": "json"},
                )
                resp.raise_for_status()
                data = resp.json()
                raw_str = data.get("response", "{}")
                raw = json.loads(raw_str) if isinstance(raw_str, str) else raw_str
                output = _parse_root_cause_response(raw)
        except Exception as exc:
            logger.warning("root_cause_agent.ollama_error", error=str(exc))
            output = _fallback_output(finding.title, finding.risk_score)

        return output, "ollama/llama3"
