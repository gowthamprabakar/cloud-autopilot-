"""
Job registry — maps JobType → BaseJob subclass.

The decorator @register_job(JobType.X) on each job class populates this dict
at import time. This module eagerly imports all job implementations at the
bottom to ensure the registry is fully populated when the application starts.

Jobs imported here: AWS_ACCOUNT_VALIDATE, SECURITY_HUB_SYNC, CONFIG_SYNC,
GUARDDUTY_SYNC, INSPECTOR_SYNC, AI_SUMMARIZE.
"""

from app.jobs.base import JobType

JOB_REGISTRY: dict[JobType, type] = {}


def register_job(job_type: JobType):
    """Decorator to register a job implementation."""
    def decorator(cls):
        JOB_REGISTRY[job_type] = cls
        return cls
    return decorator


# ── Eager registration ─────────────────────────────────────────────────────
# Import all job implementations so their @register_job decorators fire and
# JOB_REGISTRY is fully populated at application startup.
# Imports are at the BOTTOM to avoid circular imports (job files import
# register_job from this module).

def _register_all() -> None:
    """Import all job modules to trigger @register_job decorators."""
    from app.jobs import aws_account_validate_job  # noqa: F401
    from app.jobs import security_hub_sync_job  # noqa: F401
    from app.jobs import config_sync_job  # noqa: F401
    from app.jobs import guardduty_sync_job  # noqa: F401
    from app.jobs import inspector_sync_job  # noqa: F401
    from app.jobs import ai_summarize_job  # noqa: F401


_register_all()
