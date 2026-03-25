"""add finding_intelligence table

Revision ID: 016
Revises: 015
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = '016'
down_revision = '015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'finding_intelligence',
        # Primary key
        sa.Column('id', sa.String(36), primary_key=True),

        # Tenant + finding scope
        sa.Column(
            'workspace_id',
            sa.String(36),
            sa.ForeignKey('workspaces.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'finding_id',
            sa.String(36),
            sa.ForeignKey('canonical_findings.id', ondelete='CASCADE'),
            nullable=False,
            unique=True,
        ),

        # Descriptive layer (Ollama / fallback templates)
        sa.Column('what_is_it', sa.Text(), nullable=True),
        sa.Column('current_state', sa.Text(), nullable=True),
        sa.Column('expected_state', sa.Text(), nullable=True),
        sa.Column('business_impact', sa.Text(), nullable=True),
        sa.Column('attack_scenario', sa.Text(), nullable=True),

        # Causal analysis
        sa.Column('composite_score', sa.Float(), nullable=True),
        sa.Column('primary_root_cause', sa.String(64), nullable=True),
        sa.Column('causal_factors', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('causal_chain', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('toxic_combinations', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('blast_radius_count', sa.Integer(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),

        # RAG scoring
        sa.Column('rag_level', sa.String(8), nullable=True),
        sa.Column('rag_composite_score', sa.Float(), nullable=True),
        sa.Column('rag_primary_reason', sa.Text(), nullable=True),
        sa.Column('sla_days', sa.Integer(), nullable=True),
        sa.Column('escalation_required', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('stakeholders', sa.JSON(), nullable=False, server_default='[]'),

        # Prioritised actions
        sa.Column('immediate_actions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('sprint_actions', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('quarterly_actions', sa.JSON(), nullable=False, server_default='[]'),

        # Generation metadata
        sa.Column('ollama_model', sa.String(64), nullable=True),
        sa.Column('fallback_used', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('generation_status', sa.String(16), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),

        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
    )

    # Indexes for common query patterns
    op.create_index(
        'ix_finding_intelligence_workspace_id',
        'finding_intelligence',
        ['workspace_id'],
    )
    op.create_index(
        'ix_finding_intelligence_finding_id',
        'finding_intelligence',
        ['finding_id'],
        unique=True,
    )
    op.create_index(
        'ix_finding_intelligence_rag_level',
        'finding_intelligence',
        ['workspace_id', 'rag_level'],
    )


def downgrade() -> None:
    op.drop_index('ix_finding_intelligence_rag_level', table_name='finding_intelligence')
    op.drop_index('ix_finding_intelligence_finding_id', table_name='finding_intelligence')
    op.drop_index('ix_finding_intelligence_workspace_id', table_name='finding_intelligence')
    op.drop_table('finding_intelligence')
