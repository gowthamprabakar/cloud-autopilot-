"""
AiSummarizeJob — bulk AI insight generation for all open findings.

Triggered by:
  POST /api/v1/aws-accounts/{id}/ai-summarize  (per-account)

Design:
- Iterates open canonical findings for the workspace.
- Calls AiService.generate_insight() for each (idempotent — skips cached).
- Respects settings.ai_enabled — no-op if disabled.
- Limits to MAX_FINDINGS_PER_RUN to avoid runaway API cost.
"""

from app.jobs.base import BaseJob, JobContext, JobResult, JobStatus, JobType
from app.core.config import settings
import structlog

logger = structlog.get_logger(__name__)

MAX_FINDINGS_PER_RUN = 50


class AiSummarizeJob(BaseJob):
    job_type = JobType.AI_SUMMARIZE

    def __init__(self, ctx: JobContext, db_session_factory) -> None:
        super().__init__(ctx)
        self._db_session_factory = db_session_factory

    async def run(self) -> JobResult:
        if not settings.ai_enabled:
            self._log.info("ai.summarize.skipped", reason="ai_enabled=False")
            return JobResult(
                status=JobStatus.COMPLETED,
                message="AI disabled — skipped",
                output={"processed": 0},
            )

        from app.repositories.ai_insight_repository import AiInsightRepository
        from app.repositories.ai_feedback_repository import AiFeedbackRepository
        from app.repositories.canonical_finding_repository import CanonicalFindingRepository
        from app.services.ai_service import AiService
        from app.models.enums import FindingStatus

        workspace_id = self.ctx.workspace_id
        aws_account_id = self.ctx.payload.get("aws_account_id")

        processed = 0
        errors = 0

        async with self._db_session_factory() as db:
            finding_repo = CanonicalFindingRepository(db)
            svc = AiService(
                insight_repo=AiInsightRepository(db),
                feedback_repo=AiFeedbackRepository(db),
                finding_repo=finding_repo,
            )

            # Fetch open findings (limit to MAX_FINDINGS_PER_RUN)
            from sqlalchemy import select
            from app.models.canonical_finding import CanonicalFinding

            stmt = (
                select(CanonicalFinding)
                .where(
                    CanonicalFinding.workspace_id == workspace_id,
                    CanonicalFinding.status == FindingStatus.OPEN,
                )
                .limit(MAX_FINDINGS_PER_RUN)
            )
            if aws_account_id:
                stmt = stmt.where(
                    CanonicalFinding.aws_account_id == aws_account_id
                )

            result = await db.execute(stmt)
            findings = list(result.scalars().all())

            self._log.info(
                "ai.summarize.start",
                finding_count=len(findings),
                workspace_id=str(workspace_id),
            )

            for finding in findings:
                try:
                    self.emit_progress(
                        f"Processing finding {processed + 1}/{len(findings)}: {finding.title[:60]}"
                    )
                    await svc.generate_insight(
                        finding_id=finding.id,
                        workspace_id=workspace_id,
                    )
                    await db.commit()
                    processed += 1
                except Exception as exc:
                    errors += 1
                    self._log.warning(
                        "ai.summarize.finding_error",
                        finding_id=str(finding.id),
                        error=str(exc),
                    )
                    await db.rollback()

        return JobResult(
            status=JobStatus.COMPLETED,
            message=f"AI summarize complete: {processed} processed, {errors} errors",
            output={"processed": processed, "errors": errors},
        )
