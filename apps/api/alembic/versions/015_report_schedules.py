"""add report_schedules table

Revision ID: 015
Revises: 014
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = '015'
down_revision = '014'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'report_schedules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('workspace_id', sa.String(36), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('frequency', sa.String(20), nullable=False, server_default='weekly'),
        sa.Column('day_of_week', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('recipients', sa.Text(), nullable=True),
        sa.Column('last_sent_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('report_schedules')
