# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Monorepo with two deployables:

- `backend/` — FastAPI service (Python 3.12, SQLAlchemy 2.0, Alembic, PostgreSQL). Installed as the `smart-audit-backend` package via `pyproject.toml` at the repo root (`package-dir = backend/`).
- `frontend/` — Vue 3 SPA (Vite, Pinia, Vue Router, Axios, TailwindCSS 4). Served under the `/app/` base in production (see Frontend section).
- `landing/` — static institutional landing page (`index.html`) served at the domain root `/` by the external Nginx proxy. Links point to `/app/login`.
- `docs/Arquitetura_Smart_Audit.md` and `docs/DER_Smart_Audit.md` — source of truth for domain decisions and ER model.
- `docs/Deploy_Smart_Audit.md` — production topology: Docker networks, Nginx proxy, `/app/` base, onboarding scripts.
- `docker-compose.yml` — three services (`db`, `backend`, `frontend`) on an `internal` network + shared external `app_network`. Cross-network references must use unique container names (`smart_audit_db`, `smart_audit_backend`) to avoid DNS collisions with other projects on `app_network`.
- `db/schema_v1.sql` — reference schema snapshot; canonical schema is managed by Alembic in `backend/alembic/versions/`.
- `db/fix_postgres_ownership.sql` — helper script to fix PostgreSQL ownership when setting up a local database.

## Common commands

All Python commands assume the repo-root virtualenv (`.venv`). On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1`. Alembic is configured at the repo root (`alembic.ini` points at `backend/alembic`), so always run `alembic` from the repo root.

### Backend

```powershell
# Install (editable) with dev extras
pip install -e ".[dev]"

# Optional: enable local pre-commit hooks (ruff + frontend eslint/prettier before commit;
# mypy and tests stay in CI). See .pre-commit-config.yaml
pre-commit install

# Run the API (reads .env from repo root)
uvicorn app.main:app --reload --app-dir backend --port 8003

# Migrations — alembic.ini is at repo root; NOTE: alembic.ini has a hardcoded
# sqlalchemy.url for local dev. Override via DATABASE_URL in .env for other envs.
alembic upgrade head
alembic revision --autogenerate -m "<message>"

# Tests — MUST use `python -m pytest`, not bare `pytest`.
# Bare pytest does not add the repo root to sys.path, causing `ModuleNotFoundError: backend`.
python -m pytest                                                    # full suite
python -m pytest backend/tests/integration/test_forms.py           # single file
python -m pytest -k test_login_and_me                              # single test by name
python -m pytest backend/tests/unit/                               # unit tests only
python -m pytest backend/tests/integration/                        # integration tests only

# Lint (ruff config in pyproject.toml; line-length=100, select E/F/I)
ruff check backend
ruff check --fix backend

# Type check (mypy config in pyproject.toml; checks backend/app, pydantic plugin) — CI gate
mypy

# Seed scripts (require DB up + .env configured)
python backend/scripts/create_user.py --name "Admin" --email admin@smartaudit.local --password admin123456
python backend/scripts/link_user_company.py --email admin@smartaudit.local --company-name "Acme" --company-slug acme --role OWNER

# Export the OpenAPI contract (no DB needed; venv + .env). Live docs at /docs, /openapi.json (root, dev only).
python backend/scripts/export_openapi.py -o openapi.json
```

### Frontend

> **Use Node 20 / npm 10 localmente** (mesma versão do CI — ver `.nvmrc` e `engines` em `frontend/package.json`). Node 24/npm 11 resolve dependências transitivas (`@emnapi/*`) em versões diferentes e gera um `package-lock.json` que o `npm ci` do CI rejeita. Com `nvm`: `nvm use` (lê o `.nvmrc`). Corepack respeita `"packageManager": "npm@10.9.8"`.

```powershell
cd frontend
npm install
npm run dev      # Vite on 0.0.0.0:5174
npm run build    # runs `vue-tsc --noEmit` then vite build — type-check is part of build
npm run preview
npm test         # Vitest (run once)
npm run test:watch  # Vitest (watch mode)
npm run test:e2e    # Playwright E2E (starts dev server on port 5200, all API calls mocked)
npm run test:e2e:ui # Playwright interactive UI
npm run lint        # ESLint (flat config, .ts + .vue) — CI gate
npm run format      # Prettier (scope: src/**/*.ts + e2e/**/*.ts); .vue/.css excluded on purpose
npm run format:check # Prettier check (CI gate)
```

ESLint config is `frontend/eslint.config.js` (flat, ESLint 9; formatting delegated to Prettier via `@vue/eslint-config-prettier`). `no-explicit-any`/`no-unused-vars` are **enforced as errors** (test files are exempt from `no-explicit-any` for mocks). API errors are handled via `extractProblemMessage` (`src/services/api/problem.ts`), not `catch (e: any)`. Prettier (`.prettierrc.json`: no semicolons, single quotes, width 100) is scoped to `.ts` only — `.vue` is excluded because `semi:false` strips the `;` separating multi-statement inline handlers (e.g. `@click="a; b()"`), producing invalid templates.

The frontend expects the backend at `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8003/api/v1`). Copy `frontend/.env.example` to `frontend/.env.local` to override locally.

### Tests need a real database

`backend/tests/conftest.py` connects to the database configured in `.env` and uses async SQLAlchemy savepoint isolation: one `AsyncConnection` + outer transaction per test, with `join_transaction_mode="create_savepoint"` so every `db.commit()` inside service code creates a savepoint instead of a real commit. The outer transaction is rolled back at teardown — no cleanup SQL needed. There is **no** mock/SQLite shortcut — integration tests will fail if Postgres is not reachable and migrated.

```powershell
# Before running tests for the first time:
alembic upgrade head
python -m pytest
```

Key test infrastructure decisions:
- `pytest-asyncio` with `asyncio_mode = "auto"` — all `async def test_*` and `async def` fixtures run automatically.
- `asyncio_default_fixture_loop_scope = "session"` and `asyncio_default_test_loop_scope = "session"` — all tests and fixtures share one event loop for the entire run. Required because asyncpg connections bind to an event loop at creation; a per-function loop would close the loop under the connection pool.
- `httpx.AsyncClient` + `ASGITransport` replaces the sync `TestClient`. All HTTP calls in tests must be `await client.post(...)`.
- `expire_on_commit=False` on the test `AsyncSession` — prevents attribute expiry after savepoint commits, which would trigger lazy-load errors in async context.
- `populate_existing=True` in `_get_one` / `_list_from_stmt` (base repository) — forces selectinload to re-query even when the identity map already has the object. Critical for correctness after mutations: without it, stale Python-string FK values (set at object creation) would prevent selectinload from matching related objects whose PKs asyncpg returns as `uuid.UUID`.

The `client` fixture disables the rate limiter automatically (`limiter.enabled = False`) — do not disable it manually in individual tests.

Fixtures available in `conftest.py`:

| Fixture | Role | Description |
|---|---|---|
| `client` | — | `httpx.AsyncClient` with DB override + rate limiter disabled |
| `auth_headers` | OWNER | JWT + X-Company-Id for a seeded OWNER user |
| `inspector_headers` | INSPECTOR | JWT + X-Company-Id for a seeded INSPECTOR user |
| `viewer_headers` | VIEWER | JWT + X-Company-Id for a seeded VIEWER user |
| `seeded_user` | OWNER | Raw dict with email, password, user_id, company_id |
| `inspector_user` | INSPECTOR | Same shape as seeded_user |
| `viewer_user` | VIEWER | Same shape as seeded_user |
| `multi_company_user` | OWNER x2 | User with two company memberships |

## Architecture

### Backend — layered, domain-modular

The mandated flow is `api -> service -> repository -> db`. Each domain lives under `backend/app/modules/<domain>/` with `service.py`, `repository.py`, `schemas.py` (Pydantic DTOs). Routers live in `backend/app/api/v1/routers/` and are aggregated by [backend/app/api/v1/router.py](backend/app/api/v1/router.py), mounted at `/api/v1` in [backend/app/main.py](backend/app/main.py).

Rules enforced across the codebase:

- **Endpoints stay thin.** Routers parse the request, resolve dependencies, call a service method, and serialize via `success_response` / `paginated_response` from [backend/app/core/responses.py](backend/app/core/responses.py). Business validation belongs in services; persistence belongs in repositories.
- **Services commit; repositories flush.** `repository._save` / `_save_many` call `db.flush()`; the service method is responsible for the final `db.commit()`. Never commit inside repositories.
- **Named creation methods in repositories.** Do not call `_save` directly from services — repositories expose named methods (`create_team`, `create_member`, etc.) that call `_save` internally. This keeps the service layer free of ORM details.
- **Response envelope is non-negotiable.** Successes return `{ "data": ..., "meta": {...} }`; paginated lists use `PageMeta` from [backend/app/core/pagination.py](backend/app/core/pagination.py); errors flow through the handlers in [backend/app/core/errors.py](backend/app/core/errors.py) and produce **RFC 7807** `application/problem+json` payloads. Tests in `backend/tests/integration/` assert this envelope shape — breaking it breaks the suite.
- **All request schemas use Field constraints.** Every `str` field on a request schema must have `Field(min_length=..., max_length=...)`. Never use bare `name: str`.

### Async SQLAlchemy — rules and pitfalls

The entire backend uses `asyncpg` + `AsyncSession`. Every endpoint function, service method, repository method, and FastAPI dependency is `async def`. Key rules:

- **`db.add()` and `db.add_all()` are synchronous** — no `await`. Everything else that touches the database needs `await`: `db.flush()`, `db.commit()`, `db.delete()`, `db.get()`, `db.scalar()`, `db.scalars()`, `db.execute()`.
- **No lazy loading.** Async SQLAlchemy raises `MissingGreenlet` on any implicit lazy load. All relationships that are accessed after a query must be loaded eagerly with `selectinload` (or `joinedload`) in the same query. Add `selectinload` to the query options — never rely on attribute access triggering a load.
- **Chained selectinload for nested relationships.** Use `.options(selectinload(Parent.children).selectinload(Child.grandchildren))` — this issues two sequential sub-queries, both within the same async context.
- **`populate_existing=True` in base repository read methods.** `_get_one` and `_list_from_stmt` pass `.execution_options(populate_existing=True)` to every query. This forces SQLAlchemy to reload objects from the DB result even when they exist in the identity map. Without it, re-queries after mutations return stale cached state — most critically, FK columns set as Python strings at object creation would never be refreshed to the `uuid.UUID` values asyncpg returns, causing selectinload to silently fail to match related objects.
- **Alembic runs sync inside async.** `backend/alembic/env.py` uses `asyncio.run(run_async_migrations())` → `engine.connect()` → `await connection.run_sync(do_run_migrations)`. The `run_sync` bridge allows Alembic's synchronous context to run over an async connection.
- **`DATABASE_URL` must use the `asyncpg` driver.** Format: `postgresql+asyncpg://user:pass@host:port/db`. The `psycopg`/`psycopg-binary` packages are not installed — do not add them back.

### Multi-tenancy and auth

Tenancy is modeled as `User N—N Company` through `memberships` (with a `role`: `OWNER` / `ADMIN` / `MANAGER` / `INSPECTOR` / `VIEWER`). A user does **not** belong to a single company — every tenant-scoped query must be filtered by the active company.

- Auth: JWT bearer token from `/api/v1/auth/login`. Password hashing is custom PBKDF2-SHA256 (`pbkdf2_sha256$iterations$salt$digest`) in [backend/app/core/security.py](backend/app/core/security.py) — do **not** swap in passlib/bcrypt without a migration plan for existing hashes.
- Active company is resolved by the `X-Company-Id` request header via `get_current_membership` in [backend/app/modules/memberships/dependencies.py](backend/app/modules/memberships/dependencies.py). If the user has exactly one membership, the header is optional; otherwise it's required (returns 400). Endpoints inject `Membership` (or `get_admin_membership` / `get_manager_membership` for role-restricted routes — see [backend/app/modules/memberships/permissions.py](backend/app/modules/memberships/permissions.py)) and use `membership.company_id` as the tenant filter.
- The frontend mirrors this: [frontend/src/services/api/http.ts](frontend/src/services/api/http.ts) auto-attaches both `Authorization: Bearer …` and `X-Company-Id` from localStorage on every request, and clears the token on any 401.
- After page refresh, `authStore.user` is rehydrated from `contextStore.context.user` inside the router guard — see [frontend/src/router/index.ts](frontend/src/router/index.ts).

### Form versioning and the hybrid answer model

This is the load-bearing domain decision (see Decisão 2 and 3 in `docs/Arquitetura_Smart_Audit.md`):

- `forms` is the logical template; `form_versions` is what inspections actually reference. Editing a form **never** mutates fields of an existing version — `publish_new_version` creates a new `FormVersion` + new `FormField` rows. A submission is bound to a specific `form_version_id` for life, so historical inspections stay readable.
- Answers are stored **twice on purpose**:
  1. Relational rows in `submission_values` (typed columns: `value_text`, `value_number`, `value_boolean`, `value_date`, `value_json`) — for queries/reports.
  2. A denormalized `answers_json` snapshot on `submissions` — for fast reads.

  `SubmissionService.save_answers` writes both and they must stay in sync. When adding a new field type, update `normalize_value`, `serialize_raw_value`, `extract_value`, and (if it should affect scoring) `calculate_score` in [backend/app/modules/submissions/service.py](backend/app/modules/submissions/service.py).

#### Field types

The allowed `field_type` values (enforced by CHECK constraint on `form_fields`):

| Type | Stored in | Notes |
|---|---|---|
| `boolean` | `value_boolean` (or `value_text = "na"` for N/A) | Only type that contributes to score |
| `text` | `value_text` | Plain string |
| `number` | `value_number` | Float |
| `date` | `value_date` | ISO date |
| `select` | `value_json` as `{"option": "..."}` | Options list in `config_json.options` |
| `section` | — (not stored) | Visual divider / group header; never contributes to answers or score |

**Removed types** (do not re-add): `photo` (removed migration `a1b2c3d4e5f7`) and `evidence` (removed migration `b3c4d5e6f7a8`). Evidence is now a capability of any field via the Attachments module.

#### `config_json` schema per field type

- **`boolean`**: `{ weight?: number, allow_na?: boolean }`
  - `weight` (default 1) — multiplier used in score calculation
  - `allow_na` — enables a "N/A" answer option
- **`select`**: `{ options: string[] }`
- **`text` / `number` / `date`**: `{}`
- **`section`**: always `{}` — no config allowed; auto-keyed as `__section_{position}__` by the form builder

#### Score calculation

Score is 0–100, calculated only from `boolean` fields with at least one answered field. N/A and unanswered fields are excluded from both numerator and denominator. Each boolean field has an optional `weight` (`config_json.weight`, default 1). Formula: `round((sum of weight for conformes) / (sum of weight for answered non-na) * 100, 2)`. See `calculate_score` and `calculate_score_breakdown` in [backend/app/modules/submissions/service.py](backend/app/modules/submissions/service.py).

### Attachments module (evidence)

Evidence is **not** a field type — it is a first-class entity anchored by **scope** (DR-0017/ADR-0017). The `attachments` bounded context lives under `backend/app/modules/attachments/` and is served at `/submissions/{id}/attachments`.

**Data model (ADR-0017):** `attachments` é uma tabela polimórfica com âncora `(scope, company_id, submission_id?, form_field_id?, asset_id?)` + `component_label` (rótulo congelado) + `metadata_json`. **Não há mais `submission_value_id`** (removido — Q7.1). `scope ∈ {component, field, submission, asset}` governado por `CHECK`:
- `component` — `(submission, field, asset)` todos preenchidos (evidência de um componente);
- `field` — `(submission, field)`, sem asset (campo geral);
- `submission` — só `submission` (evidência da inspeção);
- `asset` — só `asset` (documento permanente do ativo, sem inspeção).

**1:N protegido (INV-E1/Q7.3):** um item inspecionado admite N evidências — a âncora é deliberadamente **não-única** (nenhum `UNIQUE`/PK a toca). **Retenção (Q7.2):** `submission_id ON DELETE CASCADE`; `asset_id` sem CASCADE (ativo soft-deletado). Limpeza física de arquivo só em `delete_attachment` (ver `docs/TECH_BACKLOG.md` TB-001).

**Endpoints (all require JWT + X-Company-Id):**
- `GET  /submissions/{id}/attachments?page=1&page_size=N` — lists all attachments for a submission
- `POST /submissions/{id}/attachments` — creates an attachment; body: `{ field_key?, asset_id?, file_url, mime_type, file_size, thumbnail_url?, metadata_json? }`. Escopo derivado: sem `field_key` ⇒ `submission`; com `field_key` ⇒ `field`; `+asset_id` ⇒ `component` (valida INV1: asset na subárvore + tipo bate com `component_type_id` do campo).
- `DELETE /submissions/{id}/attachments/{attachment_id}` — deletes attachment and removes local file if stored on disk

**Não escreve `answers_json`** — `attachments` é a fonte da verdade da evidência (revisa o efeito colateral do ADR-0006/0016).

**Serialize shape** (`AttachmentResponse`): `id`, `submission_id`, `scope`, `field_key` (de `attachment.form_field.key`), `asset_id`, `component_label`, `file_url`, `thumbnail_url`, `mime_type`, `file_size`, `metadata_json`, `created_at`.

**Allowed MIME types for uploads:** `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `video/quicktime`, `video/x-msvideo`, `audio/mpeg`, `audio/wav`, `audio/ogg`, `audio/mp4`, `application/pdf` (enforced in uploads router). Size limits: images 10 MB, PDF 20 MB, audio 50 MB, video 200 MB.

### Teams module

`teams` and `team_members` are a separate bounded context under `backend/app/modules/teams/`. Teams belong to a company; members must already be members of that company (validated in `TeamService.add_member`). Read endpoints use `get_current_membership`; write endpoints require `get_manager_membership`.

### Uploads

Uploads are handled directly in [backend/app/api/v1/routers/uploads.py](backend/app/api/v1/routers/uploads.py) — no separate module. Files are written to `settings.upload_dir/<company_id>/<uuid>.<ext>` and served via FastAPI `StaticFiles` mounted at `/uploads`. The returned URL uses `settings.upload_base_url` as prefix. Allowed MIME types: images (JPEG/PNG/WebP), video (MP4/MOV/AVI), audio (MP3/WAV/OGG/M4A), PDF. Size limits: images 10 MB, PDF 20 MB, audio 50 MB, video 200 MB.

### Email

Email is shared infrastructure under [backend/app/core/email/](backend/app/core/email/) — never send mail with raw `smtplib` from a module. The layers:

- **`sender.py`** — `EmailSender` protocol + `SmtpEmailSender` (prod) and `ConsoleEmailSender` (dev fallback, logs the message when `SMTP_HOST` is unset). `get_email_sender()` is an `lru_cache` factory that picks the impl from settings (same pattern as `get_settings`). `SmtpEmailSender` runs the blocking `smtplib` call via `asyncio.to_thread` and swallows exceptions (sending must never break the request flow — e.g. the anti-enumeration reset endpoint stays fail-soft).
- **`templates.py`** — pure functions returning an `EmailMessage` (subject + plain-text + HTML). Keep formatting out of services. Each template provides both a text and an HTML body (multipart/alternative improves deliverability).
- **`service.py`** — `EmailService` with semantic methods (`send_password_reset`, `send_user_invite`). Modules call intent, not SMTP — the same rule as repositories hiding ORM. Services that send mail take an optional `EmailService` in `__init__` for injection (e.g. `AuthService(email_service=...)`).

`FRONTEND_URL` (settings, includes the `/app` base path) is the single source for absolute links in emails — no `/app` hardcoded in code. `templates.py` is exempted from `E501` in `pyproject.toml` (long inline-CSS lines in HTML f-strings).

**User invite reuses the reset-password machinery.** `POST /users/invite` (admin-gated) creates the user with an unusable random password and issues a token in the **same** `password_reset_tokens` table with a longer TTL (`invite_token_ttl_hours`, default 72h). The invitee sets their password via the **same** `POST /auth/reset-password` endpoint and screen. `UserService` injects `AuthRepository`, `CompanyRepository` and `EmailService` for this. Cross-company provisioning (a brand-new company's first OWNER) stays manual via scripts — no membership can authorize it (see [docs/Deploy_Smart_Audit.md](docs/Deploy_Smart_Audit.md)).

### Frontend

SPA structured by domain (`stores/<domain>`, `services/<domain>.service.ts`, `views/<domain>/`). The `@` alias resolves to `frontend/src`.

- **The SPA is served under the `/app/` base path** (the landing page at `landing/index.html` owns the domain root `/`). This base is set in three places that must stay in sync: `base: '/app/'` in [frontend/vite.config.ts](frontend/vite.config.ts), `createWebHistory('/app/')` in [frontend/src/router/index.ts](frontend/src/router/index.ts), and the `location /app/` rewrite in [frontend/nginx.conf](frontend/nginx.conf). All routes are therefore reached at `/app/login`, `/app/submissions`, etc. E2E tests (`page.goto`, `toHaveURL`) use the `/app/` prefix. The Vite dev server still runs at the root on port 5174 (the base only affects build/production paths). See [docs/Deploy_Smart_Audit.md](docs/Deploy_Smart_Audit.md) for the full deployment topology.
- Auth/session state is bootstrapped in the router guard ([frontend/src/router/index.ts](frontend/src/router/index.ts)): if a route requires auth and a token exists, it calls `useContextStore().bootstrap()` to load `/me/companies` + `/me/context` before rendering. Without that, downstream stores will not have an active company. After bootstrap, `authStore.user` is synced from `contextStore.context.user` if null.
- HTTP client is centralized in [frontend/src/services/api/http.ts](frontend/src/services/api/http.ts); never call `axios` directly from views/stores.
- Token + active company id are persisted in `localStorage` under `smart-audit.token` / `smart-audit.company-id` via [frontend/src/services/api/storage.ts](frontend/src/services/api/storage.ts).
- Frontend tests live in `frontend/src/__tests__/` and run with Vitest (`npm test`). Use `setActivePinia(createPinia())` + `localStorage.clear()` in `beforeEach`. Mock service modules with `vi.mock`.

#### Score utility (`frontend/src/utils/score.ts`)

Central module for score display logic. Import from here — never inline score threshold comparisons in views.

```typescript
SCORE_THRESHOLD_OK   = 85  // green / "Aprovado"
SCORE_THRESHOLD_WARN = 65  // yellow / "Atenção"
                           // below 65 → red / "Reprovado"

scoreClass(score)     // → 'ok' | 'warn' | 'err'   (CSS modifier)
scoreColorVar(score)  // → 'var(--sa-ok)' | 'var(--sa-warn)' | 'var(--sa-danger)'
scoreChipClass(score) // → '' | 'status-chip--warn' | 'status-chip--inactive'
scoreText(score)      // → 'Aprovado' | 'Atenção' | 'Reprovado'
```

#### `FieldType` (`frontend/src/types/forms.ts`)

```typescript
export type FieldType = 'boolean' | 'text' | 'number' | 'date' | 'select' | 'section'
```

`FormField.field_type` and `FormFieldCreatePayload.field_type` are typed as `FieldType`. When writing test mocks with string literals, use `as const` to satisfy the union: `field_type: 'boolean' as const`.

#### Shared components

**`frontend/src/components/submissions/InspectionFieldRow.vue`** — renders a single field row in the **normal list mode** (read-only and in-progress via the default page view). Props: `field`, `answer`, `conformityStatus`, `conformityJustification`, `isCompleted`, `isPendingRequired`, `evidenceAttachments`, `evidenceUploading`, `evidenceError`, `compact?`. Card view and inspection list mode do not use this component.

**`frontend/src/components/submissions/InspectionListRow.vue`** — compact row used exclusively in the **inspection list overlay** (`.insp-listshell`). Props: `field`, `position`, `answer`, `conformityStatus`, `conformityJustification`, `isCompleted`, `isPendingRequired`, `evidenceCount`, `isExpanded`. Expandable inline panel for answer + conformity + evidence. Emits: `toggle`, `update-answer`, `set-conformity`, `update-justification`, `request-evidence`, `request-justification`.

**`frontend/src/components/forms/FormFieldEditor.vue`** — reusable field editor used in the version composer (FormDetailView and FormsView). Accepts a `FormFieldCreatePayload` via `v-model`, plus `index`, `showRemove`, optional `mode` (`'inline' | 'full'`) and `assetTypes` (`AssetType[]`). Emits `remove` and `updateKey`. Configures: label, key, field type, required, weight (boolean), allow_na (boolean), options (select), instruction, and **component scope** (DR-0002): a "Repetir por componente" toggle + asset-type selector + badge that sets `component_type_id` (only when `assetTypes` is provided; never for `section`).

**`frontend/src/components/submissions/InspectionComposer.vue`** — 3-step wizard (form → client → asset) extracted from SubmissionsView. Props: `preselectedAssetId?`, `preselectedAssetLabel?`, `preselectedClientId?` — the active steps adapt to which one is set (asset-preselected → only form; client-preselected → form+asset; none → all three). Emits `created(submissionId)` and `close`. Used by SubmissionsView (no preselection) and ClientDetailView (asset/client preselection). `asset_id` stays nullable on create — retro-compatible.

**`frontend/src/components/ui/AssetTree.vue`** — recursive (`defineOptions({ name: 'AssetTree' })`) asset→component tree with lazy-loaded children (`fetchAsset` on first expand). Props: `nodes`, `typeNames`, `depth?`. Emits `startInspection(asset)` and `addChild(parent)` (revealed on row hover).

#### Inspection composables (`frontend/src/composables/`)

`SubmissionDetailView`'s logic is extracted into four framework-pure composables (unit-testable without mounting the view). The view keeps the template and a thin `<script setup>` that wires them together and owns `populateDraft` (mutates the composable reactives directly — there is **no** `populateConformity`):

- **`useConformity(submissionId, answerableInstances, onAdvance)`** → `conformityStatus`, `conformityJustification`, justification-sheet state, `setConformity`, `setNaoConformeCard`, `confirmJustification`, `buildConformityItems` (includes `asset_id` for scoped fields), `triggerConformitySave` (debounced).
- **`useEvidence(submissionId, answerableInstances)`** → `evidenceAttachments` keyed by **instanceKey** (`field.key@asset_id` for scoped fields — DR-0017), upload/delete handlers, evidence-sheet state. Sends `{ field_key, asset_id }`; scope is derived server-side.
- **`useInspectionProgress(answerableInstances, conformityStatus, fields, inspectionIndex)`** → `progressStats`, `liveScore` (replicates ADR-0008 weighting; rounds to integer for the live ring only — persisted score comes from the backend), `scoreRingStyle`, `allAnswered`, `formSections`, `nearbyDots`.
- **`useInspectionSwipe({ getCurrentInstanceKey, onConformeSwipe, onNaoConformeSwipe })`** → swipe state + `cardSwipeStyle` + touch handlers for card mode.

Instances come from `buildRenderRows`/`instanceKey` in `frontend/src/utils/inspectionInstances.ts` (DR-0002 expansion: one answerable instance per `field × component`).

#### Submission inspection UI (`SubmissionDetailView`)

The main inspection screen has three mutually exclusive display modes:

1. **Normal list mode** (default, also for completed inspections) — all fields rendered in a scrollable list in the page body. Completed inspections are read-only. Uses `InspectionFieldRow.vue`.
2. **Inspection card mode** (`viewMode = 'card'`) — fullscreen Teleport overlay (`.insp-fullscreen`), one field at a time, swipe gestures (right = Conforme, left = Não conforme). Only available for in-progress inspections. Card rendered inline in the view.
3. **Inspection list mode** (`viewMode = 'list'`) — fullscreen Teleport overlay (`.insp-listshell`), compact scrollable list with filter chips and section headers. Only available for in-progress inspections. Uses `InspectionListRow.vue`.

**Overlay positioning:** Both `insp-fullscreen` and `insp-listshell` are `position: fixed`. On desktop (≥768px) `left: 248px` keeps the sidebar visible. On mobile they cover the full viewport (`z-index: 200`).

**Shared header (identical in both inspection modes):**
- Line 1 (`.insp-fhdr`): back button + form name + toggle [Lista][Cartão] + score ring
- Line 2 (`.insp-fprog`): segmented progress bar + counter + color legend + separator + chips (section chips in card, filter chips in list)

**Navigation flow:** In-progress inspections open directly in list mode. Toggle switches between card and list modes. The back button in card mode returns to list mode (does not exit inspection).

**Filter chips (list mode):** `Todos`, `Pendentes`, `Conformes`, `Não conf.`, `S/N`, `Seleção` — drives `filteredListFields` computed.

Evidence (attachments) is rendered **under each field** in all three modes via `evidenceAttachments: reactive<Record<string, AttachmentItem[]>>`, keyed by `field.key`. Loaded once in `onMounted` via `loadEvidenceAttachments()` → `listAttachments(submissionId)`. New uploads are pushed to the reactive dict immediately without a reload.

The upload button only shows for non-completed inspections (`v-if="!isCompleted"`). For completed inspections, the evidence section shows only if there are attachments. A summary line ("X evidência(s) registrada(s)" or "Sem evidências registradas") appears at the top of the fields area for completed inspections after evidence loads.

#### Report view (`SubmissionReportView`)

Read-only summary for completed (and in-progress) inspections accessible at `/submissions/:id/report`. Shows score, breakdown, boolean field results, non-boolean field values, and any evidence (attachments) for each field as clickable links. PDF export via `exportSubmissionPdf` → backend `/submissions/{id}/export`.

#### Client hub (`ClientDetailView`)

`frontend/src/views/clients/ClientDetailView.vue` at route `/clients/:id` (name `client-detail`) is the contextual hub for a client: inline-editable header, an `AssetTree` of the client's root assets, and recent inspections. The client name in `ClientsView` links here. Starting an inspection from a tree row opens `InspectionComposer` with the asset preselected; the header button opens it with the client preselected. Recent inspections are fetched **server-side** via `GET /submissions?client_id=` (no client-side filtering): the backend joins `assets.client_id`, so inspections with no asset are naturally excluded. `fetchSubmissions(page, pageSize, status?, formId?, createdBy?, assetId?, clientId?)` carries the `clientId` argument.

#### Attribute builders (zero-JSON)

Asset-type and asset attributes are edited with visual builders — **never** a raw JSON textarea:
- **`frontend/src/components/ui/AttributeSchemaBuilder.vue`** (`v-model` ↔ `attributes_schema`): a row table (name / type / required) emitting `Record<string, { type, required }>` or `null`. Reads the legacy `{ key: 'string' }` shape too. Used in `AssetTypesView` keyed by `form.id || 'new'` to remount on edit/reset.
- **`frontend/src/components/ui/AttributeValueEditor.vue`** (`v-model` ↔ `attributes_json`, `:schema` from the selected type): renders one typed input per schema attribute. The parent (`AssetsView`) resets `attributes_json` when the selected asset type changes.

Both preserve the existing store contracts (`attributes_schema` / `attributes_json` as `Record | null`).

#### Attachments service

`frontend/src/services/attachments.service.ts` exposes `listAttachments`, `createAttachment`, `deleteAttachment`. Uploads go through `frontend/src/services/uploads.service.ts` (`uploadFile` → `POST /uploads`) first, which returns a `{ url, mime_type, file_size }` object, then the URL is forwarded to `createAttachment`.

## Conventions worth knowing

- API version prefix is `/api/v1`; new routers are registered in [backend/app/api/v1/router.py](backend/app/api/v1/router.py).
- All ORM models inherit `UUIDPrimaryKeyMixin` + `TimestampMixin` from [backend/app/db/models/base.py](backend/app/db/models/base.py); PKs are PG `uuid` with `gen_random_uuid()` server default, so the `pgcrypto` extension (or PG 13+ `gen_random_uuid`) must be enabled in the database.
- Settings are loaded once via `lru_cache` in [backend/app/core/config.py](backend/app/core/config.py); `.env` lives at the **repo root** (not under `backend/`). `alembic.ini` has a hardcoded `sqlalchemy.url` for local dev — this does not affect the app at runtime, only the `alembic` CLI.
- Pydantic schemas with `model_dump(mode="json")` are the standard serializer in routers — keep that mode so UUIDs and datetimes serialize as strings inside the envelope.
- Migrations are written by hand (no autogenerate boilerplate comments). `id` column listed first. Run from repo root with `alembic`.
- Rate limiting uses `slowapi` (`backend/app/core/limiter.py`). Disabled in tests via the `disable_rate_limiting` fixture in conftest — never disable manually in individual tests.
