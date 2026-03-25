"""
PromptRegistry — versioned AI prompt templates (Sprint 26).

Stores prompt templates with workspace-level overrides.
Global prompts (workspace_id=NULL) serve as defaults;
workspace-specific prompts override them by name.
"""

import uuid

from sqlalchemy import Boolean, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPKMixin


class PromptRegistry(Base, UUIDPKMixin, TimestampMixin):
    """A versioned prompt template for AI insight generation."""

    __tablename__ = "prompt_registry"

    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "name",
            "version",
            name="uq_prompt_registry_ws_name_version",
        ),
    )

    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    template: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(
        String(64), nullable=False, default="bedrock/claude-3-sonnet"
    )
    category: Mapped[str] = mapped_column(
        String(64), nullable=False, default="general"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Optional JSON config blob (e.g. temperature, max_tokens overrides)
    metadata_json: Mapped[str | None] = mapped_column(
        "metadata", Text, nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<PromptRegistry name={self.name!r} v{self.version} "
            f"ws={self.workspace_id}>"
        )
