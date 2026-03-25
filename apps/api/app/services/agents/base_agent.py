"""
BaseAgent — abstract foundation for all THINK layer agents.

Contract:
- Subclasses implement `_run(finding_id, workspace_id) -> (output_dict, model_used_str)`.
- `execute(finding_id, workspace_id, triggered_by)` wraps _run() with:
    1. Timing (monotonic clock)
    2. AgentResult persistence (always — even on failure)
    3. AuditLog persistence (passive observer, baked in here)
- Never raises to the caller: failures are stored with status="failed" + error_message.
"""

import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod

import structlog

from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class BaseAgent(ABC):
    """
    All THINK layer agents inherit this class.

    Subclasses MUST set class variable:
        agent_name: str  — e.g. "triage", "attack_path"
    """
    agent_name: str = "base"

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @abstractmethod
    async def _run(
        self, finding_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> tuple[dict, str]:
        """
        Core agent logic. Subclasses implement this.

        Returns:
            (output_dict, model_used_str)

        Raises any exception on failure — BaseAgent.execute() catches and records it.
        """
        ...

    async def execute(
        self,
        finding_id: uuid.UUID,
        workspace_id: uuid.UUID,
        triggered_by: str = "api_user",
    ):
        """
        Public entry point. Always returns an AgentResult (completed or failed).
        Never raises to the caller.
        """
        from app.models.agent_result import AgentResult
        from app.models.agent_audit_log import AgentAuditLog

        start_ms = time.monotonic()
        model_used = "unknown"
        output: dict = {}
        error_message: str | None = None
        status = "completed"

        try:
            output, model_used = await self._run(finding_id, workspace_id)
        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            model_used = model_used or "unknown"
            output = {}
            logger.error(
                "agent.execute.failed",
                agent=self.agent_name,
                finding_id=str(finding_id),
                error=error_message,
            )

        latency_ms = int((time.monotonic() - start_ms) * 1000)

        # ── Persist AgentResult ──────────────────────────────────────────────
        result = AgentResult(
            workspace_id=workspace_id,
            finding_id=finding_id,
            agent_name=self.agent_name,
            status=status,
            model_used=model_used,
            output=output,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        self.db.add(result)
        await self.db.flush()
        await self.db.refresh(result)

        # ── AuditAgent — passively log every invocation ───────────────────────
        input_payload = json.dumps(
            {
                "finding_id": str(finding_id),
                "workspace_id": str(workspace_id),
                "agent_name": self.agent_name,
            },
            sort_keys=True,
        )
        input_hash = hashlib.sha256(input_payload.encode()).hexdigest()
        output_summary = self._summarize_output(output, error_message, status)

        audit_log = AgentAuditLog(
            workspace_id=workspace_id,
            finding_id=finding_id,
            agent_name=self.agent_name,
            triggered_by=triggered_by,
            input_hash=input_hash,
            output_summary=output_summary,
            model_used=model_used,
            latency_ms=latency_ms,
        )
        self.db.add(audit_log)
        await self.db.flush()

        logger.info(
            "agent.execute.complete",
            agent=self.agent_name,
            finding_id=str(finding_id),
            workspace_id=str(workspace_id),
            status=status,
            model=model_used,
            latency_ms=latency_ms,
        )

        return result

    def _summarize_output(
        self,
        output: dict,
        error_message: str | None,
        status: str,
    ) -> str:
        """Generate a short, human-readable summary (≤ 500 chars) for the audit log."""
        if status == "failed":
            return f"FAILED: {(error_message or 'unknown error')[:490]}"
        try:
            return json.dumps(output)[:500]
        except Exception:
            return str(output)[:500]
