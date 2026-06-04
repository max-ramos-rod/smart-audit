# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

Monorepo with two deployables:

- `backend/` — FastAPI service (Python 3.12, SQLAlchemy 2.0, Alembic, PostgreSQL). Installed as the `smart-audit-backend` package via `pyproject.toml` at the repo root (`package-dir = backend/`).
- `frontend/` — Vue 3 SPA (Vite, Pinia, Vue Router, Axios, TailwindCSS 4).
- `docs/Arquitetura_Smart_Audit.md` and `docs/DER_Smart_Audit.md` — source of truth for domain decisions and ER model.
- `db/schema_v1.sql` — reference schema snapshot; canonical schema is managed by Alembic in `backend/alembic/versions/`.
- `db/fix_postgres_ownership.sql` — helper script to fix PostgreSQL ownership when setting up a local database.

## Common commands

All Python commands assume the repo-root virtualenv (`.venv`). On Windows PowerShell, activate with `.\.venv\Scripts\Activate.ps1`. Alembic is configured at the repo root (`alembic.ini` points at `backend/alembic`), so always run `alembic` from the repo root.

### Backend

```powershell
# Install (editable) with dev extras
pip install -e ".[dev]"

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

# Seed scripts (require DB up + .env configured)
python backend/scripts/create_user.py --name "Admin" --email admin@smartaudit.local --password admin123456
python backend/scripts/link_user_company.py --email admin@smartaudit.local --company-name "Acme" --company-slug acme --role OWNER
```

### Frontend

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
```

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

- **`boolean`**: `{ weight?: number, allow_na?: boolean, visible_if?: VisibleIf }`
  - `weight` (default 1) — multiplier used in score calculation
  - `allow_na` — enables a "N/A" answer option
- **`select`**: `{ options: string[], visible_if?: VisibleIf }`
- **`text` / `number` / `date`**: `{ visible_if?: VisibleIf }`
- **`section`**: always `{}` — no config allowed; auto-keyed as `__section_{position}__` by the form builder

`VisibleIf` shape: `{ field_key: string, operator: "eq" | "neq", value: string }`. The backend evaluates it in `finish_submission` to skip required-field validation for hidden fields. The frontend evaluates it in `visibleFields` computed to hide/show fields dynamically.

#### Score calculation

Score is 0–100, calculated only from `boolean` fields with at least one answered field. N/A and unanswered fields are excluded from both numerator and denominator. Each boolean field has an optional `weight` (`config_json.weight`, default 1). Formula: `round((sum of weight for conformes) / (sum of weight for answered non-na) * 100, 2)`. See `calculate_score` and `calculate_score_breakdown` in [backend/app/modules/submissions/service.py](backend/app/modules/submissions/service.py).

### Attachments module (evidence)

Evidence is **not** a field type — it is a capability attached to any field during an inspection. The `attachments` bounded context lives under `backend/app/modules/attachments/` and is served at `/submissions/{id}/attachments`.

**Data model:** `Attachment` → FK(CASCADE) → `SubmissionValue` → FK → `FormField`. An attachment is always linked to a `submission_value`, which is created on-demand if it doesn't exist yet for the target field.

**Endpoints (all require JWT + X-Company-Id):**
- `GET  /submissions/{id}/attachments?page=1&page_size=N` — lists all attachments for a submission
- `POST /submissions/{id}/attachments` — creates an attachment; body: `{ field_key, file_url, mime_type, file_size, thumbnail_url? }`; validates that `field_key` exists in the form version
- `DELETE /submissions/{id}/attachments/{attachment_id}` — deletes attachment and removes local file if stored on disk

**Side effect on create:** `AttachmentService.create_attachment` also writes `answers_json[field_key] = file_url` on the submission snapshot, so the field appears as answered in the denormalized store.

**Serialize shape** (`AttachmentResponse`): `id`, `submission_id`, `field_key` (resolved from `submission_value.form_field.key`), `file_url`, `thumbnail_url`, `mime_type`, `file_size`, `created_at`.

**Allowed MIME types for uploads:** `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `video/quicktime`, `video/x-msvideo`, `audio/mpeg`, `audio/wav`, `audio/ogg`, `audio/mp4`, `application/pdf` (enforced in uploads router). Size limits: images 10 MB, PDF 20 MB, audio 50 MB, video 200 MB.

### Teams module

`teams` and `team_members` are a separate bounded context under `backend/app/modules/teams/`. Teams belong to a company; members must already be members of that company (validated in `TeamService.add_member`). Read endpoints use `get_current_membership`; write endpoints require `get_manager_membership`.

### Uploads

Uploads are handled directly in [backend/app/api/v1/routers/uploads.py](backend/app/api/v1/routers/uploads.py) — no separate module. Files are written to `settings.upload_dir/<company_id>/<uuid>.<ext>` and served via FastAPI `StaticFiles` mounted at `/uploads`. The returned URL uses `settings.upload_base_url` as prefix. Allowed MIME types: images (JPEG/PNG/WebP), video (MP4/MOV/AVI), audio (MP3/WAV/OGG/M4A), PDF. Size limits: images 10 MB, PDF 20 MB, audio 50 MB, video 200 MB.

### Frontend

SPA structured by domain (`stores/<domain>`, `services/<domain>.service.ts`, `views/<domain>/`). The `@` alias resolves to `frontend/src`.

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

**`frontend/src/components/forms/FormFieldEditor.vue`** — reusable field editor used in the version composer (FormDetailView). Accepts a `FormFieldCreatePayload` via `v-model`, `index`, `otherFields` (other answerable fields, for `visible_if` config), and `showRemove`. Emits `remove`.

**`frontend/src/components/submissions/InspectionFieldRow.vue`** — renders a single field row inside the inspection list and normal list modes of `SubmissionDetailView`. Props: `field`, `answer`, `conformityStatus`, `conformityJustification`, `isCompleted`, `isPendingRequired`, `evidenceAttachments`, `evidenceUploading`, `evidenceError`, `compact?`. The `compact` prop controls visual density: `true` → inspection list (inline evidence chips, no justification text); `false` (default) → normal list (full card evidence with file sizes, justification on completion). Card view (swipe mode) is rendered inline in `SubmissionDetailView` and does not use this component.

#### Submission inspection UI (`SubmissionDetailView`)

The main inspection screen has three mutually exclusive display modes:

1. **Normal list mode** (default, also for completed inspections) — all fields rendered in a scrollable list. Completed inspections are read-only.
2. **Inspection card mode** (`inspectionMode = true`, `viewMode = 'card'`) — one field at a time, swipe gestures (left = Não conforme, right = Sim/Conforme). Only available for in-progress inspections.
3. **Inspection list mode** (`inspectionMode = true`, `viewMode = 'list'`) — compact scrollable list while in inspection flow.

Evidence (attachments) is rendered **under each field** in all three modes via `evidenceAttachments: reactive<Record<string, AttachmentItem[]>>`, keyed by `field.key`. Loaded once in `onMounted` via `loadEvidenceAttachments()` → `listAttachments(submissionId)`. New uploads are pushed to the reactive dict immediately without a reload.

The upload button only shows for non-completed inspections (`v-if="!isCompleted"`). For completed inspections, the evidence section shows only if there are attachments. A summary line ("X evidência(s) registrada(s)" or "Sem evidências registradas") appears at the top of the fields area for completed inspections after evidence loads.

#### Report view (`SubmissionReportView`)

Read-only summary for completed (and in-progress) inspections accessible at `/submissions/:id/report`. Shows score, breakdown, boolean field results, non-boolean field values, and any evidence (attachments) for each field as clickable links. PDF export via `exportSubmissionPdf` → backend `/submissions/{id}/export`.

#### Attachments service

`frontend/src/services/attachments.service.ts` exposes `listAttachments`, `createAttachment`, `deleteAttachment`. Uploads go through `frontend/src/services/uploads.service.ts` (`uploadFile` → `POST /uploads`) first, which returns a `{ url, mime_type, file_size }` object, then the URL is forwarded to `createAttachment`.

## Conventions worth knowing

- API version prefix is `/api/v1`; new routers are registered in [backend/app/api/v1/router.py](backend/app/api/v1/router.py).
- All ORM models inherit `UUIDPrimaryKeyMixin` + `TimestampMixin` from [backend/app/db/models/base.py](backend/app/db/models/base.py); PKs are PG `uuid` with `gen_random_uuid()` server default, so the `pgcrypto` extension (or PG 13+ `gen_random_uuid`) must be enabled in the database.
- Settings are loaded once via `lru_cache` in [backend/app/core/config.py](backend/app/core/config.py); `.env` lives at the **repo root** (not under `backend/`). `alembic.ini` has a hardcoded `sqlalchemy.url` for local dev — this does not affect the app at runtime, only the `alembic` CLI.
- Pydantic schemas with `model_dump(mode="json")` are the standard serializer in routers — keep that mode so UUIDs and datetimes serialize as strings inside the envelope.
- Migrations are written by hand (no autogenerate boilerplate comments). `id` column listed first. Run from repo root with `alembic`.
- Rate limiting uses `slowapi` (`backend/app/core/limiter.py`). Disabled in tests via the `disable_rate_limiting` fixture in conftest — never disable manually in individual tests.
