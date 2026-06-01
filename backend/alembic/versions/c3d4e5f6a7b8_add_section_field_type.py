"""add section field type

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-31

"""

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_form_fields_type", "form_fields", type_="check")
    op.create_check_constraint(
        "ck_form_fields_type",
        "form_fields",
        "field_type IN ('boolean', 'text', 'number', 'select', 'date', 'photo', 'evidence', 'section')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_form_fields_type", "form_fields", type_="check")
    op.create_check_constraint(
        "ck_form_fields_type",
        "form_fields",
        "field_type IN ('boolean', 'text', 'number', 'select', 'date', 'photo', 'evidence')",
    )
