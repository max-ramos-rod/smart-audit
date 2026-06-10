"""add submissions.asset_id (vínculo inspeção→ativo, DR-0002 Fase 1)

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-10
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'd2e3f4a5b6c7'
down_revision = 'c1d2e3f4a5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Aditivo e retrocompatível: NULL = inspeção sem ativo (comportamento atual).
    # Sem ON DELETE CASCADE — ativos são soft-deletados (ADR-0009/ADR-0015), nunca removidos;
    # o vínculo permanece legível nas inspeções históricas.
    op.add_column(
        'submissions',
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_submissions_asset_id',
        'submissions',
        'assets',
        ['asset_id'],
        ['id'],
    )
    op.create_index(
        'ix_submissions_company_asset', 'submissions', ['company_id', 'asset_id']
    )


def downgrade() -> None:
    op.drop_index('ix_submissions_company_asset', table_name='submissions')
    op.drop_constraint('fk_submissions_asset_id', 'submissions', type_='foreignkey')
    op.drop_column('submissions', 'asset_id')
