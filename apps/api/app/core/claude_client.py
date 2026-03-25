"""
Unified async Claude API client with retry logic, rate limiting,
and token-usage tracking.

Sprint 29 — OmniSec Infrastructure
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Tuple

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class ClaudeAPIError(Exception):
    """Raised when the Claude API call fails after all retries."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"

_MAX_RETRIES = 3
_BACKOFF_SCHEDULE = (1.0, 2.0, 4.0)  # seconds


# ---------------------------------------------------------------------------
# Simple sliding-window rate limiter
# ---------------------------------------------------------------------------


class _RateLimiter:
    """In-process sliding-window rate limiter (async-safe)."""

    def __init__(self, max_requests_per_minute: int = 50) -> None:
        self._max_rpm = max_requests_per_minute
        self._timestamps: list[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            window_start = now - 60.0
            self._timestamps = [t for t in self._timestamps if t > window_start]
            if len(self._timestamps) >= self._max_rpm:
                sleep_for = 60.0 - (now - self._timestamps[0])
                if sleep_for > 0:
                    logger.info(
                        "Claude rate limiter: sleeping %.1fs (window full)", sleep_for
                    )
                    await asyncio.sleep(sleep_for)
            self._timestamps.append(time.monotonic())


# Module-level rate limiter (configurable via env)
_rate_limiter = _RateLimiter(
    max_requests_per_minute=int(os.getenv("CLAUDE_MAX_RPM", "50"))
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def call_claude(
    system_prompt: str,
    user_message: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1000,
) -> Tuple[str, int, int]:
    """Call the Anthropic Messages API with retries and rate limiting.

    Parameters
    ----------
    system_prompt:
        System-level instruction.
    user_message:
        User message content.
    model:
        Anthropic model identifier.
    max_tokens:
        Maximum tokens for the response.

    Returns
    -------
    tuple of (response_text, input_tokens, output_tokens)

    Raises
    ------
    ClaudeAPIError
        After exhausting all retry attempts.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ClaudeAPIError("ANTHROPIC_API_KEY environment variable is not set")

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

    last_exc: Exception | None = None

    for attempt in range(_MAX_RETRIES):
        await _rate_limiter.acquire()

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(_API_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

            response_text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    response_text += block["text"]

            usage = data.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            logger.debug(
                "Claude call succeeded (attempt %d): model=%s in=%d out=%d",
                attempt + 1,
                model,
                input_tokens,
                output_tokens,
            )
            return response_text, input_tokens, output_tokens

        except httpx.HTTPStatusError as exc:
            last_exc = exc
            status = exc.response.status_code
            logger.warning(
                "Claude API HTTP %d on attempt %d/%d: %s",
                status,
                attempt + 1,
                _MAX_RETRIES,
                exc.response.text[:300],
            )
            # Don't retry on client errors other than 429 (rate limit)
            if 400 <= status < 500 and status != 429:
                raise ClaudeAPIError(
                    f"Claude API returned {status}: {exc.response.text[:300]}",
                    status_code=status,
                ) from exc

        except (httpx.RequestError, httpx.TimeoutException) as exc:
            last_exc = exc
            logger.warning(
                "Claude API request error on attempt %d/%d: %s",
                attempt + 1,
                _MAX_RETRIES,
                exc,
            )

        # Exponential backoff before next retry
        if attempt < _MAX_RETRIES - 1:
            delay = _BACKOFF_SCHEDULE[attempt]
            logger.info("Retrying Claude API in %.1fs…", delay)
            await asyncio.sleep(delay)

    raise ClaudeAPIError(
        f"Claude API call failed after {_MAX_RETRIES} attempts: {last_exc}",
        status_code=getattr(last_exc, "status_code", None)
        if hasattr(last_exc, "status_code")
        else None,
    )
