"""
Async Redis client configuration with connection pooling, health checks,
and Pub/Sub helpers for the OmniSec communication bus.

Sprint 29 — OmniSec Infrastructure
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

try:
    import redis.asyncio as aioredis
    _redis_available = True
except ImportError:
    aioredis = None  # type: ignore
    _redis_available = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection setup
# ---------------------------------------------------------------------------

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_pool = None
redis_client = None

if _redis_available:
    try:
        _pool = aioredis.ConnectionPool.from_url(
            REDIS_URL,
            max_connections=50,
            decode_responses=True,
        )
        redis_client = aioredis.Redis(connection_pool=_pool)
    except Exception:
        logger.warning("Redis not available — running without Redis")

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_redis() -> aioredis.Redis:
    """Return the shared async Redis client instance."""
    return redis_client


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def redis_health() -> dict[str, Any]:
    """Ping Redis and return a simple health payload."""
    try:
        pong = await redis_client.ping()
        info = await redis_client.info(section="server")
        return {
            "status": "healthy",
            "ping": pong,
            "redis_version": info.get("redis_version", "unknown"),
        }
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return {"status": "unhealthy", "error": str(exc)}


# ---------------------------------------------------------------------------
# Pub/Sub helpers — communication bus
# ---------------------------------------------------------------------------


async def publish(channel: str, message: Any) -> int:
    """Publish a JSON-serialised message to *channel*.

    Returns the number of subscribers that received the message.
    """
    payload = json.dumps(message) if not isinstance(message, str) else message
    return await redis_client.publish(channel, payload)


async def subscribe(channel: str) -> aioredis.client.PubSub:
    """Return a PubSub object already subscribed to *channel*.

    Usage::

        ps = await subscribe("omnisec:events")
        async for msg in ps.listen():
            if msg["type"] == "message":
                data = json.loads(msg["data"])
    """
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    return pubsub


# ---------------------------------------------------------------------------
# Lifecycle helpers (call from FastAPI lifespan)
# ---------------------------------------------------------------------------


async def close_redis() -> None:
    """Gracefully close the Redis connection pool."""
    await redis_client.aclose()
    await _pool.aclose()
