"""add instruction to form fields

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-06-02
"""
import sqlalchemy as sa
from alembic import op

revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("form_fields", sa.Column("instruction", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("form_fields", "instruction")
