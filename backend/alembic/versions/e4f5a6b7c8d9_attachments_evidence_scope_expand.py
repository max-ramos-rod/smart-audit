"""attachments: ancora polimorfica por escopo (expand) — DR-0017

Fase EXPAND do expand/contract da ADR-0017. Adiciona a ancora polimorfica
(scope + company_id + submission_id/form_field_id/asset_id + component_label +
metadata_json) e backfilla as linhas existentes, mantendo submission_value_id
temporariamente (relaxado para nullable) para nao quebrar service/repository.

A fase CONTRACT (SET NOT NULL em company_id/scope, CHECK de consistencia por
scope, DROP submission_value_id) entra na migration seguinte, junto com a
reescrita do AttachmentService/Repository (etapa 3-4 da ADR-0017).

Revision ID: e4f5a6b7c8d9
Revises: e3f4a5b6c7d8
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e4f5a6b7c8d9"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    # 1. Colunas novas (todas nullable nesta fase — CONTRACT aperta depois).
    op.add_column("attachments", sa.Column("company_id", _UUID, nullable=True))
    op.add_column("attachments", sa.Column("scope", sa.Text(), nullable=True))
    op.add_column("attachments", sa.Column("submission_id", _UUID, nullable=True))
    op.add_column("attachments", sa.Column("form_field_id", _UUID, nullable=True))
    op.add_column("attachments", sa.Column("asset_id", _UUID, nullable=True))
    op.add_column("attachments", sa.Column("component_label", sa.Text(), nullable=True))
    op.add_column("attachments", sa.Column("metadata_json", postgresql.JSONB(), nullable=True))

    # 2. Relaxa submission_value_id para nullable (deprecado; removido no CONTRACT).
    op.alter_column(
        "attachments", "submission_value_id", existing_type=_UUID, nullable=True
    )

    # 3. FKs das novas ancoras. submissions com CASCADE (Q7.2); asset sem CASCADE (soft delete).
    op.create_foreign_key(
        "fk_attachments_company", "attachments", "companies", ["company_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_attachments_submission", "attachments", "submissions",
        ["submission_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_attachments_form_field", "attachments", "form_fields", ["form_field_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_attachments_asset", "attachments", "assets", ["asset_id"], ["id"]
    )

    # 4. Backfill a partir do vinculo atual (Attachment -> SubmissionValue -> Submission).
    #    asset_id e' NULL em todo o historico -> scope='field'.
    op.execute(
        """
        UPDATE attachments AS a SET
            submission_id = sv.submission_id,
            form_field_id = sv.form_field_id,
            asset_id      = sv.asset_id,
            company_id    = s.company_id,
            scope         = CASE WHEN sv.asset_id IS NOT NULL THEN 'component' ELSE 'field' END
        FROM submission_values AS sv
        JOIN submissions AS s ON s.id = sv.submission_id
        WHERE a.submission_value_id = sv.id
        """
    )

    # 5. Indices NAO-UNICOS (INV-E1 / Q7.3 — nenhum UNIQUE pode tocar a ancora).
    op.create_index("ix_attachments_submission_id", "attachments", ["submission_id"])
    op.create_index("ix_attachments_asset_id", "attachments", ["asset_id"])
    op.create_index("ix_attachments_company_id", "attachments", ["company_id"])
    op.create_index(
        "ix_attachments_submission_field_asset",
        "attachments",
        ["submission_id", "form_field_id", "asset_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_attachments_submission_field_asset", table_name="attachments")
    op.drop_index("ix_attachments_company_id", table_name="attachments")
    op.drop_index("ix_attachments_asset_id", table_name="attachments")
    op.drop_index("ix_attachments_submission_id", table_name="attachments")

    op.drop_constraint("fk_attachments_asset", "attachments", type_="foreignkey")
    op.drop_constraint("fk_attachments_form_field", "attachments", type_="foreignkey")
    op.drop_constraint("fk_attachments_submission", "attachments", type_="foreignkey")
    op.drop_constraint("fk_attachments_company", "attachments", type_="foreignkey")

    # Restaura submission_value_id NOT NULL (o vinculo nunca foi removido nesta fase).
    op.alter_column(
        "attachments", "submission_value_id", existing_type=_UUID, nullable=False
    )

    op.drop_column("attachments", "metadata_json")
    op.drop_column("attachments", "component_label")
    op.drop_column("attachments", "asset_id")
    op.drop_column("attachments", "form_field_id")
    op.drop_column("attachments", "submission_id")
    op.drop_column("attachments", "scope")
    op.drop_column("attachments", "company_id")
