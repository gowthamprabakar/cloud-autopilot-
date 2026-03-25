"""Add workspace_settings table

Revision ID: 012
Revises: 010
Create Date: 2026-03-15

Note: This branches from 010 in parallel with 011_finding_assignments.
For production these two branches need to be merged before deployment.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "012"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspace_settings",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("sla_days_critical", sa.Integer, nullable=False, server_default="3"),
        sa.Column("sla_days_high", sa.Integer, nullable=False, server_default="7"),
        sa.Column("sla_days_medium", sa.Integer, nullable=False, server_default="30"),
        sa.Column("sla_days_low", sa.Integer, nullable=False, server_default="90"),
        sa.Column("sla_days_info", sa.Integer, nullable=False, server_default="180"),
        sa.Column("finding_auto_close_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_workspace_settings_workspace_id", "workspace_settings", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_settings_workspace_id", "workspace_settings")
    op.drop_table("workspace_settings")
