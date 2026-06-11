"""attachments: ancora polimorfica por escopo (contract) — DR-0017

Fase CONTRACT do expand/contract. Aperta o schema apos a reescrita do
AttachmentService/Repository: company_id/scope viram NOT NULL, entra o CHECK
de consistencia scope x ancoras (via NOT VALID + VALIDATE, padrao seguro de
lock) e o vinculo legado submission_value_id e removido (Q7.1).

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f5a6b7c8d9e0"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)

_CHECK = (
    "(scope = 'component'  AND submission_id IS NOT NULL AND form_field_id IS NOT NULL "
    "AND asset_id IS NOT NULL) OR "
    "(scope = 'field'      AND submission_id IS NOT NULL AND form_field_id IS NOT NULL "
    "AND asset_id IS NULL) OR "
    "(scope = 'submission' AND submission_id IS NOT NULL AND form_field_id IS NULL "
    "AND asset_id IS NULL) OR "
    "(scope = 'asset'      AND submission_id IS NULL     AND form_field_id IS NULL "
    "AND asset_id IS NOT NULL)"
)


def upgrade() -> None:
    op.alter_column("attachments", "company_id", existing_type=_UUID, nullable=False)
    op.alter_column("attachments", "scope", existing_type=sa.Text(), nullable=False)

    # CHECK via NOT VALID + VALIDATE (evita lock ACCESS EXCLUSIVE prolongado em tabela grande).
    op.execute(
        f"ALTER TABLE attachments ADD CONSTRAINT ck_attachments_scope_anchor "
        f"CHECK ({_CHECK}) NOT VALID"
    )
    op.execute("ALTER TABLE attachments VALIDATE CONSTRAINT ck_attachments_scope_anchor")

    # Remove o vinculo legado (Q7.1). DROP COLUMN cascateia FK e indice dependentes.
    op.drop_column("attachments", "submission_value_id")


def downgrade() -> None:
    op.add_column("attachments", sa.Column("submission_value_id", _UUID, nullable=True))
    op.create_foreign_key(
        "attachments_submission_value_id_fkey", "attachments", "submission_values",
        ["submission_value_id"], ["id"], ondelete="CASCADE",
    )
    op.create_index("ix_attachments_submission_value_id", "attachments", ["submission_value_id"])
    # Best-effort: re-deriva o vinculo pela ancora (escopos sem value ficam NULL).
    op.execute(
        """
        UPDATE attachments AS a SET submission_value_id = sv.id
        FROM submission_values AS sv
        WHERE sv.submission_id = a.submission_id
          AND sv.form_field_id = a.form_field_id
          AND sv.asset_id IS NOT DISTINCT FROM a.asset_id
        """
    )

    op.drop_constraint("ck_attachments_scope_anchor", "attachments", type_="check")
    op.alter_column("attachments", "scope", existing_type=sa.Text(), nullable=True)
    op.alter_column("attachments", "company_id", existing_type=_UUID, nullable=True)
