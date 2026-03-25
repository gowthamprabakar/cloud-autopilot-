"""018_scan_jobs

Revision ID: 018
Revises: 017
Create Date: 2026-03-16

Creates scan_jobs table for tracking AWS scanner ingestion runs.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("aws_account_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="running"),
        sa.Column("triggered_by", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("findings_added", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("findings_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sources_scanned", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("sources_failed", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_scan_jobs_workspace_id", "scan_jobs", ["workspace_id"])
    op.create_index("ix_scan_jobs_status", "scan_jobs", ["status"])
    op.create_index("ix_scan_jobs_started_at", "scan_jobs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_scan_jobs_started_at", table_name="scan_jobs")
    op.drop_index("ix_scan_jobs_status", table_name="scan_jobs")
    op.drop_index("ix_scan_jobs_workspace_id", table_name="scan_jobs")
    op.drop_table("scan_jobs")
