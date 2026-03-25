"""
TriageAgent — AI-powered finding severity triage.

Routes to Ollama llama3 (fast, private) or Claude Haiku (complex reasoning)
based on finding description length and risk score.

Routing rule:
  description > 500 chars OR risk_score > 7.0  →  Claude Haiku
  else                                           →  Ollama llama3

Extends BaseAgent: timing, audit logging, and result persistence are inherited.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.services.agents.base_agent import BaseAgent
from app.services.agents.llm_router import LLMRouter


class TriageAgent(BaseAgent):
    """
    Analyzes a CanonicalFinding and produces:
      - suggested_severity
      - confidence (0.0–1.0)
      - rationale (natural language explanation)
      - mitre_tactics (list of MITRE ATT&CK tactics)
      - fallback_used (True if LLM was unavailable)
    """
    agent_name = "triage"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._finding_repo = CanonicalFindingRepository(db)
        self._router = LLMRouter(
            ollama_base_url=getattr(settings, "ollama_base_url", "http://localhost:11434"),
            anthropic_api_key=getattr(settings, "anthropic_api_key", ""),
        )

    async def _run(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> tuple[dict, str]:
        """
        Load the finding, run LLM triage, return (output_dict, model_used).

        Output shape:
        {
            "suggested_severity": str,    # critical|high|medium|low|info
            "confidence": float,          # 0.0–1.0
            "rationale": str,
            "mitre_tactics": list[str],
            "fallback_used": bool,
        }
        """
        from app.core.exceptions import NotFoundError

        # Load and validate finding
        finding = await self._finding_repo.get_by_id_and_workspace(finding_id, workspace_id)
        if finding is None:
            raise NotFoundError(
                f"Finding {finding_id} not found in workspace {workspace_id}"
            )

        # Route to appropriate LLM
        decision = await self._router.triage(
            title=finding.title,
            description=finding.description,
            severity=str(finding.severity.value if hasattr(finding.severity, 'value') else finding.severity),
            resource_type=finding.resource_type,
            risk_score=finding.risk_score,
        )

        output = {
            "suggested_severity": decision.suggested_severity,
            "confidence": decision.confidence,
            "rationale": decision.rationale,
            "mitre_tactics": decision.mitre_tactics,
            "fallback_used": decision.fallback_used,
            "original_severity": str(finding.severity.value if hasattr(finding.severity, 'value') else finding.severity),
        }
        return output, decision.model_used
