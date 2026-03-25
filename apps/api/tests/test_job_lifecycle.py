import uuid

import pytest

from app.jobs.base import BaseJob, JobContext, JobResult, JobStatus, JobType


class _EchoJob(BaseJob):
    job_type = JobType.AWS_ACCOUNT_VALIDATE

    async def run(self) -> JobResult:
        self.emit_progress("echo running", pct=50)
        return JobResult(
            status=JobStatus.COMPLETED,
            message="echo done",
            output={"echo": True},
        )


class _FailJob(BaseJob):
    job_type = JobType.AWS_ACCOUNT_VALIDATE

    async def run(self) -> JobResult:
        raise ValueError("intentional failure")


def _ctx() -> JobContext:
    return JobContext(
        tenant_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
    )


@pytest.mark.asyncio
async def test_job_completes_successfully():
    job = _EchoJob(_ctx())
    result = await job.execute()
    assert result.status == JobStatus.COMPLETED
    assert result.output["echo"] is True
    assert job.status == JobStatus.COMPLETED


@pytest.mark.asyncio
async def test_job_fails_on_exception():
    job = _FailJob(_ctx())
    result = await job.execute()
    assert result.status == JobStatus.FAILED
    assert "intentional failure" in (result.error or "")
    assert job.status == JobStatus.FAILED
