"""remove evidence field type

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f7
Create Date: 2026-06-02

Evidence is now a capability of any field (attachments linked to any
submission_value), not a dedicated field type.
  1. Strip evidence-field keys from submissions.answers_json snapshots
  2. Delete submission_values for evidence fields (cascades to attachments)
  3. Delete the evidence form_fields themselves
  4. Update the CHECK constraint to exclude 'evidence'
"""
from alembic import op

revision = 'b3c4d5e6f7a8'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Remove evidence-field keys from the denormalised answers_json snapshot.
    #    Must run before deleting form_fields so we can still JOIN on them.
    op.execute("""
        UPDATE submissions s
        SET answers_json = COALESCE(
            (
                SELECT jsonb_object_agg(kv.key, kv.value)
                FROM jsonb_each(s.answers_json) AS kv(key, value)
                WHERE kv.key NOT IN (
                    SELECT ff.key
                    FROM form_fields ff
                    WHERE ff.field_type = 'evidence'
                      AND ff.form_version_id = s.form_version_id
                )
            ),
            '{}'::jsonb
        )
        WHERE EXISTS (
            SELECT 1
            FROM form_fields ff
            WHERE ff.field_type = 'evidence'
              AND ff.form_version_id = s.form_version_id
        )
    """)

    # 2. Delete submission_values for evidence fields.
    #    attachments rows cascade automatically (ondelete=CASCADE on submission_value_id FK).
    op.execute("""
        DELETE FROM submission_values
        WHERE form_field_id IN (
            SELECT id FROM form_fields WHERE field_type = 'evidence'
        )
    """)

    # 3. Delete the evidence form_fields.
    op.execute("DELETE FROM form_fields WHERE field_type = 'evidence'")

    # 4. Swap the CHECK constraint to exclude 'evidence'.
    op.drop_constraint('ck_form_fields_type', 'form_fields')
    op.create_check_constraint(
        'ck_form_fields_type',
        'form_fields',
        "field_type IN ('boolean', 'text', 'number', 'select', 'date', 'section')",
    )


def downgrade() -> None:
    # Restore the constraint only — deleted data cannot be recovered.
    op.drop_constraint('ck_form_fields_type', 'form_fields')
    op.create_check_constraint(
        'ck_form_fields_type',
        'form_fields',
        "field_type IN ('boolean', 'text', 'number', 'select', 'date', 'evidence', 'section')",
    )
