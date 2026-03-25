"""
Celery configuration for asynchronous agent execution.

Broker and result backend default to Redis.  Override via
CELERY_BROKER_URL / CELERY_RESULT_BACKEND environment variables.

Sprint 29 — OmniSec Infrastructure
"""

from __future__ import annotations

import logging
import os

import httpx
from celery import Celery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------

CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "omnisec",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task time limits (seconds)
    task_soft_time_limit=120,  # 2 min per agent — raises SoftTimeLimitExceeded
    task_time_limit=180,       # hard kill at 3 min
    # Result expiry
    result_expires=3600,       # keep results for 1 hour
    # Prefetch
    worker_prefetch_multiplier=1,
)

# ---------------------------------------------------------------------------
# Claude API constants (duplicated here so the worker doesn't need FastAPI)
# ---------------------------------------------------------------------------

_ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@celery_app.task(
    name="omnisec.run_agent_task",
    bind=True,
    max_retries=2,
    default_retry_delay=5,
    acks_late=True,
)
def run_agent_task(
    self,
    agent_id: str,
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1000,
) -> dict:
    """Execute a single Claude-backed agent call synchronously inside a Celery worker.

    Parameters
    ----------
    agent_id:
        Logical identifier for the calling agent (used in logging/tracking).
    system_prompt:
        The system-level instruction for Claude.
    user_message:
        The user-facing message / query.
    model:
        Anthropic model identifier.
    max_tokens:
        Max tokens for the completion.

    Returns
    -------
    dict with keys: agent_id, response_text, input_tokens, output_tokens, model
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(_ANTHROPIC_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        response_text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                response_text += block["text"]

        usage = data.get("usage", {})
        return {
            "agent_id": agent_id,
            "response_text": response_text,
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "model": model,
        }

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Claude API HTTP error for agent %s: %s — %s",
            agent_id,
            exc.response.status_code,
            exc.response.text[:500],
        )
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.exception("Unexpected error in run_agent_task for agent %s", agent_id)
        raise self.retry(exc=exc)
