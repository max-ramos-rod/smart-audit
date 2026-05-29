# DER - Smart Audit

## Objetivo

Este documento consolida o modelo de dados real do Smart Audit no estado atual do projeto.

Ele sustenta:

- multiempresa por `company_id`
- autenticacao e memberships por empresa
- recuperacao de senha com token de uso unico
- formularios versionados
- execucao de inspecoes
- respostas tipadas por campo
- anexos de evidencias
- equipes e membros por empresa

## Decisoes de modelagem

- todas as entidades principais usam `UUID`
- o isolamento operacional acontece por `company_id`
- `form` e separado de `form_version`
- `submission` aponta para a versao efetivamente usada
- respostas usam modelo hibrido:
  - relacional em `submission_values`
  - snapshot em `submissions.answers_json`
- arquivos ficam fora do banco; `attachments` armazena apenas metadados
- equipes foram promovidas ao modelo real do sistema
- **nao existe tabela de notificacoes**: notificacoes sao derivadas em tempo real de `submissions` pelo servico
- o estado de leitura e armazenado em `notification_reads` com chave deterministica por usuario

## Contextos e relacionamentos

### Acesso

- `users`
- `companies`
- `memberships`
- `password_reset_tokens`
- `notification_reads`

Relacionamentos:

- `companies 1:N memberships`
- `users 1:N memberships`
- `users 1:N password_reset_tokens`
- `users 1:N notification_reads`

### Formularios

- `forms`
- `form_versions`
- `form_fields`

Relacionamentos:

- `companies 1:N forms`
- `forms 1:N form_versions`
- `form_versions 1:N form_fields`

### Inspecoes

- `submissions`
- `submission_values`
- `attachments`

Relacionamentos:

- `companies 1:N submissions`
- `users 1:N submissions`
- `form_versions 1:N submissions`
- `submissions 1:N submission_values`
- `form_fields 1:N submission_values`
- `submission_values 1:N attachments`

### Equipes

- `teams`
- `team_members`

Relacionamentos:

- `companies 1:N teams`
- `teams 1:N team_members`
- `users 1:N team_members`

## DER textual

```text
users
  |-< memberships >- companies
  |                     |
  |-< password_         |-< forms
  |   reset_tokens      |    `-< form_versions
  |                     |         `-< form_fields
  `-< notification_     |
      reads             |-< submissions >- users
                        |      |
                        |      |- form_versions
                        |      `-< submission_values >- form_fields
                        |             `-< attachments
                        |
                        `-< teams
                               `-< team_members >- users
```

## DER em Mermaid

```mermaid
erDiagram
    USERS ||--o{ MEMBERSHIPS : belongs_to
    COMPANIES ||--o{ MEMBERSHIPS : has
    USERS ||--o{ PASSWORD_RESET_TOKENS : has
    COMPANIES ||--o{ FORMS : owns
    FORMS ||--o{ FORM_VERSIONS : has
    FORM_VERSIONS ||--o{ FORM_FIELDS : has
    COMPANIES ||--o{ SUBMISSIONS : owns
    USERS ||--o{ SUBMISSIONS : creates
    FORM_VERSIONS ||--o{ SUBMISSIONS : uses
    SUBMISSIONS ||--o{ SUBMISSION_VALUES : contains
    FORM_FIELDS ||--o{ SUBMISSION_VALUES : answers
    SUBMISSION_VALUES ||--o{ ATTACHMENTS : has
    COMPANIES ||--o{ TEAMS : owns
    TEAMS ||--o{ TEAM_MEMBERS : has
    USERS ||--o{ TEAM_MEMBERS : belongs_to
```

## Tabelas

### `users`

- `id UUID PK`
- `name VARCHAR(150)`
- `email VARCHAR(255) UNIQUE`
- `password_hash VARCHAR(255)`
- `is_active BOOLEAN`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Observacoes:

- email e unico globalmente
- `password_hash` usa formato PBKDF2-SHA256 customizado (`pbkdf2_sha256$iterations$salt$digest`)

### `companies`

- `id UUID PK`
- `name VARCHAR(150)`
- `slug VARCHAR(120) UNIQUE`
- `plan VARCHAR(50)`
- `is_active BOOLEAN`
- `cnpj VARCHAR(20) NULL`
- `timezone VARCHAR(60) NULL`
- `contact_email VARCHAR(255) NULL`
- `phone VARCHAR(30) NULL`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

### `memberships`

- `id UUID PK`
- `company_id UUID FK -> companies.id`
- `user_id UUID FK -> users.id`
- `role VARCHAR(30)`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Restricoes:

- `UNIQUE(company_id, user_id)`
- `CHECK role IN ('OWNER', 'ADMIN', 'MANAGER', 'INSPECTOR', 'VIEWER')`

### `password_reset_tokens`

- `id UUID PK`
- `user_id UUID FK -> users.id ON DELETE CASCADE`
- `token VARCHAR(64) UNIQUE`
- `expires_at TIMESTAMPTZ`
- `used_at TIMESTAMPTZ NULL`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Observacoes:

- `token` e gerado com `secrets.token_urlsafe(32)` (URL-safe base64, ~43 chars)
- TTL de 1 hora a partir da criacao
- uso unico: `used_at` e preenchido na troca de senha e valida como barreira de reuso
- o endpoint de forgot-password nao expoe se o email existe (anti-enumeracao)

### `forms`

- `id UUID PK`
- `company_id UUID FK -> companies.id`
- `name VARCHAR(180)`
- `description TEXT NULL`
- `is_active BOOLEAN`
- `created_by UUID FK -> users.id`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

### `form_versions`

- `id UUID PK`
- `form_id UUID FK -> forms.id`
- `version INTEGER`
- `status VARCHAR(20)`
- `published_at TIMESTAMPTZ NULL`
- `created_by UUID FK -> users.id`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Restricoes:

- `UNIQUE(form_id, version)`
- `CHECK status IN ('draft', 'published', 'archived')`

### `form_fields`

- `id UUID PK`
- `form_version_id UUID FK -> form_versions.id`
- `key VARCHAR(100)`
- `label VARCHAR(180)`
- `field_type VARCHAR(30)`
- `required BOOLEAN`
- `position INTEGER`
- `config_json JSONB`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Restricoes:

- `UNIQUE(form_version_id, key)`
- `UNIQUE(form_version_id, position)`

Tipos de campo atualmente suportados:

- `boolean`
- `text`
- `number`
- `select`
- `date`
- `photo`

### `submissions`

- `id UUID PK`
- `company_id UUID FK -> companies.id`
- `form_version_id UUID FK -> form_versions.id`
- `created_by UUID FK -> users.id`
- `status VARCHAR(20)`
- `score NUMERIC(5,2) NULL`
- `started_at TIMESTAMPTZ`
- `finished_at TIMESTAMPTZ NULL`
- `answers_json JSONB`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Restricoes:

- `CHECK status IN ('draft', 'in_progress', 'completed', 'cancelled')`

Observacoes:

- `status` e usado tambem para dashboard, busca e notificacoes derivadas
- `score` e calculado no momento da finalizacao com base nos campos obrigatorios respondidos

### `submission_values`

- `id UUID PK`
- `submission_id UUID FK -> submissions.id`
- `form_field_id UUID FK -> form_fields.id`
- `value_text TEXT NULL`
- `value_number NUMERIC(14,4) NULL`
- `value_boolean BOOLEAN NULL`
- `value_date DATE NULL`
- `value_json JSONB NULL`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Restricoes:

- `UNIQUE(submission_id, form_field_id)`

### `attachments`

- `id UUID PK`
- `submission_value_id UUID FK -> submission_values.id ON DELETE CASCADE`
- `file_url TEXT`
- `thumbnail_url TEXT NULL`
- `mime_type VARCHAR(120)`
- `file_size BIGINT`
- `uploaded_by UUID FK -> users.id`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Observacoes:

- o arquivo fisico fica em disco em `settings.upload_dir/<company_id>/<uuid>.<ext>`
- `attachments` armazena apenas metadados e a URL publica
- vinculo e com `submission_value` (nao diretamente com a submission)
- `uploaded_by` registra o usuario que fez o upload

### `teams`

- `id UUID PK`
- `company_id UUID FK -> companies.id`
- `name VARCHAR(150)`
- `created_by UUID FK -> users.id`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

### `team_members`

- `id UUID PK`
- `team_id UUID FK -> teams.id`
- `user_id UUID FK -> users.id`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

Restricoes:

- `UNIQUE(team_id, user_id)`

## Regras de consistencia

### Isolamento por empresa

Toda query de dominio filtra por `company_id` com base no membership atual.

Isso vale para:

- usuarios da empresa
- formularios
- inspecoes
- equipes
- evidencias e uploads

### Versionamento

- formularios publicados nao sao editados retroativamente
- uma mudanca estrutural relevante gera nova `form_version`
- cada `submission` fica congelada na versao usada no momento da execucao

### Snapshot `answers_json`

- fonte estruturada: `submission_values`
- leitura otimizada: `answers_json`
- ambos sao mantidos no fluxo de `save_answers`

### Uploads e anexos

- o arquivo e salvo fora do banco
- o endpoint de upload devolve URL publica
- `attachments` liga essa URL a uma submission

### Notificacoes sem persistencia

Nao existe tabela `notifications`. O endpoint `GET /me/notifications` deriva alertas em tempo real a partir de `submissions`:

- `in_progress` ha mais de 24h → alerta `pending`
- `completed` com score < 80% → alerta `low_score`
- `completed` com score >= 90% → alerta `excellent`

Se for necessario persistir estado de leitura por usuario, sera preciso criar uma tabela (ex: `notification_reads` com FK para user e um identificador do alerta derivado).

## Migracoes aplicadas

| Revisao | Descricao |
|---|---|
| `332b89327dc7` | schema inicial |
| `8aeb51c1026f` | add updated_at nas tabelas de metadados |
| `f73cae8e6de7` | add teams e team_members |
| `d4e5f6a7b8c9` | add campos de contato em companies (cnpj, timezone, contact_email, phone) |
| `e5f6a7b8c9d0` | add password_reset_tokens |

## Evolucao futura prevista

Ainda nao implementados como tabela/modulo:

- `notification_reads` — para persistir estado de leitura de notificacoes por usuario
- `audit_logs` — rastreabilidade de acoes criticas
- `corrective_actions` — acoes vinculadas a itens reprovados em inspecoes
- storage externo (S3/GCS) em substituicao ao disco local
