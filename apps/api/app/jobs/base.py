"""
Job lifecycle base — Cloud Posture Copilot.

All async jobs (AWS validation, Security Hub ingestion, Config sync,
GuardDuty sync, normalization, scoring, report generation) inherit
from BaseJob and conform to this lifecycle:

  PENDING → RUNNING → COMPLETED
                    ↘ FAILED
                    ↘ CANCELLED

Each job implementation:
  1. Overrides `job_type` class variable.
  2. Implements `run()` with all domain logic.
  3. Calls `self.emit_progress()` to report incremental state.
  4. Never touches risk_score, compliance_state, or ai_insights directly.

Sprint 0: base class + enums only.
Phase 1: persistence layer (job_runs table) + runner abstraction.
Phase 2: source-specific job implementations.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(StrEnum):
    # Phase 1
    AWS_ACCOUNT_VALIDATE = "aws_account_validate"
    # Phase 2
    SECURITY_HUB_SYNC = "security_hub_sync"
    CONFIG_SYNC = "config_sync"
    GUARDDUTY_SYNC = "guardduty_sync"
    INSPECTOR_SYNC = "inspector_sync"
    NORMALIZATION = "normalization"
    # Phase 3
    RISK_SCORING = "risk_scoring"
    COVERAGE_COMPUTE = "coverage_compute"
    # Phase 4
    REPORT_GENERATE = "report_generate"
    # Phase 5
    AI_SUMMARIZE = "ai_summarize"


@dataclass
class JobContext:
    """Immutable context passed into every job run."""

    tenant_id: uuid.UUID
    workspace_id: uuid.UUID
    job_run_id: uuid.UUID = field(default_factory=uuid.uuid4)
    triggered_by: str = "system"
    payload: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class JobResult:
    status: JobStatus
    message: str = ""
    output: dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    error: str | None = None


class BaseJob(ABC):
    """Abstract base for all Cloud Posture Copilot async jobs."""

    job_type: JobType  # must be set by subclass

    def __init__(self, ctx: JobContext) -> None:
        self.ctx = ctx
        self._status = JobStatus.PENDING
        self._log = logger.bind(
            job_type=self.job_type,
            job_run_id=str(ctx.job_run_id),
            tenant_id=str(ctx.tenant_id),
            workspace_id=str(ctx.workspace_id),
        )

    @property
    def status(self) -> JobStatus:
        return self._status

    async def execute(self) -> JobResult:
        """Entrypoint — manages lifecycle; subclass implements run()."""
        self._status = JobStatus.RUNNING
        self._log.info("job.started")

        try:
            result = await asyncio.wait_for(self.run(), timeout=self._timeout_seconds())
            self._status = JobStatus.COMPLETED
            self._log.info("job.completed", output_keys=list(result.output.keys()))
            return result
        except asyncio.TimeoutError:
            self._status = JobStatus.FAILED
            self._log.error("job.timeout")
            return JobResult(
                status=JobStatus.FAILED,
                error="Job exceeded maximum allowed runtime",
            )
        except Exception as exc:
            self._status = JobStatus.FAILED
            self._log.exception("job.failed", error=str(exc))
            return JobResult(
                status=JobStatus.FAILED,
                error=str(exc),
            )

    @abstractmethod
    async def run(self) -> JobResult:
        """Implement all domain logic here. Must return a JobResult."""
        ...

    def emit_progress(self, message: str, pct: int | None = None) -> None:
        """Log incremental progress. Phase 1 will wire this to SSE/websocket."""
        self._log.info("job.progress", message=message, pct=pct)

    def _timeout_seconds(self) -> int:
        # Default 10 min; heavy jobs can override
        return 600
