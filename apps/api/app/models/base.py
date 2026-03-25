"""
Shared SQLAlchemy model mixin.

UUID PKs and timestamps use Python-side defaults so models work with
both PostgreSQL (production) and SQLite (test). Postgres's uuid_generate_v4()
extension is used only in the Alembic migration DDL (server-side default),
not in the ORM model definition.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
