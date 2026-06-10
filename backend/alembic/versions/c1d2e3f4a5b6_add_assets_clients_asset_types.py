"""add assets, clients and asset_types

Revision ID: c1d2e3f4a5b6
Revises: b0c1d2e3f4a5
Create Date: 2026-06-08
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'c1d2e3f4a5b6'
down_revision = 'b0c1d2e3f4a5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'clients',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_clients_company_id', 'clients', ['company_id'])

    op.create_table(
        'asset_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('attributes_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_asset_types_company_id', 'asset_types', ['company_id'])

    op.create_table(
        'assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('asset_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('parent_asset_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('identifier', sa.String(length=180), nullable=False),
        sa.Column('attributes_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'active'"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['asset_type_id'], ['asset_types.id']),
        sa.ForeignKeyConstraint(['parent_asset_id'], ['assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('parent_asset_id IS NULL OR client_id IS NULL', name='ck_assets_client_only_on_root'),
        sa.CheckConstraint("status IN ('active', 'inactive', 'retired')", name='ck_assets_status'),
    )
    op.create_index('ix_assets_company_parent', 'assets', ['company_id', 'parent_asset_id'])
    op.create_index('ix_assets_company_type', 'assets', ['company_id', 'asset_type_id'])
    op.create_index('ix_assets_company_client', 'assets', ['company_id', 'client_id'])


def downgrade() -> None:
    op.drop_index('ix_assets_company_client', table_name='assets')
    op.drop_index('ix_assets_company_type', table_name='assets')
    op.drop_index('ix_assets_company_parent', table_name='assets')
    op.drop_table('assets')
    op.drop_index('ix_asset_types_company_id', table_name='asset_types')
    op.drop_table('asset_types')
    op.drop_index('ix_clients_company_id', table_name='clients')
    op.drop_table('clients')
