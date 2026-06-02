"""remove photo field type

Revision ID: a1b2c3d4e5f7
Revises: f73cae8e6de7
Create Date: 2026-06-02

Remove the 'photo' field type entirely:
  1. Strip photo-field keys from submissions.answers_json snapshots
  2. Delete submission_values for photo fields (cascades to attachments)
  3. Delete the photo form_fields themselves
  4. Update the CHECK constraint to exclude 'photo'
"""
from alembic import op

revision = 'a1b2c3d4e5f7'
down_revision = 'f73cae8e6de7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Remove photo-field keys from the denormalised answers_json snapshot.
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
                    WHERE ff.field_type = 'photo'
                      AND ff.form_version_id = s.form_version_id
                )
            ),
            '{}'::jsonb
        )
        WHERE EXISTS (
            SELECT 1
            FROM form_fields ff
            WHERE ff.field_type = 'photo'
              AND ff.form_version_id = s.form_version_id
        )
    """)

    # 2. Delete submission_values for photo fields.
    #    attachments rows cascade automatically (ondelete=CASCADE on submission_value_id FK).
    op.execute("""
        DELETE FROM submission_values
        WHERE form_field_id IN (
            SELECT id FROM form_fields WHERE field_type = 'photo'
        )
    """)

    # 3. Delete the photo form_fields.
    op.execute("DELETE FROM form_fields WHERE field_type = 'photo'")

    # 4. Swap the CHECK constraint to exclude 'photo'.
    op.drop_constraint('ck_form_fields_type', 'form_fields')
    op.create_check_constraint(
        'ck_form_fields_type',
        'form_fields',
        "field_type IN ('boolean', 'text', 'number', 'select', 'date', 'evidence', 'section')",
    )


def downgrade() -> None:
    # Restore the constraint only — deleted data cannot be recovered.
    op.drop_constraint('ck_form_fields_type', 'form_fields')
    op.create_check_constraint(
        'ck_form_fields_type',
        'form_fields',
        "field_type IN ('boolean', 'text', 'number', 'select', 'date', 'photo', 'evidence', 'section')",
    )
