"""
LLMRouter — routes a triage request to Ollama llama3 or Claude Haiku
based on finding complexity and risk.

Routing rules (Sprint 18):
  IF description_len > 500 OR risk_score > 7.0  →  Claude Haiku (complex reasoning)
  ELSE                                            →  Ollama llama3 (fast, private)

Falls back gracefully if either provider is unavailable — never raises.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Model identifiers ─────────────────────────────────────────────────────────

OLLAMA_MODEL = "llama3"
CLAUDE_HAIKU_MODEL = "claude-haiku-20240307"

# Cloud-relevant MITRE ATT&CK tactics (constrained list prevents hallucination)
_MITRE_CLOUD_TACTICS = [
    "Initial Access", "Execution", "Persistence", "Privilege Escalation",
    "Defense Evasion", "Credential Access", "Discovery", "Lateral Movement",
    "Collection", "Exfiltration", "Impact", "Resource Development",
]


@dataclass
class TriageDecision:
    suggested_severity: str        # critical | high | medium | low | info
    confidence: float              # 0.0–1.0
    rationale: str
    mitre_tactics: list[str] = field(default_factory=list)
    model_used: str = "unknown"
    fallback_used: bool = False


# ── Pure routing predicate (testable without mocking) ────────────────────────

def _should_use_claude(description: str | None, risk_score: float | None) -> bool:
    """True → Claude Haiku, False → Ollama llama3."""
    return len(description or "") > 500 or (risk_score or 0.0) > 7.0


def _build_triage_prompt(
    title: str,
    description: str | None,
    severity: str,
    resource_type: str | None,
    risk_score: float | None,
) -> str:
    return (
        "You are a cloud security triage analyst. Analyze the following AWS security finding "
        "and classify its severity and associated MITRE ATT&CK tactics.\n\n"
        "Return a JSON object with EXACTLY these keys:\n"
        '- "suggested_severity": one of critical|high|medium|low|info\n'
        '- "confidence": float 0.0-1.0 representing your confidence\n'
        '- "rationale": 2-3 sentence explanation of your severity decision\n'
        f'- "mitre_tactics": list of applicable MITRE tactics from: {_MITRE_CLOUD_TACTICS}\n\n'
        f"Finding Title: {title}\n"
        f"Current Severity: {severity}\n"
        f"Resource Type: {resource_type or 'Unknown'}\n"
        f"Risk Score: {risk_score or 'N/A'}\n"
        f"Description: {(description or '')[:1000]}\n\n"
        "Return ONLY valid JSON, no markdown, no explanation outside the JSON."
    )


def _parse_triage_response(raw: dict, model_used: str) -> TriageDecision:
    """Parse raw LLM dict → TriageDecision. Defensive on missing/invalid keys."""
    sev = raw.get("suggested_severity", "medium")
    if sev not in {"critical", "high", "medium", "low", "info"}:
        sev = "medium"

    confidence = raw.get("confidence", 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    tactics = raw.get("mitre_tactics", [])
    if not isinstance(tactics, list):
        tactics = []

    return TriageDecision(
        suggested_severity=sev,
        confidence=confidence,
        rationale=raw.get("rationale", "No rationale provided."),
        mitre_tactics=[t for t in tactics if t in _MITRE_CLOUD_TACTICS],
        model_used=model_used,
        fallback_used=False,
    )


def _fallback_decision(model_used: str, reason: str) -> TriageDecision:
    return TriageDecision(
        suggested_severity="medium",
        confidence=0.0,
        rationale=f"AI triage unavailable: {reason}. Manual review recommended.",
        mitre_tactics=[],
        model_used=model_used,
        fallback_used=True,
    )


class LLMRouter:
    """
    Routes triage requests to the appropriate LLM.
    Stateless — safe to share as a singleton or create per-request.
    """

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        anthropic_api_key: str = "",
    ) -> None:
        self._ollama_url = ollama_base_url
        self._anthropic_key = anthropic_api_key

    async def triage(
        self,
        title: str,
        description: str | None,
        severity: str,
        resource_type: str | None,
        risk_score: float | None,
    ) -> TriageDecision:
        """
        Route to the correct LLM and return a TriageDecision.
        Never raises — returns a fallback decision on any error.
        """
        use_claude = _should_use_claude(description, risk_score)
        prompt = _build_triage_prompt(title, description, severity, resource_type, risk_score)

        if use_claude and self._anthropic_key:
            return await self._call_claude(prompt)
        else:
            return await self._call_ollama(prompt)

    async def _call_ollama(self, prompt: str) -> TriageDecision:
        """Call Ollama llama3 with JSON format mode."""
        import httpx
        model_id = f"ollama/{OLLAMA_MODEL}"
        try:
            async with httpx.AsyncClient(timeout=90.0) as client:
                resp = await client.post(
                    f"{self._ollama_url}/api/generate",
                    json={
                        "model": OLLAMA_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                raw_str = data.get("response", "{}")
                # response field is a JSON string when format="json"
                raw = json.loads(raw_str) if isinstance(raw_str, str) else raw_str
                return _parse_triage_response(raw, model_id)
        except Exception as exc:
            logger.warning("LLMRouter.ollama_error: %s", exc)
            return _fallback_decision(model_id, f"Ollama error: {type(exc).__name__}")

    async def _call_claude(self, prompt: str) -> TriageDecision:
        """Call Claude Haiku. Falls back to Ollama on any error."""
        import anthropic  # lazy import — only when Claude path is active
        model_id = CLAUDE_HAIKU_MODEL
        system = (
            "You are a senior cloud security analyst performing automated triage. "
            "Always respond with valid JSON only. Never add commentary outside the JSON object."
        )
        try:
            client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
            message = await client.messages.create(
                model=CLAUDE_HAIKU_MODEL,
                max_tokens=512,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = message.content[0].text.strip()
            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                lines = [l for l in raw_text.splitlines() if not l.startswith("```")]
                raw_text = "\n".join(lines).strip()
            raw = json.loads(raw_text)
            return _parse_triage_response(raw, model_id)
        except Exception as exc:
            logger.warning("LLMRouter.claude_error: %s — falling back to Ollama", exc)
            # Fall back to Ollama on Claude failure
            return await self._call_ollama(prompt)
