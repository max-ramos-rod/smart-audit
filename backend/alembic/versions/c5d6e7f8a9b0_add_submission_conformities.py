"""add submission conformities

Revision ID: c5d6e7f8a9b0
Revises: b3c4d5e6f7a8
Create Date: 2026-06-02
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'c5d6e7f8a9b0'
down_revision = 'b3c4d5e6f7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'submission_conformities',
        sa.Column('id', postgresql.UUID(as_uuid=False), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('submission_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('form_field_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['form_field_id'], ['form_fields.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id', 'form_field_id', name='uq_submission_conformities_submission_field'),
        sa.CheckConstraint("status IN ('conforme', 'nao_conforme')", name='ck_submission_conformities_status'),
    )
    op.create_index('ix_submission_conformities_submission_id', 'submission_conformities', ['submission_id'])


def downgrade() -> None:
    op.drop_index('ix_submission_conformities_submission_id', table_name='submission_conformities')
    op.drop_table('submission_conformities')
