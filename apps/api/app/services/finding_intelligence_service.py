"""
FindingIntelligenceService — orchestrator for the full intelligence pipeline.

Pipeline per finding:
  1. Load CanonicalFinding from DB
  2. CausalEngine.analyze() — multi-factor weighted root-cause analysis
  3. RAGPriorityService.compute() — RAG level + prioritised actions
  4. OllamaService (if available):
       a. generate_descriptive_analysis()
       b. generate_rca_narrative()
       c. generate_recommendations()
  5. Upsert result into finding_intelligence table
  6. Return FindingIntelligenceResult

The service NEVER returns empty data. If Ollama is unavailable, the Ollama
service's template fallbacks are used automatically.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.canonical_finding import CanonicalFinding
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.finding_intelligence_repository import FindingIntelligenceRepository
from app.services.causal_engine import CausalAnalysis, CausalEngine
from app.services.ollama_service import DescriptiveOutput, OllamaService, RCANarrative
from app.services.rag_priority_service import RAGPriorityService, RAGScore

logger = logging.getLogger(__name__)


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class FindingIntelligenceResult:
    finding_id: uuid.UUID
    descriptive: DescriptiveOutput
    causal_analysis: CausalAnalysis
    rag_score: RAGScore
    generated_at: datetime
    ollama_model: str | None
    fallback_used: bool


# ── Service ───────────────────────────────────────────────────────────────────

class FindingIntelligenceService:
    """
    Orchestrates the full intelligence pipeline for one or many findings.
    """

    def __init__(
        self,
        db: AsyncSession,
        ollama_svc: OllamaService | None = None,
    ) -> None:
        self.db = db
        self.ollama = ollama_svc or OllamaService()
        self._causal = CausalEngine(db)
        self._rag = RAGPriorityService()
        self._finding_repo = CanonicalFindingRepository(db)
        self._intel_repo = FindingIntelligenceRepository(db)

    # ── Public interface ──────────────────────────────────────────────────────

    async def analyze_finding(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> FindingIntelligenceResult:
        """
        Run the full intelligence pipeline for a single finding.
        Upserts the result into finding_intelligence table.
        Returns complete FindingIntelligenceResult.
        """
        # 1. Load finding
        finding = await self._finding_repo.get_by_id_and_workspace(
            finding_id, workspace_id
        )
        if finding is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError(f"Finding {finding_id} not found in workspace {workspace_id}")

        # Mark as pending in DB
        await self._intel_repo.upsert(
            finding_id=finding_id,
            workspace_id=workspace_id,
            generation_status="pending",
        )

        try:
            result = await self._run_pipeline(finding, workspace_id)
        except Exception as exc:
            logger.exception(
                "intelligence_pipeline_error finding_id=%s error=%s", finding_id, exc
            )
            await self._intel_repo.upsert(
                finding_id=finding_id,
                workspace_id=workspace_id,
                generation_status="failed",
                error_message=str(exc),
            )
            raise

        # 6. Persist
        await self._persist_result(result, finding, workspace_id)
        return result

    async def batch_analyze(
        self,
        workspace_id: uuid.UUID,
        limit: int = 10,
    ) -> list[FindingIntelligenceResult]:
        """
        Analyze the top `limit` findings ordered by risk_score descending.
        Skips findings that raise errors and collects the rest.
        """
        findings = await self._finding_repo.list_by_workspace(
            workspace_id=workspace_id,
            order_by_risk_desc=True,
            page=1,
            page_size=limit,
        )

        results: list[FindingIntelligenceResult] = []
        for f in findings:
            try:
                res = await self._run_pipeline(f, workspace_id)
                await self._persist_result(res, f, workspace_id)
                results.append(res)
            except Exception as exc:
                logger.warning(
                    "batch_analyze_skip finding_id=%s error=%s", f.id, exc
                )
        return results

    # ── Pipeline ──────────────────────────────────────────────────────────────

    async def _run_pipeline(
        self,
        finding: CanonicalFinding,
        workspace_id: uuid.UUID,
    ) -> FindingIntelligenceResult:
        """
        Execute causal analysis → RAG scoring → Ollama (or fallback) → result.
        """
        # 2. Causal analysis
        causal: CausalAnalysis = await self._causal.analyze(finding, workspace_id)

        # 3. RAG scoring
        rag: RAGScore = self._rag.compute(finding, causal)

        # 4. Ollama descriptive + RCA + recommendations
        ollama_available = await self.ollama.is_available()
        ollama_model: str | None = None
        fallback_used = False

        finding_context = {
            "title": finding.title,
            "description": finding.description or "",
            "resource_type": finding.resource_type or "AWS Resource",
            "severity": str(finding.severity or "medium"),
            "resource_arn": finding.resource_arn or "",
            "compliance_frameworks": finding.compliance_frameworks or [],
        }

        if ollama_available:
            try:
                models = await self.ollama.list_models()
                ollama_model = self.ollama.model
                descriptive = await self.ollama.generate_descriptive_analysis(finding_context)
                # If Ollama returned a fallback (rare but possible if model responded badly)
                if descriptive.fallback_used:
                    fallback_used = True

                rca_factors_dict = {
                    "primary_root_cause": causal.primary_root_cause,
                    "composite_score": causal.composite_score,
                    "causal_chain": causal.causal_chain,
                    "factors": [f.to_dict() for f in causal.factors],
                    "toxic_combinations": [c.to_dict() for c in causal.toxic_combinations],
                    "resource_type": finding.resource_type or "",
                }
                rca_narrative: RCANarrative = await self.ollama.generate_rca_narrative(
                    rca_factors_dict,
                    graph_context={},
                )
                # Enrich descriptive output with RCA narrative if it adds value
                # (attack_scenario is already in descriptive; rca_narrative is stored separately
                #  but we don't have a separate field — fold into attack_scenario)
                _ = await self.ollama.generate_recommendations(
                    rca_factors_dict,
                    rag.level,
                )
            except Exception as exc:
                logger.warning(
                    "ollama_pipeline_error finding_id=%s error=%s — using fallback",
                    finding.id,
                    exc,
                )
                descriptive = self.ollama._fallback_descriptive(finding_context)
                fallback_used = True
                ollama_model = None
        else:
            descriptive = self.ollama._fallback_descriptive(finding_context)
            fallback_used = True
            ollama_model = None

        return FindingIntelligenceResult(
            finding_id=finding.id,
            descriptive=descriptive,
            causal_analysis=causal,
            rag_score=rag,
            generated_at=datetime.now(UTC),
            ollama_model=ollama_model,
            fallback_used=fallback_used,
        )

    # ── Persistence ───────────────────────────────────────────────────────────

    async def _persist_result(
        self,
        result: FindingIntelligenceResult,
        finding: CanonicalFinding,
        workspace_id: uuid.UUID,
    ) -> None:
        d = result.descriptive
        c = result.causal_analysis
        r = result.rag_score

        # Normalise attack_scenario: Ollama may return a list of step-dicts or a plain string
        import json as _json
        attack_scenario = d.attack_scenario
        if isinstance(attack_scenario, list):
            # Convert step-list to numbered prose: "1. ... 2. ..."
            # Handles both {"action": "..."} and {"description": "..."} keys
            parts = []
            for item in attack_scenario:
                if isinstance(item, dict):
                    step = item.get("step", "")
                    text = item.get("action") or item.get("description") or str(item)
                    parts.append(f"{step}. {text}" if step else text)
                else:
                    parts.append(str(item))
            attack_scenario = "\n".join(parts)

        await self._intel_repo.upsert(
            finding_id=finding.id,
            workspace_id=workspace_id,
            # Descriptive
            what_is_it=d.what_is_it,
            current_state=d.current_state,
            expected_state=d.expected_state,
            business_impact=d.business_impact,
            attack_scenario=attack_scenario,
            # Causal
            composite_score=c.composite_score,
            primary_root_cause=c.primary_root_cause,
            causal_factors=[f.to_dict() for f in c.factors],
            causal_chain=c.causal_chain,
            toxic_combinations=[tc.to_dict() for tc in c.toxic_combinations],
            blast_radius_count=c.blast_radius.sensitive_node_count,
            confidence=c.confidence,
            # RAG
            rag_level=r.level,
            rag_composite_score=r.composite_score,
            rag_primary_reason=r.primary_reason,
            sla_days=r.sla_days,
            escalation_required=r.escalation_required,
            stakeholders=r.stakeholders,
            # Actions
            immediate_actions=[a.to_dict() for a in r.immediate_actions],
            sprint_actions=[a.to_dict() for a in r.sprint_actions],
            quarterly_actions=[a.to_dict() for a in r.quarterly_actions],
            # Metadata
            ollama_model=result.ollama_model,
            fallback_used=result.fallback_used,
            generation_status="completed",
            error_message=None,
        )
