"""add_updated_at_to_metadata_tables

Revision ID: 8aeb51c1026f
Revises: 332b89327dc7
Create Date: 2026-03-13 17:06:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8aeb51c1026f'
down_revision: Union[str, Sequence[str], None] = '332b89327dc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.add_column(
        'memberships',
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.add_column(
        'form_versions',
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.add_column(
        'attachments',
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )



def downgrade() -> None:
    op.drop_column('attachments', 'updated_at')
    op.drop_column('form_versions', 'updated_at')
    op.drop_column('memberships', 'updated_at')