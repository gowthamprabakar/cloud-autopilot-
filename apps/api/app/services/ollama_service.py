"""
OllamaService — async HTTP client for the local Ollama inference server.

Design principles:
- Never fail silently. If Ollama is unavailable every public method returns
  a usable template-based result rather than None or an empty dict.
- All JSON parsing is defensive — a raw string response is wrapped so callers
  always get a structured object.
- The service is stateless: instantiate once per request or share as a
  singleton; the underlying httpx.AsyncClient handles connection pooling.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)


# ── Output dataclasses (lightweight — no ORM dependency) ─────────────────────

@dataclass
class DescriptiveOutput:
    what_is_it: str
    current_state: str
    expected_state: str
    business_impact: str
    attack_scenario: str
    fallback_used: bool = False


@dataclass
class RCANarrative:
    root_cause_title: str
    root_cause_explanation: str
    contributing_factors: list[str]
    governance_gaps: list[str]
    remediation_summary: str
    fallback_used: bool = False


@dataclass
class RecommendationOutput:
    summary: str
    immediate_steps: list[str]
    sprint_steps: list[str]
    long_term_steps: list[str]
    estimated_effort: str
    fallback_used: bool = False


# ── Service ───────────────────────────────────────────────────────────────────

class OllamaService:
    """
    Async wrapper around the Ollama REST API.

    All generate_* methods are safe to call even when Ollama is not running —
    they return template-based fallback objects and log a warning.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    # ── HTTP client lifecycle ─────────────────────────────────────────────────

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── Core generate call ────────────────────────────────────────────────────

    async def generate(
        self,
        prompt: str,
        system: str | None = None,
        fmt: str = "json",
    ) -> dict:
        """
        Call POST /api/generate on Ollama.

        Returns a dict. On any error returns {"error": "<message>"} so callers
        can detect failure without raising exceptions.
        """
        payload: dict = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if fmt == "json":
            payload["format"] = "json"

        try:
            client = self._get_client()
            resp = await client.post("/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_response = data.get("response", "{}")
            # Ollama returns the model output as a JSON string inside "response"
            if isinstance(raw_response, str):
                try:
                    return json.loads(raw_response)
                except json.JSONDecodeError:
                    # Model returned prose instead of JSON — wrap it
                    return {"raw": raw_response}
            return raw_response
        except httpx.ConnectError:
            logger.warning("ollama_unavailable base_url=%s", self.base_url)
            return {"error": "Ollama not available"}
        except httpx.TimeoutException:
            logger.warning("ollama_timeout model=%s", self.model)
            return {"error": "Ollama timeout"}
        except Exception as exc:
            logger.exception("ollama_generate_error: %s", exc)
            return {"error": str(exc)}

    # ── Health / discovery ────────────────────────────────────────────────────

    async def is_available(self) -> bool:
        """Return True if Ollama is reachable and responding."""
        try:
            client = self._get_client()
            resp = await client.get("/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """Return list of locally available model names."""
        try:
            client = self._get_client()
            resp = await client.get("/api/tags", timeout=5.0)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("models", [])
            return [m.get("name", "") for m in models if m.get("name")]
        except Exception:
            return []

    # ── Descriptive analysis ──────────────────────────────────────────────────

    async def generate_descriptive_analysis(
        self, finding_context: dict
    ) -> DescriptiveOutput:
        """
        Ask Ollama to describe a security finding in plain English across 5 dimensions.
        Falls back to template rendering when Ollama is unavailable.
        """
        title = finding_context.get("title", "Security Finding")
        resource_type = finding_context.get("resource_type", "AWS Resource")
        severity = finding_context.get("severity", "medium")
        description = finding_context.get("description", "")
        resource_arn = finding_context.get("resource_arn", "")

        prompt = (
            "You are a cloud security expert. Analyze the following AWS security finding "
            "and return a JSON object with EXACTLY these 5 keys:\n"
            "- what_is_it: plain English explanation (2-3 sentences, non-technical, "
            "suitable for a business executive)\n"
            "- current_state: what is happening right now (technical but clear, 1-2 sentences)\n"
            "- expected_state: what the correct/secure configuration should be (1-2 sentences)\n"
            "- business_impact: what could go wrong for the business if not fixed (business language, "
            "mention data breach, compliance fines, reputational damage where relevant)\n"
            "- attack_scenario: how an attacker could exploit this step by step "
            "(numbered list, 3-5 steps)\n\n"
            f"Finding Title: {title}\n"
            f"Resource Type: {resource_type}\n"
            f"Severity: {severity}\n"
            f"Resource ARN: {resource_arn}\n"
            f"Description: {description}\n\n"
            "Return ONLY valid JSON, no markdown, no explanation outside the JSON."
        )

        system = (
            "You are a senior cloud security analyst. Always respond with valid JSON only. "
            "Never include markdown code blocks. Never add commentary outside the JSON object."
        )

        result = await self.generate(prompt, system=system, fmt="json")

        if "error" in result or not result:
            return self._fallback_descriptive(finding_context)

        return DescriptiveOutput(
            what_is_it=result.get(
                "what_is_it",
                self._template_what_is_it(title, resource_type, severity),
            ),
            current_state=result.get(
                "current_state",
                self._template_current_state(title, description),
            ),
            expected_state=result.get(
                "expected_state",
                self._template_expected_state(resource_type),
            ),
            business_impact=result.get(
                "business_impact",
                self._template_business_impact(severity),
            ),
            attack_scenario=result.get(
                "attack_scenario",
                self._template_attack_scenario(resource_type, title),
            ),
            fallback_used=False,
        )

    # ── RCA narrative ─────────────────────────────────────────────────────────

    async def generate_rca_narrative(
        self, rca_factors: dict, graph_context: dict
    ) -> RCANarrative:
        """
        Ask Ollama to explain WHY this misconfiguration exists — not just the symptom.
        Falls back to template when Ollama is unavailable.
        """
        primary_cause = rca_factors.get("primary_root_cause", "misconfiguration")
        composite_score = rca_factors.get("composite_score", 0.5)
        causal_chain = rca_factors.get("causal_chain", [])
        top_factors = rca_factors.get("factors", [])[:3]
        toxic_combos = rca_factors.get("toxic_combinations", [])

        factors_text = "\n".join(
            f"- {f.get('name', 'factor')}: score={f.get('score', 0):.2f}, "
            f"evidence={f.get('evidence', [])}"
            for f in top_factors
        )
        chain_text = " → ".join(causal_chain) if causal_chain else "No chain identified"
        combos_text = (
            "\n".join(f"- {c.get('name', 'combo')}: {c.get('description', '')}" for c in toxic_combos)
            if toxic_combos
            else "None detected"
        )

        prompt = (
            "You are a cloud security root-cause analyst. Given the multi-factor security "
            "analysis below, explain the ROOT CAUSE — not just the symptom. Focus on WHY "
            "the misconfiguration exists: missing governance, IaC drift, no SCP enforcement, "
            "manual changes bypassing automation, missing guardrails, etc.\n\n"
            "Return a JSON object with these exact keys:\n"
            "- root_cause_title: one-line title (10 words max)\n"
            "- root_cause_explanation: 3-4 sentences explaining the underlying cause\n"
            "- contributing_factors: list of 3-5 contributing factors (strings)\n"
            "- governance_gaps: list of 2-3 governance or process gaps identified\n"
            "- remediation_summary: 2-3 sentences on what needs to change structurally\n\n"
            f"Primary Root Cause Category: {primary_cause}\n"
            f"Composite Risk Score: {composite_score:.2f}/1.0\n"
            f"Causal Chain: {chain_text}\n"
            f"Top Contributing Factors:\n{factors_text}\n"
            f"Toxic Combinations:\n{combos_text}\n\n"
            "Return ONLY valid JSON."
        )

        system = (
            "You are a senior security architect performing root cause analysis. "
            "Always respond with valid JSON only. Never add commentary outside the JSON."
        )

        result = await self.generate(prompt, system=system, fmt="json")

        if "error" in result or not result:
            return self._fallback_rca(rca_factors)

        return RCANarrative(
            root_cause_title=result.get(
                "root_cause_title",
                f"Root cause: {primary_cause.replace('_', ' ').title()}",
            ),
            root_cause_explanation=result.get(
                "root_cause_explanation",
                f"The primary driver is classified as {primary_cause} with a "
                f"composite risk score of {composite_score:.2f}.",
            ),
            contributing_factors=result.get("contributing_factors", []),
            governance_gaps=result.get("governance_gaps", []),
            remediation_summary=result.get(
                "remediation_summary",
                "Immediate remediation and process review required.",
            ),
            fallback_used=False,
        )

    # ── Recommendations ───────────────────────────────────────────────────────

    async def generate_recommendations(
        self, rca: dict, rag_score: str
    ) -> RecommendationOutput:
        """
        Produce prioritised remediation recommendations aligned with RAG level.
        Falls back to template when Ollama is unavailable.
        """
        primary_cause = rca.get("primary_root_cause", "misconfiguration")
        resource_type = rca.get("resource_type", "AWS resource")
        causal_chain = rca.get("causal_chain", [])
        rag_label = rag_score.upper()

        sla_map = {"RED": "within 24 hours", "AMBER": "within 7 days (this sprint)", "GREEN": "within 90 days (this quarter)"}
        sla_text = sla_map.get(rag_label, "as soon as possible")

        prompt = (
            "You are a cloud security remediation expert. Based on the analysis below, "
            "generate prioritised remediation recommendations.\n\n"
            "Return a JSON object with these exact keys:\n"
            "- summary: 2 sentences describing the overall remediation approach\n"
            f"- immediate_steps: list of actions to take {sla_text} (3-5 items, RED priority)\n"
            "- sprint_steps: list of actions to take this sprint/week (3-5 items, AMBER priority)\n"
            "- long_term_steps: list of structural improvements for this quarter (2-4 items, GREEN priority)\n"
            "- estimated_effort: overall effort estimate (e.g. '2-4 hours', '1-2 days')\n\n"
            f"RAG Priority Level: {rag_label}\n"
            f"Primary Root Cause: {primary_cause}\n"
            f"Affected Resource Type: {resource_type}\n"
            f"Causal Chain: {' → '.join(causal_chain) if causal_chain else 'N/A'}\n\n"
            "Return ONLY valid JSON."
        )

        system = (
            "You are a senior cloud security engineer specialising in AWS remediation. "
            "Always respond with valid JSON only."
        )

        result = await self.generate(prompt, system=system, fmt="json")

        if "error" in result or not result:
            return self._fallback_recommendations(primary_cause, rag_label)

        return RecommendationOutput(
            summary=result.get(
                "summary",
                f"Address {primary_cause} with {rag_label} priority.",
            ),
            immediate_steps=result.get("immediate_steps", []),
            sprint_steps=result.get("sprint_steps", []),
            long_term_steps=result.get("long_term_steps", []),
            estimated_effort=result.get("estimated_effort", "Unknown"),
            fallback_used=False,
        )

    # ── Template fallbacks (never return empty data) ─────────────────────────

    def _fallback_descriptive(self, ctx: dict) -> DescriptiveOutput:
        title = ctx.get("title", "Security Finding")
        resource_type = ctx.get("resource_type", "AWS Resource")
        severity = ctx.get("severity", "medium")
        description = ctx.get("description", "")
        return DescriptiveOutput(
            what_is_it=self._template_what_is_it(title, resource_type, severity),
            current_state=self._template_current_state(title, description),
            expected_state=self._template_expected_state(resource_type),
            business_impact=self._template_business_impact(severity),
            attack_scenario=self._template_attack_scenario(resource_type, title),
            fallback_used=True,
        )

    def _fallback_rca(self, rca_factors: dict) -> RCANarrative:
        cause = rca_factors.get("primary_root_cause", "misconfiguration")
        score = rca_factors.get("composite_score", 0.5)
        factors = [f.get("name", "factor") for f in rca_factors.get("factors", [])[:3]]
        return RCANarrative(
            root_cause_title=f"Root cause: {cause.replace('_', ' ').title()}",
            root_cause_explanation=(
                f"Analysis identified {cause} as the primary root cause with a "
                f"composite risk score of {score:.2f}. This likely results from "
                f"missing governance controls or configuration drift in the environment."
            ),
            contributing_factors=factors or ["Missing security controls", "Configuration drift"],
            governance_gaps=[
                "No automated compliance enforcement detected",
                "Manual configuration changes may be bypassing IaC pipelines",
            ],
            remediation_summary=(
                "Implement automated guardrails and review IaC templates to prevent recurrence. "
                "Prioritise remediation based on the RAG level assigned to this finding."
            ),
            fallback_used=True,
        )

    def _fallback_recommendations(self, cause: str, rag: str) -> RecommendationOutput:
        return RecommendationOutput(
            summary=(
                f"Remediate this {cause} finding with {rag} priority. "
                "Follow the specific actions below aligned to your remediation SLA."
            ),
            immediate_steps=[
                "Review the affected resource configuration immediately",
                "Restrict access to the minimum required permissions",
                "Enable CloudTrail logging if not already active",
            ],
            sprint_steps=[
                "Update IaC templates (Terraform/CloudFormation) to encode the secure configuration",
                "Add automated compliance checks to CI/CD pipeline",
                "Review similar resources in the same region for the same misconfiguration",
            ],
            long_term_steps=[
                "Implement AWS Config Rules to continuously evaluate this control",
                "Enable AWS Security Hub with the relevant compliance standard",
            ],
            estimated_effort="2-8 hours",
            fallback_used=True,
        )

    # ── Template helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _template_what_is_it(title: str, resource_type: str, severity: str) -> str:
        return (
            f"This is a {severity}-severity security finding affecting a {resource_type} resource. "
            f"The issue was identified as: {title}. "
            "If left unaddressed, this configuration weakness could expose the environment "
            "to unauthorised access or data exposure."
        )

    @staticmethod
    def _template_current_state(title: str, description: str) -> str:
        if description:
            return f"{title}. {description[:300]}"
        return f"The resource is currently in a non-compliant state: {title}."

    @staticmethod
    def _template_expected_state(resource_type: str) -> str:
        defaults: dict[str, str] = {
            "S3": "The S3 bucket should have public access blocked, server-side encryption enabled, "
                  "and access logging turned on.",
            "IAM": "IAM principals should follow least-privilege principles with MFA enforced, "
                   "no wildcard permissions, and permission boundaries applied.",
            "EC2": "EC2 instances should reside in private subnets, have no public IPs unless required, "
                   "and be protected by restrictive security groups.",
            "RDS": "RDS instances should be in private subnets, encrypted at rest, "
                   "and not publicly accessible.",
            "SecurityGroup": "Security groups should restrict inbound traffic to known CIDR ranges "
                             "on required ports only — never 0.0.0.0/0 for sensitive ports.",
        }
        for key, text in defaults.items():
            if key.lower() in (resource_type or "").lower():
                return text
        return (
            f"The {resource_type} resource should be configured according to AWS security best practices "
            "with least-privilege access, encryption enabled, and appropriate network restrictions."
        )

    @staticmethod
    def _template_business_impact(severity: str) -> str:
        impacts: dict[str, str] = {
            "critical": (
                "A critical vulnerability of this type could result in complete account compromise, "
                "large-scale data exfiltration, regulatory fines (GDPR, HIPAA, PCI-DSS), "
                "and severe reputational damage. Immediate remediation is essential."
            ),
            "high": (
                "This high-severity issue could lead to unauthorised data access, lateral movement "
                "through the environment, and significant compliance violations with associated fines."
            ),
            "medium": (
                "If exploited, this medium-severity finding could expose sensitive data or allow "
                "privilege escalation. Addressing this within the current sprint reduces overall risk posture."
            ),
            "low": (
                "This low-severity finding represents a compliance gap or theoretical risk. "
                "Addressing it will improve security posture and audit readiness."
            ),
        }
        return impacts.get(
            severity.lower(),
            "This finding should be reviewed and remediated to maintain a strong security posture.",
        )

    @staticmethod
    def _template_attack_scenario(resource_type: str, title: str) -> str:
        return (
            f"1. Attacker discovers the misconfigured {resource_type} resource via automated scanning "
            f"(e.g., Shodan, AWS API enumeration).\n"
            f"2. Attacker exploits the weakness identified in: {title}.\n"
            f"3. Initial access is established to the affected resource.\n"
            f"4. Attacker moves laterally to connected resources using the compromised credentials or network path.\n"
            f"5. Data is exfiltrated or the attacker establishes persistence for long-term access."
        )
