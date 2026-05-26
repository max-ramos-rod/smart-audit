-- Execute este script com um usuario administrador do PostgreSQL.
-- Objetivo: transferir ownership dos objetos do banco smart_audit para smart_audit_app.

ALTER DATABASE smart_audit OWNER TO smart_audit_app;
ALTER SCHEMA public OWNER TO smart_audit_app;

ALTER TABLE public.users OWNER TO smart_audit_app;
ALTER TABLE public.companies OWNER TO smart_audit_app;
ALTER TABLE public.memberships OWNER TO smart_audit_app;
ALTER TABLE public.forms OWNER TO smart_audit_app;
ALTER TABLE public.form_versions OWNER TO smart_audit_app;
ALTER TABLE public.form_fields OWNER TO smart_audit_app;
ALTER TABLE public.submissions OWNER TO smart_audit_app;
ALTER TABLE public.submission_values OWNER TO smart_audit_app;
ALTER TABLE public.attachments OWNER TO smart_audit_app;
ALTER TABLE public.alembic_version OWNER TO smart_audit_app;

ALTER INDEX public.users_email_key OWNER TO smart_audit_app;
ALTER INDEX public.companies_slug_key OWNER TO smart_audit_app;
ALTER INDEX public.uq_memberships_company_user OWNER TO smart_audit_app;
ALTER INDEX public.ix_memberships_company_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_memberships_user_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_forms_company_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_forms_company_active OWNER TO smart_audit_app;
ALTER INDEX public.uq_form_versions_form_version OWNER TO smart_audit_app;
ALTER INDEX public.ix_form_versions_form_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_form_versions_status OWNER TO smart_audit_app;
ALTER INDEX public.uq_form_fields_version_key OWNER TO smart_audit_app;
ALTER INDEX public.uq_form_fields_version_position OWNER TO smart_audit_app;
ALTER INDEX public.ix_form_fields_form_version_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_submissions_company_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_submissions_form_version_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_submissions_created_by OWNER TO smart_audit_app;
ALTER INDEX public.ix_submissions_status OWNER TO smart_audit_app;
ALTER INDEX public.ix_submissions_company_status_created_at OWNER TO smart_audit_app;
ALTER INDEX public.uq_submission_values_submission_field OWNER TO smart_audit_app;
ALTER INDEX public.ix_submission_values_submission_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_submission_values_form_field_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_attachments_submission_value_id OWNER TO smart_audit_app;
ALTER INDEX public.ix_attachments_uploaded_by OWNER TO smart_audit_app;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO smart_audit_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO smart_audit_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO smart_audit_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO smart_audit_app;