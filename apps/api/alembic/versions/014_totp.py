"""add totp fields to users

Revision ID: 014
Revises: 013
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('totp_secret', sa.String(256), nullable=True))
    op.add_column('users', sa.Column('totp_enabled', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('totp_backup_codes', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('totp_pending', sa.Boolean(), nullable=False, server_default='0'))

def downgrade() -> None:
    op.drop_column('users', 'totp_pending')
    op.drop_column('users', 'totp_backup_codes')
    op.drop_column('users', 'totp_enabled')
    op.drop_column('users', 'totp_secret')
