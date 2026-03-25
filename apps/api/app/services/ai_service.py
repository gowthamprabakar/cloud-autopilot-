"""
AI Service — Cloud Posture Copilot AI Safe Layer.

Design invariants:
1. AI is AUGMENTATION ONLY. It never writes risk_score, severity, or
   compliance_frameworks on any canonical finding.
2. Only whitelisted prompt templates (PROMPT_REGISTRY) are executed.
3. All Anthropic calls are gated by settings.ai_enabled. When disabled,
   a clearly-labelled stub is returned so the UI works without API keys.
4. Idempotency: if an insight with the same (finding_id, prompt_template_id,
   input_context_hash) already exists and is completed, it is returned
   without calling the API again.
5. Structured JSON output is always parsed and validated before storage.
   A parse failure falls back to returning the raw text as the summary.
"""

import hashlib
import json
import uuid
from typing import Any

import structlog

from app.core.config import settings
from app.models.ai_feedback import AiFeedback
from app.models.ai_insight import AiInsight
from app.repositories.ai_feedback_repository import AiFeedbackRepository
from app.repositories.ai_insight_repository import AiInsightRepository
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.schemas.ai import AiFeedbackRequest
from app.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


# ── Prompt Registry ────────────────────────────────────────────────────────────
# Only keys in this dict may be used — prevents prompt injection.

PROMPT_REGISTRY: dict[str, dict[str, Any]] = {
    "finding_summary_v1": {
        "description": "Plain-English summary + top 3 remediation actions for a security finding",
        "system": (
            "You are a senior cloud security analyst. Your role is to help security "
            "engineers quickly understand and act on AWS security findings. "
            "You provide clear, concise, actionable summaries. "
            "You NEVER make up CVE IDs, account numbers, or resource ARNs. "
            "You NEVER assign or modify severity levels or risk scores — those are "
            "determined by authoritative backend systems. "
            "Always respond with valid JSON only, no prose outside the JSON object."
        ),
        "user_template": (
            "Summarize the following AWS security finding in plain English for a "
            "security engineer. Focus on: what is the issue, why it matters, and "
            "the top remediation steps.\n\n"
            "Finding details:\n{finding_context}\n\n"
            "Respond with a JSON object matching this exact schema:\n"
            '{{\n'
            '  "summary": "<2-3 sentence plain English explanation>",\n'
            '  "suggested_actions": ["<action 1>", "<action 2>", "<action 3>"]\n'
            '}}\n'
            "Do not include any text outside the JSON object."
        ),
        "max_tokens": 512,
    },
}


def _build_finding_context(finding) -> str:
    """Serialize finding fields relevant to the AI prompt."""
    parts = [
        f"Title: {finding.title}",
        f"Severity: {finding.severity}",
        f"Source: {finding.primary_source}",
    ]
    if finding.description:
        parts.append(f"Description: {finding.description}")
    if finding.resource_type:
        parts.append(f"Resource type: {finding.resource_type}")
    if finding.region:
        parts.append(f"Region: {finding.region}")
    if finding.remediation:
        parts.append(f"Existing remediation guidance: {finding.remediation}")
    if finding.compliance_frameworks:
        parts.append(f"Compliance frameworks: {', '.join(finding.compliance_frameworks)}")
    return "\n".join(parts)


def _hash_context(context: str) -> str:
    return hashlib.sha256(context.encode()).hexdigest()


def _stub_insight_data(finding_title: str) -> dict[str, Any]:
    """Return a clearly-labelled stub when ai_enabled=False."""
    return {
        "summary": (
            f"[AI Disabled] This is a placeholder insight for: {finding_title}. "
            "Enable AI in settings (AI_ENABLED=true + ANTHROPIC_API_KEY) to generate "
            "real AI-powered summaries."
        ),
        "suggested_actions": [
            "Review the finding details and remediation guidance above.",
            "Check your AWS console for the affected resource.",
            "Enable AI insights by setting ANTHROPIC_API_KEY in your environment.",
        ],
    }


class AiService:
    def __init__(
        self,
        insight_repo: AiInsightRepository,
        feedback_repo: AiFeedbackRepository,
        finding_repo: CanonicalFindingRepository,
    ) -> None:
        self._insight_repo = insight_repo
        self._feedback_repo = feedback_repo
        self._finding_repo = finding_repo

    async def generate_insight(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        prompt_template_id: str = "finding_summary_v1",
    ) -> AiInsight:
        """
        Generate (or return cached) an AI insight for a finding.

        Flow:
          1. Validate prompt_template_id is in PROMPT_REGISTRY.
          2. Load the finding (workspace-scoped).
          3. Build context string + hash.
          4. Check idempotency — return cached if exists.
          5. Create pending insight row.
          6. Generate via Anthropic (or return stub if disabled).
          7. Persist completed/failed state.
        """
        if prompt_template_id not in PROMPT_REGISTRY:
            raise ValidationError(
                f"Unknown prompt template '{prompt_template_id}'. "
                f"Allowed: {list(PROMPT_REGISTRY.keys())}"
            )

        # Load finding (enforces workspace scope via workspace_id check)
        finding = await self._finding_repo.get_by_id(finding_id)
        if finding is None or finding.workspace_id != workspace_id:
            raise NotFoundError(f"Finding {finding_id} not found")

        context_str = _build_finding_context(finding)
        context_hash = _hash_context(
            f"{prompt_template_id}:{context_str}"
        )

        # Idempotency — return existing completed insight
        existing = await self._insight_repo.find_by_hash(
            finding_id=finding_id,
            prompt_template_id=prompt_template_id,
            input_context_hash=context_hash,
        )
        if existing and existing.generation_status == "completed":
            logger.info(
                "ai.insight.cache_hit",
                finding_id=str(finding_id),
                insight_id=str(existing.id),
            )
            return existing

        # Create pending row
        insight = AiInsight(
            workspace_id=workspace_id,
            finding_id=finding_id,
            prompt_template_id=prompt_template_id,
            input_context_hash=context_hash,
            model_id=settings.ai_model,
            generation_status="pending",
        )
        insight = await self._insight_repo.create(insight)

        # Generate
        try:
            if not settings.ai_enabled or not settings.anthropic_api_key:
                data = _stub_insight_data(finding.title)
                raw_response = json.dumps(data)
            else:
                raw_response = await self._call_anthropic(
                    prompt_template_id=prompt_template_id,
                    context_str=context_str,
                )
                data = self._parse_response(raw_response)

            await self._insight_repo.update_completed(
                insight_id=insight.id,
                summary=data["summary"],
                suggested_actions=data.get("suggested_actions", []),
                raw_response=raw_response,
            )
            insight.generation_status = "completed"
            insight.summary = data["summary"]
            insight.suggested_actions = data.get("suggested_actions", [])
            logger.info(
                "ai.insight.generated",
                finding_id=str(finding_id),
                insight_id=str(insight.id),
                stub=not (settings.ai_enabled and settings.anthropic_api_key),
            )
        except Exception as exc:
            error_msg = str(exc)
            await self._insight_repo.update_failed(insight.id, error_msg)
            insight.generation_status = "failed"
            insight.error_message = error_msg
            logger.error(
                "ai.insight.failed",
                finding_id=str(finding_id),
                error=error_msg,
            )

        return insight

    async def get_insight_for_finding(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> AiInsight | None:
        """Get the latest completed insight for a finding."""
        return await self._insight_repo.get_for_finding(finding_id, workspace_id)

    async def submit_feedback(
        self,
        insight_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        req: AiFeedbackRequest,
    ) -> AiFeedback:
        insight = await self._insight_repo.get_by_id(insight_id, workspace_id)
        if insight is None:
            raise NotFoundError(f"Insight {insight_id} not found")

        feedback = AiFeedback(
            workspace_id=workspace_id,
            insight_id=insight_id,
            user_id=user_id,
            verdict=req.verdict,
            edited_text=req.edited_text,
        )
        feedback = await self._feedback_repo.create(feedback)
        logger.info(
            "ai.feedback.submitted",
            insight_id=str(insight_id),
            verdict=req.verdict,
        )
        return feedback

    def list_prompt_templates(self) -> list[dict[str, str]]:
        return [
            {"id": k, "description": v["description"]}
            for k, v in PROMPT_REGISTRY.items()
        ]

    async def _call_anthropic(
        self, prompt_template_id: str, context_str: str
    ) -> str:
        """Call Anthropic API with bounded prompt template."""
        import anthropic  # lazy import — only needed when ai_enabled

        template = PROMPT_REGISTRY[prompt_template_id]
        user_message = template["user_template"].format(
            finding_context=context_str
        )

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        message = await client.messages.create(
            model=settings.ai_model,
            max_tokens=template["max_tokens"],
            system=template["system"],
            messages=[{"role": "user", "content": user_message}],
        )
        return message.content[0].text

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """Parse JSON response; fall back to raw text as summary on failure."""
        raw = raw.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()
        try:
            data = json.loads(raw)
            if not isinstance(data.get("summary"), str):
                raise ValueError("missing 'summary' string")
            if not isinstance(data.get("suggested_actions"), list):
                data["suggested_actions"] = []
            return data
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("ai.response.parse_error", error=str(exc))
            return {
                "summary": raw,
                "suggested_actions": [],
            }
