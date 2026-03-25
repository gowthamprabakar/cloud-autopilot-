"""AWS accounts, job runs, source findings, canonical findings

Revision ID: 002
Revises: 001
Create Date: 2026-03-14
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── aws_accounts ─────────────────────────────────────────────
    op.create_table(
        "aws_accounts",
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
        sa.Column("account_id", sa.String(12), nullable=False),
        sa.Column("account_alias", sa.String(64), nullable=True),
        sa.Column("role_arn", sa.Text, nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("last_synced_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
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
            nullable=False,
        ),
        sa.UniqueConstraint("workspace_id", "account_id", name="uq_aws_account_workspace_account"),
    )
    op.create_index("ix_aws_accounts_workspace_id", "aws_accounts", ["workspace_id"])
    op.create_index("ix_aws_accounts_status", "aws_accounts", ["status"])

    # ── job_runs ─────────────────────────────────────────────────
    op.create_table(
        "job_runs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "aws_account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("aws_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "triggered_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("job_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        # JSONB on Postgres; JSON on SQLite for tests
        sa.Column("progress_detail", JSONB, nullable=False, server_default="{}"),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            nullable=False,
        ),
    )
    op.create_index("ix_job_runs_aws_account_id", "job_runs", ["aws_account_id"])
    op.create_index("ix_job_runs_workspace_id", "job_runs", ["workspace_id"])
    op.create_index("ix_job_runs_job_type", "job_runs", ["job_type"])
    op.create_index("ix_job_runs_status", "job_runs", ["status"])

    # ── canonical_findings ───────────────────────────────────────
    # Create canonical_findings first (source_findings FK depends on it)
    op.create_table(
        "canonical_findings",
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
            "aws_account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("aws_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("primary_source", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("remediation", sa.Text, nullable=True),
        sa.Column("resource_arn", sa.Text, nullable=True),
        sa.Column("resource_type", sa.String(128), nullable=True),
        sa.Column("region", sa.String(32), nullable=True),
        sa.Column("compliance_frameworks", JSONB, nullable=False, server_default="[]"),
        sa.Column("tags", JSONB, nullable=False, server_default="{}"),
        sa.Column("first_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            nullable=False,
        ),
    )
    op.create_index("ix_canonical_findings_workspace_id", "canonical_findings", ["workspace_id"])
    op.create_index("ix_canonical_findings_aws_account_id", "canonical_findings", ["aws_account_id"])
    op.create_index("ix_canonical_findings_severity", "canonical_findings", ["severity"])
    op.create_index("ix_canonical_findings_status", "canonical_findings", ["status"])
    op.create_index("ix_canonical_findings_fingerprint", "canonical_findings", ["fingerprint"])
    op.create_index("ix_canonical_findings_resource_arn", "canonical_findings", ["resource_arn"])

    # ── source_findings ──────────────────────────────────────────
    op.create_table(
        "source_findings",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "aws_account_id",
            UUID(as_uuid=True),
            sa.ForeignKey("aws_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "canonical_finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("canonical_findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("native_finding_id", sa.Text, nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("raw_payload", JSONB, nullable=False, server_default="{}"),
        sa.Column("region", sa.String(32), nullable=True),
        sa.Column("resource_arn", sa.Text, nullable=True),
        sa.Column("resource_type", sa.String(128), nullable=True),
        sa.Column("first_observed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_observed_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            nullable=False,
        ),
        sa.UniqueConstraint(
            "aws_account_id", "native_finding_id",
            name="uq_source_finding_account_native",
        ),
    )
    op.create_index("ix_source_findings_aws_account_id", "source_findings", ["aws_account_id"])
    op.create_index("ix_source_findings_workspace_id", "source_findings", ["workspace_id"])
    op.create_index("ix_source_findings_canonical_finding_id", "source_findings", ["canonical_finding_id"])
    op.create_index("ix_source_findings_source", "source_findings", ["source"])
    op.create_index("ix_source_findings_severity", "source_findings", ["severity"])


def downgrade() -> None:
    op.drop_table("source_findings")
    op.drop_table("canonical_findings")
    op.drop_table("job_runs")
    op.drop_table("aws_accounts")
