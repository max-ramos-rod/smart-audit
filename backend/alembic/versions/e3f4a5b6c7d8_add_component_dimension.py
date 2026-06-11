"""add component dimension (DR-0002 Fases 2-4, ADR-0016)

Adiciona a dimensão de componente ao modelo híbrido:
- form_fields.component_type_id  (escopo do campo; NULL = campo geral)
- submission_values.asset_id     (componente respondido; NULL = comportamento atual)
- submission_conformities.asset_id
- submissions.components_snapshot (identidade congelada por componente)
e troca os UNIQUE de (submission_id, form_field_id) para incluir asset_id.

Aditiva e reversível. Os novos UNIQUE usam NULLS NOT DISTINCT (PG 15+): NULL é tratado
como igual, então o histórico (asset_id NULL) continua com UMA linha por
(submission_id, form_field_id) — preservando a garantia do constraint antigo — enquanto
componentes distintos (asset_id não-nulo) coexistem no mesmo campo. (O padrão NULLS
DISTINCT permitiria múltiplos NULLs e perderia essa garantia — regressão; ver ADR-0016.)
Sem ON DELETE CASCADE nos FKs de asset_id — ativos são soft-deletados (ADR-0009/0015).

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-06-11
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- form_fields.component_type_id (escopo de componente; parte da versão imutável) ---
    op.add_column(
        'form_fields',
        sa.Column('component_type_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_form_fields_component_type_id',
        'form_fields',
        'asset_types',
        ['component_type_id'],
        ['id'],
    )
    op.create_index(
        'ix_form_fields_component_type', 'form_fields', ['component_type_id']
    )

    # --- submission_values.asset_id + nova unicidade ---
    op.add_column(
        'submission_values',
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_submission_values_asset_id',
        'submission_values',
        'assets',
        ['asset_id'],
        ['id'],
    )
    op.create_index(
        'ix_submission_values_asset', 'submission_values', ['asset_id']
    )
    op.drop_constraint(
        'uq_submission_values_submission_field', 'submission_values', type_='unique'
    )
    op.create_unique_constraint(
        'uq_submission_values_submission_field_asset',
        'submission_values',
        ['submission_id', 'form_field_id', 'asset_id'],
        postgresql_nulls_not_distinct=True,
    )

    # --- submission_conformities.asset_id + nova unicidade ---
    op.add_column(
        'submission_conformities',
        sa.Column('asset_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        'fk_submission_conformities_asset_id',
        'submission_conformities',
        'assets',
        ['asset_id'],
        ['id'],
    )
    op.create_index(
        'ix_submission_conformities_asset', 'submission_conformities', ['asset_id']
    )
    op.drop_constraint(
        'uq_submission_conformities_submission_field',
        'submission_conformities',
        type_='unique',
    )
    op.create_unique_constraint(
        'uq_submission_conformities_submission_field_asset',
        'submission_conformities',
        ['submission_id', 'form_field_id', 'asset_id'],
        postgresql_nulls_not_distinct=True,
    )

    # --- submissions.components_snapshot (identidade congelada; Q1.1 / ADR-0016) ---
    op.add_column(
        'submissions',
        sa.Column('components_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('submissions', 'components_snapshot')

    op.drop_constraint(
        'uq_submission_conformities_submission_field_asset',
        'submission_conformities',
        type_='unique',
    )
    op.create_unique_constraint(
        'uq_submission_conformities_submission_field',
        'submission_conformities',
        ['submission_id', 'form_field_id'],
    )
    op.drop_index('ix_submission_conformities_asset', table_name='submission_conformities')
    op.drop_constraint(
        'fk_submission_conformities_asset_id', 'submission_conformities', type_='foreignkey'
    )
    op.drop_column('submission_conformities', 'asset_id')

    op.drop_constraint(
        'uq_submission_values_submission_field_asset', 'submission_values', type_='unique'
    )
    op.create_unique_constraint(
        'uq_submission_values_submission_field',
        'submission_values',
        ['submission_id', 'form_field_id'],
    )
    op.drop_index('ix_submission_values_asset', table_name='submission_values')
    op.drop_constraint('fk_submission_values_asset_id', 'submission_values', type_='foreignkey')
    op.drop_column('submission_values', 'asset_id')

    op.drop_index('ix_form_fields_component_type', table_name='form_fields')
    op.drop_constraint('fk_form_fields_component_type_id', 'form_fields', type_='foreignkey')
    op.drop_column('form_fields', 'component_type_id')
