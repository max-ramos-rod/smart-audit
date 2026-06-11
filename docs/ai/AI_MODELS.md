# AI_MODELS — Mapa do modelo de dados

Resumo verificado em `backend/app/db/models/` e nas migrations
(`backend/alembic/versions/`). Fonte completa: `docs/DER_Smart_Audit.md`. Toda entidade
herda `UUIDPrimaryKeyMixin` (PK `uuid` com `gen_random_uuid()`); a maioria herda
`TimestampMixin` (`created_at`/`updated_at`) — **exceção: `audit_logs`** (imutável, só
`created_at`).

## Entidades por contexto

### Acesso
- `users` — `name`, `email` (único global), `password_hash` (PBKDF2-SHA256), `is_active`.
- `companies` — `name`, `slug` (único), `plan`, `is_active`, `cnpj`, `timezone`, `contact_email`, `phone`.
- `memberships` — `company_id`, `user_id`, `role`, `revoked_at` (NULL = ativo). `UNIQUE(company_id, user_id)`; `CHECK role IN (OWNER, ADMIN, MANAGER, INSPECTOR, VIEWER)`.
- `password_reset_tokens` — `user_id` (CASCADE), `token` (único, `secrets.token_urlsafe(32)`), `expires_at`, `used_at`. Reusada para reset (TTL 1h) **e** convite (TTL `invite_token_ttl_hours`, default 72h).
- `notification_reads` — `user_id` (CASCADE), `notification_key`, `dismissed` (bool). `UNIQUE(user_id, notification_key)`. **Não tem coluna `read`** (ver decisões).

### Formulários
- `forms` — `company_id`, `name`, `description`, `is_active`, `created_by`.
- `form_versions` — `form_id`, `version`, `status`, `published_at`, `created_by`. `UNIQUE(form_id, version)`; `CHECK status IN (draft, published, archived)`.
- `form_fields` — `form_version_id`, `key`, `label`, `field_type`, `required`, `position`, `config_json` (JSONB), `instruction` (TEXT NULL). `UNIQUE(form_version_id, key)`; `UNIQUE(form_version_id, position)`; `CHECK field_type IN (boolean, text, number, select, date, section)`.

### Inspeções
- `submissions` — `company_id`, `form_version_id`, `created_by`, `status`, `score` (NUMERIC(5,2)), `started_at`, `finished_at`, `answers_json` (JSONB). `CHECK status IN (draft, in_progress, completed, cancelled)`.
- `submission_values` — `submission_id`, `form_field_id`, `value_text`, `value_number` (NUMERIC(14,4)), `value_boolean`, `value_date`, `value_json`. `UNIQUE(submission_id, form_field_id)`.
- `submission_conformities` — `submission_id` (CASCADE), `form_field_id` (CASCADE), `status`, `justification`. `UNIQUE(submission_id, form_field_id)`; `CHECK status IN (conforme, nao_conforme)`.
- `attachments` (ADR-0017) — âncora por escopo: `company_id`, `scope` (`component`/`field`/`submission`/`asset`), `submission_id` (CASCADE, nullable), `form_field_id` (nullable), `asset_id` (nullable, sem CASCADE), `component_label`, `metadata_json`, `file_url`, `thumbnail_url`, `mime_type`, `file_size` (BIGINT), `uploaded_by`. `CHECK ck_attachments_scope_anchor`; índices da âncora **não-únicos** (1:N por item — INV-E1). **Sem `submission_value_id`** (removido — Q7.1). `field_key` resolvido via `attachment.form_field.key`.

### Equipes
- `teams` — `company_id`, `name`, `created_by`, `is_active` (soft delete).
- `team_members` — `team_id`, `user_id`. `UNIQUE(team_id, user_id)`.

### Auditoria
- `audit_logs` — `company_id`, `actor_id`, `target_user_id` (NULL), `action`, `meta` (JSON), `created_at`. Índices `ix_audit_logs_company_id`, `ix_audit_logs_created_at`. **Sem `updated_at`, sem CASCADE.**

## Relacionamentos (resumo)

```
companies 1:N memberships, forms, submissions, teams, audit_logs
users     1:N memberships, password_reset_tokens, notification_reads, submissions (created_by),
              team_members, audit_logs (actor + target)
forms          1:N form_versions 1:N form_fields
form_versions  1:N submissions
submissions    1:N submission_values
submissions / form_fields / assets / companies  1:N attachments  (âncora por escopo — ADR-0017)
submissions    1:N submission_conformities
form_fields    1:N submission_values, submission_conformities
teams          1:N team_members
```

## Tipos de campo e armazenamento

| `field_type` | Coluna em `submission_values` | Observação |
|---|---|---|
| `boolean` | `value_boolean` | N/A → `value_text = "na"`, `value_boolean = NULL` |
| `text` | `value_text` | string livre |
| `number` | `value_number` | float (NUMERIC 14,4) |
| `date` | `value_date` | ISO date |
| `select` | `value_json` | `{ "option": "valor" }` |
| `section` | — | **não gera** `submission_value`; divisor visual |

`config_json` por tipo:
- `weight` (float, default 1.0) — o motor de score lê de **qualquer campo exceto `section`**; a UI só ajusta em `boolean`.
- `allow_na` (bool) — habilita N/A em `boolean`.
- `options` (string[]) — opções do `select`.

## Score (verificado em `submissions/service.py`)

```
score = round( Σ weight(conforme) / Σ weight(avaliados em submission_conformities) * 100 , 2 )
```

- Fonte: `submission_conformities` (não `submission_values`).
- Campos sem registro de conformidade — incluindo N/A — **não entram no denominador**.
- `score_breakdown.total_boolean` conta todos os campos não-`section` (nome mantido por compat); `na_count` retorna sempre `0`.

## Snapshot e N/A

- `answers_json` é snapshot escrito em `save_answers` (campo geral escalar; campo escopado =
  `{ <asset_id>: valor }`). **Anexos não escrevem mais `answers_json`** — `attachments` é a fonte da
  verdade da evidência (ADR-0017 revisa o efeito colateral do ADR-0006/0016).
- N/A: linha existe em `submission_values` com `value_text = "na"`; "sem resposta" = linha
  inexistente.

## Migrations aplicadas (16)

`332b89327dc7` (inicial) → `8aeb51c1026f` → `f73cae8e6de7` (teams) → `d4e5f6a7b8c9` (contato
companies) → `e5f6a7b8c9d0` (reset tokens) → `a1b2c3d4e5f6` (notification_reads) →
`b2c3d4e5f6a7` (+evidence) → `c3d4e5f6a7b8` (+section) → `a1b2c3d4e5f7` (−photo) →
`b3c4d5e6f7a8` (−evidence) → `c5d6e7f8a9b0` (submission_conformities) → `d6e7f8a9b0c1`
(instruction) → `e7f8a9b0c1d2` (dismissed) → `f8a9b0c1d2e3` (revoked_at) → `a9b0c1d2e3f4`
(teams.is_active) → `b0c1d2e3f4a5` (audit_logs).
