# AI_WORKFLOWS — Comandos e receitas

Comandos de `CLAUDE.md` (autoritativo) e receitas derivadas dos padrões reais do código.
Ambiente: Windows PowerShell; virtualenv na raiz (`.venv`). Alembic roda do **repo root**.

## Backend

```powershell
# Instalar (editável) com extras de dev
pip install -e ".[dev]"

# Rodar a API (lê .env da raiz)
uvicorn app.main:app --reload --app-dir backend --port 8003

# Migrations (rodar da raiz)
alembic upgrade head
alembic revision -m "<mensagem>"          # migration escrita a mao, id primeiro

# Testes — SEMPRE com python -m
python -m pytest                          # suite completa
python -m pytest backend/tests/integration/test_forms.py
python -m pytest -k test_login_and_me
python -m pytest backend/tests/unit/

# Lint
ruff check backend
ruff check --fix backend

# Seed (precisa do DB no ar + .env)
python backend/scripts/create_user.py --name "Admin" --email admin@smartaudit.local --password admin123456
python backend/scripts/link_user_company.py --email admin@smartaudit.local --company-name "Acme" --company-slug acme --role OWNER
```

## Frontend

```powershell
cd frontend
npm install
npm run dev        # Vite em 0.0.0.0:5174 (base /app/ só afeta build)
npm run build      # vue-tsc --noEmit + vite build (type-check faz parte do build)
npm test           # Vitest (run once)
npm run test:e2e   # Playwright (sobe dev server na 5200, API mockada)
npm run lint       # ESLint (flat config) — .ts e .vue
npm run lint:fix   # ESLint com --fix
npm run format     # Prettier (escopo: src/**/*.ts e e2e/**/*.ts)
npm run format:check  # Prettier em modo verificacao (usado no CI)
```

Lint/format (verificados no CI, job `frontend`):

- **ESLint** cobre `.ts` e `.vue` (flat config em `frontend/eslint.config.js`; formatacao desligada via `@vue/eslint-config-prettier`). As regras `@typescript-eslint/no-explicit-any` e
  `no-unused-vars` estao como **`warn`** (divida pre-existente; nao bloqueiam o CI). Codigo novo deve evitar ambos.
- **Prettier** (`frontend/.prettierrc.json`: `semi:false`, `singleQuote:true`, `printWidth:100`) tem
  escopo **apenas `.ts`**. `.vue` esta **fora** de proposito: com `semi:false`, o Prettier remove o `;`
  separador de handlers inline com multiplos statements (ex.: `@click="a; b()"`), gerando template
  invalido. `.css` tambem esta fora (evita churn grande no design system). Formatacao de `.vue`/`.css`
  fica a cargo do editor (`.editorconfig`).

## Infra de teste (backend)

- `pytest-asyncio` em `asyncio_mode = "auto"`; loop de evento **único por sessão**.
- Isolamento por **savepoint**: uma `AsyncConnection` + transação externa por teste, rollback
  no teardown — **sem SQL de limpeza**.
- HTTP em testes é `httpx.AsyncClient` + `ASGITransport` — **todas** as chamadas são `await`.
- O fixture `client` já desabilita o rate limiter.
- Fixtures disponíveis (`backend/tests/conftest.py`): `client`, `auth_headers` (OWNER),
  `inspector_headers` (INSPECTOR), `viewer_headers` (VIEWER), `seeded_user`, `inspector_user`,
  `viewer_user`, `multi_company_user`.
- Pré-requisito: `alembic upgrade head` contra um PostgreSQL real.

## Receita: adicionar um endpoint

1. **Schema** (`modules/<dominio>/schemas.py`) — request com `Field(min_length/max_length)`.
2. **Repository** (`repository.py`) — método nomeado; usa `_save`/`_get_one`/`_paginate_select`; **só `flush`**.
3. **Service** (`service.py`) — regra de negócio + validação; faz o `db.commit()`.
4. **Router** (`api/v1/routers/<dominio>.py`) — fino; injeta o guard de papel certo
   (`get_current/operator/manager/admin/owner_membership`); serializa com
   `success_response`/`paginated_response`.
5. **Registrar** o router em `backend/app/api/v1/router.py` (se for módulo novo).

## Receita: adicionar um tipo de campo

Atualize em `backend/app/modules/submissions/service.py`:
`normalize_value` · `serialize_raw_value` · `extract_value` · (se contar no score)
`calculate_score`/`calculate_score_breakdown`. Crie migration alterando o
`CHECK field_type` de `form_fields`. No frontend, ajuste `FieldType`
(`frontend/src/types/forms.ts`) e `FormFieldEditor.vue`.

## Receita: registrar um evento de auditoria

No service, antes do commit:

```python
await self.audit_repository.log(
    db,
    company_id=str(membership.company_id),
    actor_id=str(membership.user_id),
    action="<dominio>.<acao>",        # ex.: user.created
    target_user_id=...,               # opcional
    meta={...},                       # opcional
)
await db.commit()
```

Eventos hoje emitidos: `user.created`, `user.invited`, `membership.revoked`,
`membership.reactivated`, `team.deactivated`, `company.deactivated`.

## Receita: nova migration

`alembic revision -m "..."` no repo root → escreva `upgrade`/`downgrade` à mão (`id`
primeiro nas tabelas) → encadeie `down_revision` na última revisão → `alembic upgrade head`.

## Frontend: padrões

- Stores Pinia por domínio (`stores/<dominio>`), serviços em `services/<dominio>.service.ts`,
  views em `views/<dominio>/`. Alias `@` → `frontend/src`.
- HTTP só via `services/api/http.ts`. Token e `company-id` em `localStorage`
  (`services/api/storage.ts`).
- Testes Vitest em `frontend/src/__tests__/`; use `setActivePinia(createPinia())` +
  `localStorage.clear()` em `beforeEach`; mocke serviços com `vi.mock`.
