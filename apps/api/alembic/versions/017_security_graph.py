"""add security graph tables (nodes, edges, attack paths)

Revision ID: 017
Revises: 016
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

revision = '017'
down_revision = '016'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── security_graph_nodes ──────────────────────────────────────────────
    op.create_table(
        'security_graph_nodes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column(
            'workspace_id', sa.String(36),
            sa.ForeignKey('workspaces.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'aws_account_id', sa.String(36),
            sa.ForeignKey('aws_accounts.id', ondelete='CASCADE'),
            nullable=True,
        ),
        sa.Column('node_type', sa.String(32), nullable=False),
        sa.Column('resource_arn', sa.Text(), nullable=True),
        sa.Column('resource_name', sa.String(256), nullable=True),
        sa.Column('region', sa.String(32), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('finding_ids', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('risk_score', sa.Float(), nullable=True),
        sa.Column('is_internet_facing', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_sensitive_data', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_sgn_workspace_id', 'security_graph_nodes', ['workspace_id'])
    op.create_index('ix_sgn_aws_account_id', 'security_graph_nodes', ['aws_account_id'])
    op.create_index('ix_sgn_node_type', 'security_graph_nodes', ['node_type'])
    op.create_index('ix_sgn_resource_arn', 'security_graph_nodes', ['resource_arn'])
    op.create_index('ix_sgn_is_internet_facing', 'security_graph_nodes', ['is_internet_facing'])
    op.create_index('ix_sgn_workspace_node_type', 'security_graph_nodes', ['workspace_id', 'node_type'])
    op.create_index('ix_sgn_workspace_internet_facing', 'security_graph_nodes', ['workspace_id', 'is_internet_facing'])

    # ── security_graph_edges ──────────────────────────────────────────────
    op.create_table(
        'security_graph_edges',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column(
            'workspace_id', sa.String(36),
            sa.ForeignKey('workspaces.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'source_node_id', sa.String(36),
            sa.ForeignKey('security_graph_nodes.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'target_node_id', sa.String(36),
            sa.ForeignKey('security_graph_nodes.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('edge_type', sa.String(64), nullable=False),
        sa.Column('is_attack_path', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('risk_contribution', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_sge_workspace_id', 'security_graph_edges', ['workspace_id'])
    op.create_index('ix_sge_source_node_id', 'security_graph_edges', ['source_node_id'])
    op.create_index('ix_sge_target_node_id', 'security_graph_edges', ['target_node_id'])
    op.create_index('ix_sge_edge_type', 'security_graph_edges', ['edge_type'])
    op.create_index('ix_sge_is_attack_path', 'security_graph_edges', ['is_attack_path'])
    op.create_index('ix_sge_workspace_attack_path', 'security_graph_edges', ['workspace_id', 'is_attack_path'])
    op.create_index('ix_sge_source_target', 'security_graph_edges', ['source_node_id', 'target_node_id'])

    # ── attack_paths ──────────────────────────────────────────────────────
    op.create_table(
        'attack_paths',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column(
            'workspace_id', sa.String(36),
            sa.ForeignKey('workspaces.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('name', sa.String(256), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(16), nullable=False),
        sa.Column('node_path', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('edge_path', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('toxic_combo_tags', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('blast_radius', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'entry_node_id', sa.String(36),
            sa.ForeignKey('security_graph_nodes.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column(
            'target_node_id', sa.String(36),
            sa.ForeignKey('security_graph_nodes.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('entry_description', sa.Text(), nullable=True),
        sa.Column('target_description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('related_finding_ids', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_ap_workspace_id', 'attack_paths', ['workspace_id'])
    op.create_index('ix_ap_severity', 'attack_paths', ['severity'])
    op.create_index('ix_ap_is_active', 'attack_paths', ['is_active'])
    op.create_index('ix_ap_entry_node_id', 'attack_paths', ['entry_node_id'])
    op.create_index('ix_ap_target_node_id', 'attack_paths', ['target_node_id'])
    op.create_index('ix_ap_workspace_active', 'attack_paths', ['workspace_id', 'is_active'])
    op.create_index('ix_ap_workspace_severity', 'attack_paths', ['workspace_id', 'severity'])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table('attack_paths')
    op.drop_table('security_graph_edges')
    op.drop_table('security_graph_nodes')
