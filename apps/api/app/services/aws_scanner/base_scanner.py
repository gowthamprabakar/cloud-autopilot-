"""
BaseScanner — abstract base for all AWS service scanners.

Rules:
- Each scanner receives a pre-built boto3 client, account_id, and region.
- scan() must return a list of normalised finding dicts ready for DB upsert.
- _safe_scan() wraps scan() so orchestrators never see raw exceptions.
- All boto3 calls in subclasses MUST use run_in_executor to avoid blocking.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseScanner(ABC):
    """Abstract base class for all AWS service scanners."""

    def __init__(self, boto3_client: Any, account_id: str, region: str) -> None:
        self.client = boto3_client
        self.account_id = account_id
        self.region = region
        self._loop = asyncio.get_event_loop

    @abstractmethod
    async def scan(self) -> list[dict]:
        """Return list of normalised finding dicts ready for DB upsert."""
        ...

    async def safe_scan(self) -> tuple[list[dict], str | None]:
        """
        Wraps scan() with try/except.
        Returns (findings, None) on success.
        Returns ([], error_message) on any error.
        Logs a warning but never raises.
        """
        try:
            findings = await self.scan()
            return findings, None
        except Exception as exc:
            logger.warning(
                "Scanner %s failed for account=%s region=%s: %s",
                self.__class__.__name__,
                self.account_id,
                self.region,
                str(exc),
            )
            return [], str(exc)

    def _run_sync(self, fn, *args, **kwargs):
        """
        Execute a synchronous boto3 call in a thread executor to avoid blocking
        the asyncio event loop.
        Returns a coroutine that resolves to the function's return value.
        """
        loop = asyncio.get_event_loop()
        import functools
        return loop.run_in_executor(None, functools.partial(fn, *args, **kwargs))
