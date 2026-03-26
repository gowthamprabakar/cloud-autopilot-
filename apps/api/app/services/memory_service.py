"""
MemoryService — Zep-compatible agent memory management.

Sprint 31: Provides persistent, queryable memory for swarm agents.
Memory types:
  - working:    Live key-value state during simulation (short-term)
  - episodic:   Historical actions and outcomes (medium-term, FIFO bounded)
  - semantic:   Domain knowledge and learned patterns (long-term)
  - procedural: Reusable strategies and playbooks (permanent)

Features:
  - Relevance decay: memories lose relevance over time (configurable half-life)
  - Access-based reinforcement: frequently accessed memories gain relevance
  - TTL eviction: working memories auto-expire after simulation ends
  - Cross-simulation learning: semantic/procedural memories persist across runs
"""

from __future__ import annotations

import json
import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_memory import AgentMemory
from app.models.swarm_agent import SwarmAgent

VALID_MEMORY_TYPES = {"working", "episodic", "semantic", "procedural"}

# Reinforcement boost per access — caps diminishing returns via log curve
_ACCESS_BOOST_FACTOR = 0.02


def _utcnow() -> datetime:
    return datetime.now(UTC)


class MemoryService:
    """Zep-compatible agent memory management backed by SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Store ────────────────────────────────────────────────────────────────

    async def store(
        self,
        workspace_id: uuid.UUID,
        agent_id: str,
        memory_type: str,
        key: str,
        value: Any,
        relevance: float = 1.0,
        ttl_hours: float | None = None,
        run_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> AgentMemory:
        """Store a memory entry. Upserts on (workspace_id, agent_id, memory_type, key)."""
        if memory_type not in VALID_MEMORY_TYPES:
            raise ValueError(
                f"Invalid memory_type '{memory_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_MEMORY_TYPES))}"
            )

        value_str = json.dumps(value) if not isinstance(value, str) else value
        expires_at = _utcnow() + timedelta(hours=ttl_hours) if ttl_hours else None
        metadata_str = json.dumps(metadata) if metadata else None

        # Check for existing entry (upsert)
        stmt = select(AgentMemory).where(
            AgentMemory.workspace_id == workspace_id,
            AgentMemory.agent_id == agent_id,
            AgentMemory.memory_type == memory_type,
            AgentMemory.key == key,
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value_str
            existing.relevance_score = min(1.0, max(0.0, relevance))
            existing.expires_at = expires_at
            existing.simulation_run_id = run_id
            existing.metadata_json = metadata_str
            existing.access_count += 1
            existing.last_accessed_at = _utcnow()
            await self.db.flush()
            return existing

        mem = AgentMemory(
            workspace_id=workspace_id,
            agent_id=agent_id,
            memory_type=memory_type,
            key=key,
            value=value_str,
            relevance_score=min(1.0, max(0.0, relevance)),
            access_count=0,
            expires_at=expires_at,
            simulation_run_id=run_id,
            metadata_json=metadata_str,
        )
        self.db.add(mem)
        await self.db.flush()
        return mem

    # ── Recall ───────────────────────────────────────────────────────────────

    async def recall(
        self,
        workspace_id: uuid.UUID,
        agent_id: str,
        memory_type: str | None = None,
        key: str | None = None,
        min_relevance: float = 0.1,
        limit: int = 50,
    ) -> list[dict]:
        """Recall memories with optional filtering.

        Updates access_count and last_accessed_at for returned memories.
        Returns list of dicts sorted by relevance descending.
        """
        stmt = select(AgentMemory).where(
            AgentMemory.workspace_id == workspace_id,
            AgentMemory.agent_id == agent_id,
            AgentMemory.relevance_score >= min_relevance,
        )
        if memory_type:
            stmt = stmt.where(AgentMemory.memory_type == memory_type)
        if key:
            stmt = stmt.where(AgentMemory.key == key)

        stmt = stmt.order_by(AgentMemory.relevance_score.desc()).limit(limit)

        result = await self.db.execute(stmt)
        memories = list(result.scalars().all())

        # Update access stats for recalled memories
        if memories:
            now = _utcnow()
            mem_ids = [m.id for m in memories]
            await self.db.execute(
                update(AgentMemory)
                .where(AgentMemory.id.in_(mem_ids))
                .values(
                    access_count=AgentMemory.access_count + 1,
                    last_accessed_at=now,
                    # Slight relevance boost on access (capped at 1.0)
                    relevance_score=func.least(
                        1.0,
                        AgentMemory.relevance_score + _ACCESS_BOOST_FACTOR,
                    ),
                )
            )

        return [_memory_to_dict(m) for m in memories]

    # ── Prompt Context Builder ───────────────────────────────────────────────

    async def recall_for_prompt(
        self,
        workspace_id: uuid.UUID,
        agent_id: str,
        domain: str,
        max_tokens: int = 500,
    ) -> str:
        """Build a memory context string for injection into agent prompts.

        Retrieves most relevant semantic + procedural memories for the domain.
        Truncates to approximately max_tokens worth of text (4 chars ~ 1 token).
        """
        stmt = (
            select(AgentMemory)
            .where(
                AgentMemory.workspace_id == workspace_id,
                AgentMemory.agent_id == agent_id,
                AgentMemory.memory_type.in_(["semantic", "procedural"]),
                AgentMemory.relevance_score >= 0.2,
            )
            .order_by(AgentMemory.relevance_score.desc())
            .limit(20)
        )
        result = await self.db.execute(stmt)
        memories = list(result.scalars().all())

        if not memories:
            return ""

        max_chars = max_tokens * 4
        lines: list[str] = []
        char_count = 0

        for mem in memories:
            # Try to extract domain from metadata
            if mem.metadata_json:
                try:
                    meta = json.loads(mem.metadata_json)
                    mem_domain = meta.get("domain", "")
                    if mem_domain and mem_domain != domain:
                        continue  # Skip memories from other domains
                except (json.JSONDecodeError, TypeError):
                    pass

            line = f"- [{mem.memory_type}] {mem.key}: {mem.value}"
            if char_count + len(line) > max_chars:
                break
            lines.append(line)
            char_count += len(line)

        if not lines:
            return ""

        return "## Agent Memory Context\n" + "\n".join(lines)

    # ── Learn from Simulation ────────────────────────────────────────────────

    async def learn_from_simulation(
        self,
        workspace_id: uuid.UUID,
        run_id: uuid.UUID,
    ) -> int:
        """Extract semantic memories from a completed simulation's agent outputs.

        Scans agent outputs for key patterns and stores as semantic memories.
        Returns count of memories created.
        """
        # Fetch all agents for this simulation run
        stmt = select(SwarmAgent).where(
            SwarmAgent.simulation_run_id == run_id,
            SwarmAgent.status == "completed",
            SwarmAgent.output.isnot(None),
        )
        result = await self.db.execute(stmt)
        agents = list(result.scalars().all())

        created = 0
        for agent in agents:
            try:
                output = json.loads(agent.output) if isinstance(agent.output, str) else agent.output
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(output, dict):
                continue

            # Extract findings/recommendations as semantic memories
            for field in ("findings", "recommendations", "key_insights", "summary"):
                if field in output:
                    content = output[field]
                    if isinstance(content, list):
                        for i, item in enumerate(content):
                            await self.store(
                                workspace_id=workspace_id,
                                agent_id=agent.agent_id,
                                memory_type="semantic",
                                key=f"sim_{run_id}_{field}_{i}",
                                value=item,
                                relevance=0.8,
                                run_id=run_id,
                                metadata={"domain": getattr(agent, "role", "unknown"), "source": "simulation"},
                            )
                            created += 1
                    elif isinstance(content, str) and len(content) > 10:
                        await self.store(
                            workspace_id=workspace_id,
                            agent_id=agent.agent_id,
                            memory_type="semantic",
                            key=f"sim_{run_id}_{field}",
                            value=content,
                            relevance=0.8,
                            run_id=run_id,
                            metadata={"domain": getattr(agent, "role", "unknown"), "source": "simulation"},
                        )
                        created += 1

        await self.db.flush()
        return created

    # ── Relevance Decay ──────────────────────────────────────────────────────

    async def decay_relevance(
        self,
        workspace_id: uuid.UUID,
        half_life_days: float = 7.0,
    ) -> int:
        """Apply relevance decay to all memories.

        Memories older than half_life_days get their relevance halved.
        Uses exponential decay: relevance *= 2^(-days_since_update / half_life).
        Returns count of decayed memories.
        """
        now = _utcnow()
        cutoff = now - timedelta(days=half_life_days)

        # Select memories that haven't been updated recently
        stmt = select(AgentMemory).where(
            AgentMemory.workspace_id == workspace_id,
            AgentMemory.updated_at < cutoff,
            AgentMemory.relevance_score > 0.01,  # Skip nearly-zero memories
            # Don't decay procedural memories — they're permanent
            AgentMemory.memory_type != "procedural",
        )
        result = await self.db.execute(stmt)
        memories = list(result.scalars().all())

        decayed = 0
        for mem in memories:
            days_since = (now - mem.updated_at).total_seconds() / 86400
            decay_factor = math.pow(2, -days_since / half_life_days)
            # Access count provides resistance to decay
            access_resistance = 1.0 + (math.log1p(mem.access_count) * 0.1)
            new_relevance = mem.relevance_score * decay_factor * min(access_resistance, 1.5)
            new_relevance = max(0.0, min(1.0, new_relevance))

            if abs(new_relevance - mem.relevance_score) > 0.001:
                mem.relevance_score = new_relevance
                decayed += 1

        if decayed:
            await self.db.flush()

        return decayed

    # ── TTL Eviction ─────────────────────────────────────────────────────────

    async def evict_expired(self, workspace_id: uuid.UUID) -> int:
        """Remove memories past their TTL. Returns count of evicted memories."""
        now = _utcnow()
        stmt = (
            delete(AgentMemory)
            .where(
                AgentMemory.workspace_id == workspace_id,
                AgentMemory.expires_at.isnot(None),
                AgentMemory.expires_at <= now,
            )
            .returning(AgentMemory.id)
        )
        result = await self.db.execute(stmt)
        evicted = len(result.all())
        return evicted

    # ── Agent Memory Summary ─────────────────────────────────────────────────

    async def get_agent_memory_summary(
        self,
        workspace_id: uuid.UUID,
        agent_id: str,
    ) -> dict:
        """Return memory stats: count by type, avg relevance, oldest/newest."""
        # Count + avg relevance by type
        stmt = (
            select(
                AgentMemory.memory_type,
                func.count(AgentMemory.id).label("count"),
                func.avg(AgentMemory.relevance_score).label("avg_relevance"),
                func.min(AgentMemory.created_at).label("oldest"),
                func.max(AgentMemory.created_at).label("newest"),
            )
            .where(
                AgentMemory.workspace_id == workspace_id,
                AgentMemory.agent_id == agent_id,
            )
            .group_by(AgentMemory.memory_type)
        )
        result = await self.db.execute(stmt)
        rows = result.all()

        by_type: dict[str, dict] = {}
        total_count = 0
        for row in rows:
            by_type[row.memory_type] = {
                "count": row.count,
                "avg_relevance": round(float(row.avg_relevance or 0), 4),
                "oldest": row.oldest.isoformat() if row.oldest else None,
                "newest": row.newest.isoformat() if row.newest else None,
            }
            total_count += row.count

        return {
            "agent_id": agent_id,
            "workspace_id": str(workspace_id),
            "total_memories": total_count,
            "by_type": by_type,
        }

    # ── Bulk Working Memory ──────────────────────────────────────────────────

    async def bulk_store_working_memory(
        self,
        workspace_id: uuid.UUID,
        agent_id: str,
        memory_dict: dict[str, Any],
        run_id: uuid.UUID | None = None,
    ) -> int:
        """Store multiple working memory entries from an agent's state dict.

        Each key-value pair in memory_dict becomes a working memory entry.
        Returns count of stored entries.
        """
        stored = 0
        for key, value in memory_dict.items():
            await self.store(
                workspace_id=workspace_id,
                agent_id=agent_id,
                memory_type="working",
                key=key,
                value=value,
                ttl_hours=24,  # Working memory expires in 24h by default
                run_id=run_id,
            )
            stored += 1
        return stored

    # ── Clear Working Memory ─────────────────────────────────────────────────

    async def clear_working_memory(
        self,
        workspace_id: uuid.UUID,
        agent_id: str,
        run_id: uuid.UUID | None = None,
    ) -> int:
        """Clear all working memory for an agent (typically after simulation ends).

        If run_id is provided, only clears working memory for that run.
        Returns count of cleared entries.
        """
        conditions = [
            AgentMemory.workspace_id == workspace_id,
            AgentMemory.agent_id == agent_id,
            AgentMemory.memory_type == "working",
        ]
        if run_id:
            conditions.append(AgentMemory.simulation_run_id == run_id)

        stmt = delete(AgentMemory).where(*conditions).returning(AgentMemory.id)
        result = await self.db.execute(stmt)
        cleared = len(result.all())
        return cleared


# ── Helpers ──────────────────────────────────────────────────────────────────


def _memory_to_dict(mem: AgentMemory) -> dict:
    """Serialize an AgentMemory row to a JSON-friendly dict."""
    # Try to parse value as JSON, fall back to raw string
    try:
        value = json.loads(mem.value)
    except (json.JSONDecodeError, TypeError):
        value = mem.value

    metadata = None
    if mem.metadata_json:
        try:
            metadata = json.loads(mem.metadata_json)
        except (json.JSONDecodeError, TypeError):
            metadata = mem.metadata_json

    return {
        "id": str(mem.id),
        "agent_id": mem.agent_id,
        "memory_type": mem.memory_type,
        "key": mem.key,
        "value": value,
        "relevance_score": mem.relevance_score,
        "access_count": mem.access_count,
        "last_accessed_at": mem.last_accessed_at.isoformat() if mem.last_accessed_at else None,
        "expires_at": mem.expires_at.isoformat() if mem.expires_at else None,
        "simulation_run_id": str(mem.simulation_run_id) if mem.simulation_run_id else None,
        "metadata": metadata,
        "created_at": mem.created_at.isoformat() if mem.created_at else None,
        "updated_at": mem.updated_at.isoformat() if mem.updated_at else None,
    }
