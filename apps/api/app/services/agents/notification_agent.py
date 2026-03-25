"""
NotificationAgent — first ACT layer agent.

Triggered after TriageAgent completes. If suggested_severity is "critical",
broadcasts an in-app notification to all workspace users via NotificationService.

Idempotent: skips if a notification was already sent for this finding.
No LLM involved — pure rule-based ACT agent.

Output shape:
  {
    notification_sent: bool,
    channel: "in_app",
    severity: str,
    message: str,
  }
"""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_result import AgentResult
from app.repositories.canonical_finding_repository import CanonicalFindingRepository
from app.repositories.notification_repository import NotificationRepository
from app.services.agents.base_agent import BaseAgent
from app.services.notification_service import NotificationService

logger = structlog.get_logger(__name__)

_CRITICAL_SEVERITIES = {"critical"}


class NotificationAgent(BaseAgent):
    """
    ACT layer agent — sends in-app notifications for critical findings.
    Runs after TriageAgent; reads the latest triage result to get suggested_severity.
    """
    agent_name = "notification"

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._finding_repo = CanonicalFindingRepository(db)
        self._notif_repo = NotificationRepository(db)

    async def _run(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> tuple[dict, str]:
        from app.core.exceptions import NotFoundError

        finding = await self._finding_repo.get_by_id_and_workspace(finding_id, workspace_id)
        if finding is None:
            raise NotFoundError(f"Finding {finding_id} not found in workspace {workspace_id}")

        # ── Idempotency check ────────────────────────────────────────────────
        existing = await self.db.execute(
            select(AgentResult)
            .where(
                AgentResult.finding_id == finding_id,
                AgentResult.workspace_id == workspace_id,
                AgentResult.agent_name == "notification",
                AgentResult.status == "completed",
            )
            .order_by(AgentResult.created_at.desc())
            .limit(1)
        )
        existing_row = existing.scalar_one_or_none()
        if existing_row and existing_row.output.get("notification_sent") is True:
            logger.info("notification_agent.skipped_duplicate", finding_id=str(finding_id))
            return existing_row.output, "none"

        # ── Load triage result ────────────────────────────────────────────────
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

        # Fall back to finding's own severity if no triage result
        if triage_row:
            suggested_severity = triage_row.output.get("suggested_severity", "")
        else:
            sev = finding.severity
            suggested_severity = sev.value if hasattr(sev, "value") else str(sev)

        # ── Severity gate ────────────────────────────────────────────────────
        if suggested_severity.lower() not in _CRITICAL_SEVERITIES:
            output = {
                "notification_sent": False,
                "channel": "in_app",
                "severity": suggested_severity,
                "message": f"Severity '{suggested_severity}' is below critical threshold — no notification sent.",
            }
            return output, "none"

        # ── Send notification ─────────────────────────────────────────────────
        notif_svc = NotificationService(self._notif_repo)
        await notif_svc.create(
            workspace_id=workspace_id,
            user_id=None,  # broadcast to workspace
            type="critical_finding",
            title=f"Critical Finding: {finding.title[:80]}",
            body=(
                f"AI triage classified '{finding.title[:100]}' as CRITICAL. "
                f"Resource: {finding.resource_type or 'Unknown'}. "
                "Immediate review required."
            ),
            metadata_={"finding_id": str(finding_id), "triggered_by": "notification_agent"},
            link_path=f"/dashboard/findings/{finding_id}",
        )

        message = f"In-app notification sent for critical finding: {finding.title[:80]}"
        logger.info("notification_agent.sent", finding_id=str(finding_id), message=message)

        output = {
            "notification_sent": True,
            "channel": "in_app",
            "severity": suggested_severity,
            "message": message,
        }
        return output, "none"
