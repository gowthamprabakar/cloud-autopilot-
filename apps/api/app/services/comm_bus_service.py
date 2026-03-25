"""
CommBusService — Cross-agent communication bus.

Sprint 30: Manages typed messages between agents during simulation.
Messages are persisted to DB and optionally broadcast via Redis pub/sub.
"""

from __future__ import annotations
import json, uuid
from datetime import datetime, UTC
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.comm_message import CommMessage


class CommBusService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def post_message(
        self,
        run_id: uuid.UUID,
        from_agent: str,
        to_agent: str,
        body: str,
        msg_type: str = "info",  # info/solution/alert/spawn/wiz
    ) -> CommMessage:
        """Post a new message to the communication bus."""
        # Get next sequence number
        result = await self.db.execute(
            select(func.coalesce(func.max(CommMessage.sequence_number), 0))
            .where(CommMessage.simulation_run_id == run_id)
        )
        next_seq = result.scalar() + 1

        msg = CommMessage(
            simulation_run_id=run_id,
            from_agent_id=from_agent,
            to_agent_id=to_agent,
            message_type=msg_type,
            body=body[:2000],  # cap message length
            sequence_number=next_seq,
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def get_messages(
        self,
        run_id: uuid.UUID,
        after_seq: int = 0,
        limit: int = 200,
    ) -> list[CommMessage]:
        """Get messages for a run, optionally after a sequence number (for polling)."""
        result = await self.db.execute(
            select(CommMessage)
            .where(CommMessage.simulation_run_id == run_id)
            .where(CommMessage.sequence_number > after_seq)
            .order_by(CommMessage.sequence_number.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_audit_log(self, run_id: uuid.UUID) -> list[dict]:
        """Export full audit log as structured dicts for compliance."""
        messages = await self.get_messages(run_id, limit=10000)
        return [
            {
                "sequence": m.sequence_number,
                "timestamp": m.created_at.isoformat() if hasattr(m.created_at, 'isoformat') else str(m.created_at),
                "from": m.from_agent_id,
                "to": m.to_agent_id,
                "type": m.message_type,
                "body": m.body,
            }
            for m in messages
        ]

    async def message_count(self, run_id: uuid.UUID) -> int:
        """Count total messages in a simulation run."""
        result = await self.db.execute(
            select(func.count(CommMessage.id))
            .where(CommMessage.simulation_run_id == run_id)
        )
        return result.scalar() or 0
