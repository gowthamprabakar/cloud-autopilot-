"""Add enabled_regions to aws_accounts; add ai_summarize job type support

Revision ID: 004
Revises: 003
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add enabled_regions column with default ["us-east-1"]
    op.add_column(
        "aws_accounts",
        sa.Column(
            "enabled_regions",
            JSONB,
            nullable=False,
            server_default=sa.text('\'["us-east-1"]\'::jsonb'),
        ),
    )


def downgrade() -> None:
    op.drop_column("aws_accounts", "enabled_regions")
