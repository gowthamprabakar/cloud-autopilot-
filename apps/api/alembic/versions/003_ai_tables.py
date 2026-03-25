"""AI insights and feedback tables

Revision ID: 003
Revises: 002
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── ai_insights ───────────────────────────────────────────────
    op.create_table(
        "ai_insights",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("canonical_findings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("prompt_template_id", sa.String(64), nullable=False),
        sa.Column("input_context_hash", sa.String(64), nullable=False),
        sa.Column("model_id", sa.String(64), nullable=False),
        sa.Column(
            "generation_status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("suggested_actions", JSONB, nullable=False, server_default="[]"),
        sa.Column("raw_response", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_insights_workspace_id", "ai_insights", ["workspace_id"])
    op.create_index("ix_ai_insights_finding_id", "ai_insights", ["finding_id"])
    op.create_unique_constraint(
        "uq_ai_insight_idempotency",
        "ai_insights",
        ["finding_id", "prompt_template_id", "input_context_hash"],
    )

    # ── ai_feedback ───────────────────────────────────────────────
    op.create_table(
        "ai_feedback",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "insight_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_insights.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("verdict", sa.String(16), nullable=False),
        sa.Column("edited_text", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ai_feedback_workspace_id", "ai_feedback", ["workspace_id"])
    op.create_index("ix_ai_feedback_insight_id", "ai_feedback", ["insight_id"])


def downgrade() -> None:
    op.drop_table("ai_feedback")
    op.drop_table("ai_insights")
