CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(120) NOT NULL UNIQUE,
    plan VARCHAR(50) NOT NULL DEFAULT 'starter',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_memberships_company_user UNIQUE (company_id, user_id),
    CONSTRAINT ck_memberships_role CHECK (role IN ('OWNER', 'ADMIN', 'MANAGER', 'INSPECTOR', 'VIEWER'))
);

CREATE TABLE forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE form_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id UUID NOT NULL REFERENCES forms(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    published_at TIMESTAMPTZ NULL,
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_form_versions_form_version UNIQUE (form_id, version),
    CONSTRAINT ck_form_versions_status CHECK (status IN ('draft', 'published', 'archived'))
);

CREATE TABLE form_fields (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_version_id UUID NOT NULL REFERENCES form_versions(id) ON DELETE CASCADE,
    key VARCHAR(100) NOT NULL,
    label VARCHAR(180) NOT NULL,
    field_type VARCHAR(30) NOT NULL,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    position INTEGER NOT NULL,
    config_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_form_fields_version_key UNIQUE (form_version_id, key),
    CONSTRAINT uq_form_fields_version_position UNIQUE (form_version_id, position),
    CONSTRAINT ck_form_fields_type CHECK (field_type IN ('boolean', 'text', 'number', 'select', 'date', 'photo'))
);

CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    form_version_id UUID NOT NULL REFERENCES form_versions(id),
    created_by UUID NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    score NUMERIC(5,2) NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ NULL,
    answers_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_submissions_status CHECK (status IN ('draft', 'in_progress', 'completed', 'cancelled'))
);

CREATE TABLE submission_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    form_field_id UUID NOT NULL REFERENCES form_fields(id),
    value_text TEXT NULL,
    value_number NUMERIC(14,4) NULL,
    value_boolean BOOLEAN NULL,
    value_date DATE NULL,
    value_json JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_submission_values_submission_field UNIQUE (submission_id, form_field_id)
);

CREATE TABLE attachments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_value_id UUID NOT NULL REFERENCES submission_values(id) ON DELETE CASCADE,
    file_url TEXT NOT NULL,
    thumbnail_url TEXT NULL,
    mime_type VARCHAR(120) NOT NULL,
    file_size BIGINT NOT NULL,
    uploaded_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_memberships_company_id ON memberships(company_id);
CREATE INDEX ix_memberships_user_id ON memberships(user_id);

CREATE INDEX ix_forms_company_id ON forms(company_id);
CREATE INDEX ix_forms_company_active ON forms(company_id, is_active);

CREATE INDEX ix_form_versions_form_id ON form_versions(form_id);
CREATE INDEX ix_form_versions_status ON form_versions(status);

CREATE INDEX ix_form_fields_form_version_id ON form_fields(form_version_id);

CREATE INDEX ix_submissions_company_id ON submissions(company_id);
CREATE INDEX ix_submissions_form_version_id ON submissions(form_version_id);
CREATE INDEX ix_submissions_created_by ON submissions(created_by);
CREATE INDEX ix_submissions_status ON submissions(status);
CREATE INDEX ix_submissions_company_status_created_at ON submissions(company_id, status, created_at DESC);

CREATE INDEX ix_submission_values_submission_id ON submission_values(submission_id);
CREATE INDEX ix_submission_values_form_field_id ON submission_values(form_field_id);

CREATE INDEX ix_attachments_submission_value_id ON attachments(submission_value_id);
CREATE INDEX ix_attachments_uploaded_by ON attachments(uploaded_by);
