"""Add jira_tickets, onboarding_progress tables and Jira columns to workspace_settings

Revision ID: 013
Revises: 012
Create Date: 2026-03-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add Jira columns to workspace_settings ────────────────────────────────
    op.add_column("workspace_settings", sa.Column("jira_base_url", sa.String(500), nullable=True))
    op.add_column("workspace_settings", sa.Column("jira_email", sa.String(255), nullable=True))
    op.add_column("workspace_settings", sa.Column("jira_api_token", sa.String(500), nullable=True))
    op.add_column("workspace_settings", sa.Column("jira_project_key", sa.String(50), nullable=True))
    op.add_column(
        "workspace_settings",
        sa.Column("jira_issue_type", sa.String(50), nullable=False, server_default="Task"),
    )

    # ── Create jira_tickets table ─────────────────────────────────────────────
    op.create_table(
        "jira_tickets",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("canonical_findings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("jira_key", sa.String(50), nullable=False),
        sa.Column("jira_url", sa.String(500), nullable=False),
        sa.Column(
            "created_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
    op.create_index("ix_jira_tickets_finding_id", "jira_tickets", ["finding_id"])

    # ── Create onboarding_progress table ─────────────────────────────────────
    op.create_table(
        "onboarding_progress",
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
        sa.Column(
            "step_workspace_created", sa.Boolean, nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "step_aws_account_connected", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "step_first_sync_complete", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "step_team_member_invited", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "step_sla_configured", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "dismissed", sa.Boolean, nullable=False, server_default=sa.false()
        ),
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


def downgrade() -> None:
    op.drop_table("onboarding_progress")
    op.drop_index("ix_jira_tickets_finding_id", "jira_tickets")
    op.drop_table("jira_tickets")
    op.drop_column("workspace_settings", "jira_issue_type")
    op.drop_column("workspace_settings", "jira_project_key")
    op.drop_column("workspace_settings", "jira_api_token")
    op.drop_column("workspace_settings", "jira_email")
    op.drop_column("workspace_settings", "jira_base_url")
