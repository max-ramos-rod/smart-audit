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
uvicorn app.main:app --reload --app-dir backend

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
npm run dev      # Vite on 0.0.0.0:5173
npm run build    # runs `vue-tsc --noEmit` then vite build — type-check is part of build
npm run preview
npm test         # Vitest (run once)
npm run test:watch  # Vitest (watch mode)
```

The frontend expects the backend at `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8000/api/v1`). Copy `frontend/.env.example` to `frontend/.env.local` to override locally.

### Tests need a real database

`backend/tests/conftest.py` connects to the database configured in `.env` and uses SQLAlchemy savepoint isolation (open a connection + transaction per test, rollback at teardown). There is **no** mock/SQLite shortcut — integration tests will fail if Postgres is not reachable and migrated.

```powershell
# Before running tests for the first time:
alembic upgrade head
python -m pytest
```

The `client` fixture disables the rate limiter automatically (`limiter.enabled = False`) — do not disable it manually in individual tests.

Fixtures available in `conftest.py`:

| Fixture | Role | Description |
|---|---|---|
| `client` | — | TestClient with DB override + rate limiter disabled |
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

### Teams module

`teams` and `team_members` are a separate bounded context under `backend/app/modules/teams/`. Teams belong to a company; members must already be members of that company (validated in `TeamService.add_member`). Read endpoints use `get_current_membership`; write endpoints require `get_manager_membership`.

### Uploads

Uploads are handled directly in [backend/app/api/v1/routers/uploads.py](backend/app/api/v1/routers/uploads.py) — no separate module. Files are written to `settings.upload_dir/<company_id>/<uuid>.<ext>` and served via FastAPI `StaticFiles` mounted at `/uploads`. The returned URL uses `settings.upload_base_url` as prefix. Allowed MIME types: `image/jpeg`, `image/png`, `image/webp`. Max size: 10 MB.

### Frontend

SPA structured by domain (`stores/<domain>`, `services/<domain>.service.ts`, `views/<domain>/`). The `@` alias resolves to `frontend/src`.

- Auth/session state is bootstrapped in the router guard ([frontend/src/router/index.ts](frontend/src/router/index.ts)): if a route requires auth and a token exists, it calls `useContextStore().bootstrap()` to load `/me/companies` + `/me/context` before rendering. Without that, downstream stores will not have an active company. After bootstrap, `authStore.user` is synced from `contextStore.context.user` if null.
- HTTP client is centralized in [frontend/src/services/api/http.ts](frontend/src/services/api/http.ts); never call `axios` directly from views/stores.
- Token + active company id are persisted in `localStorage` under `smart-audit.token` / `smart-audit.company-id` via [frontend/src/services/api/storage.ts](frontend/src/services/api/storage.ts).
- Frontend tests live in `frontend/src/__tests__/` and run with Vitest (`npm test`). Use `setActivePinia(createPinia())` + `localStorage.clear()` in `beforeEach`. Mock service modules with `vi.mock`.

## Conventions worth knowing

- API version prefix is `/api/v1`; new routers are registered in [backend/app/api/v1/router.py](backend/app/api/v1/router.py).
- All ORM models inherit `UUIDPrimaryKeyMixin` + `TimestampMixin` from [backend/app/db/models/base.py](backend/app/db/models/base.py); PKs are PG `uuid` with `gen_random_uuid()` server default, so the `pgcrypto` extension (or PG 13+ `gen_random_uuid`) must be enabled in the database.
- Settings are loaded once via `lru_cache` in [backend/app/core/config.py](backend/app/core/config.py); `.env` lives at the **repo root** (not under `backend/`). `alembic.ini` has a hardcoded `sqlalchemy.url` for local dev — this does not affect the app at runtime, only the `alembic` CLI.
- Pydantic schemas with `model_dump(mode="json")` are the standard serializer in routers — keep that mode so UUIDs and datetimes serialize as strings inside the envelope.
- Migrations are written by hand (no autogenerate boilerplate comments). `id` column listed first. Run from repo root with `alembic`.
- Rate limiting uses `slowapi` (`backend/app/core/limiter.py`). Disabled in tests via the `disable_rate_limiting` fixture in conftest — never disable manually in individual tests.
