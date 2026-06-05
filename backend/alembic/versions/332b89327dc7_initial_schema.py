"""initial_schema

Revision ID: 332b89327dc7
Revises:
Create Date: 2026-03-13 13:23:39.011137

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '332b89327dc7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


role_check = "role IN ('OWNER', 'ADMIN', 'MANAGER', 'INSPECTOR', 'VIEWER')"
form_version_status_check = "status IN ('draft', 'published', 'archived')"
form_field_type_check = "field_type IN ('boolean', 'text', 'number', 'select', 'date', 'photo')"
submission_status_check = "status IN ('draft', 'in_progress', 'completed', 'cancelled')"



def upgrade() -> None:
    """Upgrade schema."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
    )

    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=120), nullable=False),
        sa.Column('plan', sa.String(length=50), server_default=sa.text("'starter'"), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )

    op.create_table(
        'memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(role_check, name='ck_memberships_role'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', 'user_id', name='uq_memberships_company_user'),
    )

    op.create_table(
        'forms',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=180), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_forms_company_id', 'forms', ['company_id'])
    op.create_index('ix_forms_company_active', 'forms', ['company_id', 'is_active'])

    op.create_table(
        'form_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('form_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(form_version_status_check, name='ck_form_versions_status'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('form_id', 'version', name='uq_form_versions_form_version'),
    )
    op.create_index('ix_form_versions_form_id', 'form_versions', ['form_id'])
    op.create_index('ix_form_versions_status', 'form_versions', ['status'])

    op.create_table(
        'form_fields',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('form_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=180), nullable=False),
        sa.Column('field_type', sa.String(length=30), nullable=False),
        sa.Column('required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(form_field_type_check, name='ck_form_fields_type'),
        sa.ForeignKeyConstraint(['form_version_id'], ['form_versions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('form_version_id', 'key', name='uq_form_fields_version_key'),
        sa.UniqueConstraint('form_version_id', 'position', name='uq_form_fields_version_position'),
    )
    op.create_index('ix_form_fields_form_version_id', 'form_fields', ['form_version_id'])

    op.create_table(
        'submissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('form_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(length=20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column('score', sa.Numeric(5, 2), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('answers_json', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(submission_status_check, name='ck_submissions_status'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id']),
        sa.ForeignKeyConstraint(['form_version_id'], ['form_versions.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_submissions_company_id', 'submissions', ['company_id'])
    op.create_index('ix_submissions_form_version_id', 'submissions', ['form_version_id'])
    op.create_index('ix_submissions_created_by', 'submissions', ['created_by'])
    op.create_index('ix_submissions_status', 'submissions', ['status'])
    op.create_index('ix_submissions_company_status_created_at', 'submissions', ['company_id', 'status', 'created_at'])

    op.create_table(
        'submission_values',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('submission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('form_field_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('value_text', sa.Text(), nullable=True),
        sa.Column('value_number', sa.Numeric(14, 4), nullable=True),
        sa.Column('value_boolean', sa.Boolean(), nullable=True),
        sa.Column('value_date', sa.Date(), nullable=True),
        sa.Column('value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['form_field_id'], ['form_fields.id']),
        sa.ForeignKeyConstraint(['submission_id'], ['submissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('submission_id', 'form_field_id', name='uq_submission_values_submission_field'),
    )
    op.create_index('ix_submission_values_submission_id', 'submission_values', ['submission_id'])
    op.create_index('ix_submission_values_form_field_id', 'submission_values', ['form_field_id'])

    op.create_table(
        'attachments',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('submission_value_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_url', sa.Text(), nullable=False),
        sa.Column('thumbnail_url', sa.Text(), nullable=True),
        sa.Column('mime_type', sa.String(length=120), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['submission_value_id'], ['submission_values.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_attachments_submission_value_id', 'attachments', ['submission_value_id'])
    op.create_index('ix_attachments_uploaded_by', 'attachments', ['uploaded_by'])



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_attachments_uploaded_by', table_name='attachments')
    op.drop_index('ix_attachments_submission_value_id', table_name='attachments')
    op.drop_table('attachments')

    op.drop_index('ix_submission_values_form_field_id', table_name='submission_values')
    op.drop_index('ix_submission_values_submission_id', table_name='submission_values')
    op.drop_table('submission_values')

    op.drop_index('ix_submissions_company_status_created_at', table_name='submissions')
    op.drop_index('ix_submissions_status', table_name='submissions')
    op.drop_index('ix_submissions_created_by', table_name='submissions')
    op.drop_index('ix_submissions_form_version_id', table_name='submissions')
    op.drop_index('ix_submissions_company_id', table_name='submissions')
    op.drop_table('submissions')

    op.drop_index('ix_form_fields_form_version_id', table_name='form_fields')
    op.drop_table('form_fields')

    op.drop_index('ix_form_versions_status', table_name='form_versions')
    op.drop_index('ix_form_versions_form_id', table_name='form_versions')
    op.drop_table('form_versions')

    op.drop_index('ix_forms_company_active', table_name='forms')
    op.drop_index('ix_forms_company_id', table_name='forms')
    op.drop_table('forms')

    op.drop_table('memberships')
    op.drop_table('companies')
    op.drop_table('users')
