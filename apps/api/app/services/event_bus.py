"""
EventBus — Asynchronous event distribution for OmniSec.

Sprint 31: Dual-mode event bus:
  - Production: Apache Kafka (KAFKA_BROKER_URL env var)
  - Development: Redis pub/sub fallback (always available)

Events:
  - simulation.started / simulation.completed / simulation.failed
  - agent.started / agent.completed / agent.error / agent.spawned
  - gate.evaluated / gate.passed / gate.failed
  - message.posted (comm bus relay)
  - finding.ingested / finding.resolved
  - graph.updated (Neo4j sync trigger)
"""

from __future__ import annotations
import json, os, uuid
from datetime import datetime, UTC
from typing import Any, Callable, Awaitable

# Event types
EVENT_TYPES = {
    "simulation.started", "simulation.completed", "simulation.failed",
    "agent.started", "agent.completed", "agent.error", "agent.spawned",
    "gate.evaluated", "gate.passed", "gate.failed",
    "message.posted",
    "finding.ingested", "finding.resolved",
    "graph.updated",
}


class Event:
    """Structured event envelope."""
    def __init__(self, event_type: str, payload: dict, source: str = "omnisec"):
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.payload = payload
        self.source = source
        self.timestamp = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "payload": self.payload,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, data: str) -> "Event":
        d = json.loads(data)
        event = cls(d["event_type"], d["payload"], d.get("source", "omnisec"))
        event.id = d.get("id", str(uuid.uuid4()))
        event.timestamp = d.get("timestamp", datetime.now(UTC).isoformat())
        return event


class EventBus:
    """Dual-mode event bus: Kafka (prod) or Redis pub/sub (dev)."""

    def __init__(self):
        self._handlers: dict[str, list[Callable[[Event], Awaitable[None]]]] = {}
        self._mode = "redis"  # default fallback
        self._redis = None

    async def initialize(self):
        """Initialize the event bus backend."""
        kafka_url = os.getenv("KAFKA_BROKER_URL")
        if kafka_url:
            # Production: Kafka mode
            self._mode = "kafka"
            # Kafka initialization would go here
            # For Sprint 31, we use Redis as primary

        # Redis fallback (always available)
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            self._mode = "redis"
        except Exception:
            self._mode = "memory"  # in-memory fallback if no Redis

    def on(self, event_type: str, handler: Callable[[Event], Awaitable[None]]):
        """Register an event handler."""
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event: Event):
        """Emit an event to all registered handlers and the bus backend."""
        # Local handlers
        handlers = self._handlers.get(event.event_type, [])
        handlers.extend(self._handlers.get("*", []))  # wildcard handlers
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                pass  # don't let handler errors break the bus

        # Publish to backend
        if self._mode == "redis" and self._redis:
            try:
                channel = f"omnisec:events:{event.event_type}"
                await self._redis.publish(channel, event.to_json())
            except Exception:
                pass

    async def emit_simple(self, event_type: str, **payload):
        """Convenience: emit a simple event with keyword payload."""
        await self.emit(Event(event_type, payload))

    async def close(self):
        """Shutdown the event bus."""
        if self._redis:
            await self._redis.close()


# Singleton
_bus: EventBus | None = None

async def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
        await _bus.initialize()
    return _bus
