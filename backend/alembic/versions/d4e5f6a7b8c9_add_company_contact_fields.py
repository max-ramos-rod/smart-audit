"""add_company_contact_fields

Revision ID: d4e5f6a7b8c9
Revises: f73cae8e6de7
Create Date: 2026-05-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'f73cae8e6de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('companies', sa.Column('cnpj',          sa.String(18),  nullable=True))
    op.add_column('companies', sa.Column('timezone',       sa.String(50),  nullable=True, server_default='America/Sao_Paulo'))
    op.add_column('companies', sa.Column('contact_email',  sa.String(255), nullable=True))
    op.add_column('companies', sa.Column('phone',          sa.String(30),  nullable=True))


def downgrade() -> None:
    op.drop_column('companies', 'phone')
    op.drop_column('companies', 'contact_email')
    op.drop_column('companies', 'timezone')
    op.drop_column('companies', 'cnpj')
