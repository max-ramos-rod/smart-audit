# Plano de Implementação — DR-0001 Fase 1 (Clients + AssetTypes + Assets)

**Status:** Proposta · **Data:** 2026-06-08
**Origem:** [SPEC r2](SPEC-DR-0001-Fase1-Ativos.md) · [ADR-0015](../adr/0015-modelo-de-ativos-genericos.md) · [DR-0001](../design-records/DR-0001-ativos-genericos.md)

Tarefas pequenas e independentes, cada uma implementável em **≤ 1 PR**, com critério de aceite,
arquivos impactados e testes. Ordenadas por dependência técnica.

## Grafo de dependências

```
T1 (migration + modelos)
 ├─ T2 (backend clients) ─────────── T6 (frontend clients)
 ├─ T3 (backend asset_types) ─────── T7 (frontend asset_types)
 └─ T4 (backend assets CRUD) ─ T5 (assets soft-delete cascata) ─ T8 (frontend assets)
T9 (finalização docs/ADR)  ← depende do backend (T1–T5)

Paralelizável: T2 ∥ T3 ; T6 ∥ T7 (após suas dependências).
```

| # | Tarefa | Depende | Camada | Tamanho |
|---|---|---|---|---|
| T1 | Migration + modelos ORM (3 tabelas) | — | DB | M |
| T2 | Backend Clients (slice vertical) | T1 | Backend | S |
| T3 | Backend AssetTypes (slice vertical) | T1 | Backend | S |
| T4 | Backend Assets — CRUD + árvore (sem cascata) | T1,T2,T3 | Backend | M |
| T5 | Backend Assets — soft delete em cascata + reativação | T4 | Backend | M |
| T6 | Frontend Clients | T2 | Frontend | S |
| T7 | Frontend AssetTypes | T3 | Frontend | M |
| T8 | Frontend Assets (cadastro raiz/componente + árvore) | T4,T5 | Frontend | M |
| T9 | Finalização: ADR→Aceita + DER/Arquitetura | T1–T5 | Docs | S |

---

## T1 — Migration + modelos ORM

**Objetivo.** Criar as tabelas `clients`, `asset_types`, `assets` (ordem de dependência) e os
modelos ORM, com os `CHECK`/índices da spec. Nenhuma rota ainda.

**Arquivos impactados**
- `backend/alembic/versions/<rev>_add_assets_clients_asset_types.py` (novo; `down_revision = "b0c1d2e3f4a5"`)
- `backend/app/db/models/clients.py`, `asset_types.py`, `assets.py` (novos)
- `backend/app/db/models/__init__.py` (imports + `__all__`)
- `backend/app/db/models/companies.py` (`back_populates="clients"`)

**Critérios de aceite**
- `alembic upgrade head` e `alembic downgrade -1` rodam limpos.
- Tabelas com colunas/tipos da spec; `CHECK ck_assets_client_only_on_root` e `ck_assets_status`
  presentes; índices criados; `id` listado primeiro em cada `create_table`.
- Modelos importam; árvore mapeada por self-`relationship` (`parent`/`components`); `ruff` e
  `mypy` verdes.

**Testes necessários**
- `backend/tests/integration/test_assets_schema.py` (mínimo): inserir via ORM um `Asset` raiz
  (ok) e um componente com `client_id` setado → **IntegrityError** (valida o `CHECK` M6);
  inserir `status` inválido → IntegrityError.

---

## T2 — Backend Clients (slice vertical)

**Objetivo.** Módulo `clients` completo: schemas, repository (flush), service (commit), router,
registro. CRUD + soft delete.

**Arquivos impactados**
- `backend/app/modules/clients/schemas.py`, `repository.py`, `service.py` (novos)
- `backend/app/api/v1/routers/clients.py` (novo)
- `backend/app/api/v1/router.py` (registrar `clients_router`)
- `backend/tests/integration/test_clients.py` (novo)

**Critérios de aceite**
- `GET/POST/PATCH/DELETE /api/v1/clients` no envelope `{data,meta}`/RFC 7807; paginação.
- Escrita = `get_manager_membership`; leitura = `get_current_membership`.
- `DELETE` faz soft delete (`is_active=false`); item some da listagem ativa.
- Isolamento por `company_id`; `ruff`/`mypy`/`pytest` verdes.

**Testes necessários** (`test_clients.py`)
- CRUD feliz; `DELETE` → soft delete (some da lista, ainda existe no banco).
- INSPECTOR em escrita → 403; leitura por membro comum → 200.
- Isolamento multiempresa (cliente de outra empresa → 404).
- Paginação (`assert_pagination_meta`).

---

## T3 — Backend AssetTypes (slice vertical)

**Objetivo.** Módulo `asset_types` completo. `attributes_schema` aceito **livre** (sem
validação — M1).

**Arquivos impactados**
- `backend/app/modules/asset_types/schemas.py`, `repository.py`, `service.py` (novos)
- `backend/app/api/v1/routers/asset_types.py` (novo)
- `backend/app/api/v1/router.py` (registrar `asset_types_router`)
- `backend/tests/integration/test_asset_types.py` (novo)

**Critérios de aceite**
- CRUD `/api/v1/asset-types`; `attributes_schema` opcional aceito sem validar conteúdo.
- Soft delete (`is_active=false`); escrita MANAGER+; isolamento; envelope/RFC 7807.

**Testes necessários** (`test_asset_types.py`)
- CRUD; criar tipo **sem** `attributes_schema` e **com** schema arbitrário (ambos 200, sem
  validação); soft delete; 403 INSPECTOR; isolamento.

---

## T4 — Backend Assets — CRUD + árvore (sem cascata)

**Objetivo.** Módulo `assets`: criar raiz/componente, listar com filtros, detalhe com filhos
diretos, update (sem `parent_asset_id`). Validações V1, V2 (parent imutável), V3 (client só
raiz), V8, V9. **Soft delete em cascata fica na T5.**

**Arquivos impactados**
- `backend/app/modules/assets/schemas.py`, `repository.py`, `service.py` (novos)
- `backend/app/api/v1/routers/assets.py` (novo)
- `backend/app/api/v1/router.py` (registrar `assets_router`)
- `backend/tests/integration/test_assets.py` (novo — parte CRUD/árvore/cliente/parent)

**Critérios de aceite**
- `POST /assets` cria raiz ou componente (`parent_asset_id` só aqui); `GET /assets/{id}` traz
  filhos diretos (`AssetDetailResponse.components`); `GET /assets` filtra por
  `asset_type_id`/`client_id`/`parent_asset_id`/`status`.
- V1: `asset_type_id`/`parent_asset_id`/`client_id` de outra empresa → 400/404.
- V2: `PATCH` alterando `parent_asset_id` → 400.
- V3: `client_id` em componente → 400 (além do `CHECK`).
- V8/V9: criar com tipo arquivado ou cliente inativo → 400.
- Escrita MANAGER+; isolamento; envelope/RFC 7807; `ruff`/`mypy`/`pytest` verdes.

**Testes necessários** (`test_assets.py` — parte 1)
- Criar raiz e componente; árvore profundidade ≥2 (CA2).
- Dois tipos de domínios diferentes sem mudança de schema (CA1).
- `attributes_json` aceito livre (M1).
- `client_id` em raiz (ok) e em componente (400) — CA4/M6.
- `client_id`/`asset_type_id` de outra empresa → rejeitado (CA4/V1).
- `PATCH parent_asset_id` → 400 (M5/V2).
- Listar por `client_id` retorna só os daquele cliente (CA4).
- Tipo arquivado/cliente inativo → 400 (V8/V9).
- Isolamento multiempresa (CA6).

---

## T5 — Backend Assets — soft delete em cascata + reativação

**Objetivo.** `DELETE /assets/{id}` desativa o ativo **e toda a subárvore** (transacional);
`PATCH status='active'` segue reativação top-down. (V6/V7.)

**Arquivos impactados**
- `backend/app/modules/assets/repository.py` (`deactivate_subtree` — CTE recursiva)
- `backend/app/modules/assets/service.py` (V6 no DELETE, V7 no PATCH status)
- `backend/app/api/v1/routers/assets.py` (DELETE/PATCH já existem; ajustar comportamento)
- `backend/tests/integration/test_assets.py` (novos casos — parte 2)

**Critérios de aceite**
- `DELETE` numa raiz com filhos → raiz e todos os descendentes ficam `status='inactive'` na
  mesma transação; **nenhum** ativo `active` sob ancestral `inactive` (invariante).
- `PATCH status='active'` num componente cujo pai está `inactive` → 400; reativação **não**
  cascateia para filhos.
- Auditoria `asset.deactivated` na raiz com contagem de descendentes.

**Testes necessários** (`test_assets.py` — parte 2)
- Cascata: criar raiz + 2 componentes → DELETE raiz → todos `inactive` (V6).
- Invariante: não existe filho `active` sob pai `inactive`.
- Reativação top-down: reativar componente com pai `inactive` → 400; reativar raiz, depois
  componente → ok; reativar raiz **não** reativa filhos automaticamente (V7).

---

## T6 — Frontend Clients

**Objetivo.** Tela de CRUD de clientes.

**Arquivos impactados**
- `frontend/src/types/clients.ts` (novo)
- `frontend/src/services/clients.service.ts` (novo; via `http`)
- `frontend/src/stores/clients/clients.store.ts` (novo)
- `frontend/src/views/clients/ClientsView.vue` (novo)
- `frontend/src/router/index.ts` (rota `/clients`)
- `frontend/src/__tests__/clients.store.test.ts`, `clients.service.test.ts` (novos)
- `frontend/e2e/clients.spec.ts` (novo)

**Critérios de aceite**
- Listar/criar/editar/desativar cliente; usa `http` central (nunca `axios` direto); rota sob
  `/app/`; `npm run build` (vue-tsc) e `npm test` verdes.

**Testes necessários**
- Vitest: store (load/create/update/revoke mockando o service) + service (chama `/clients`).
- E2E (mockado): lista, criar com sucesso, desativar.

---

## T7 — Frontend AssetTypes

**Objetivo.** Tela de tipos de ativo, com editor de `attributes_schema` como **JSON livre**
(sem validação — M1).

**Arquivos impactados**
- `frontend/src/types/asset-types.ts`, `services/asset-types.service.ts`,
  `stores/asset-types/asset-types.store.ts`, `views/asset-types/AssetTypesView.vue` (novos)
- `frontend/src/router/index.ts` (rota `/asset-types`)
- `frontend/src/__tests__/asset-types.{store,service}.test.ts`; `frontend/e2e/asset-types.spec.ts`

**Critérios de aceite**
- CRUD de tipos; campo `attributes_schema` editável como texto JSON livre; soft delete; build/
  test verdes.

**Testes necessários**
- Vitest store/service; E2E lista + criar + desativar.

---

## T8 — Frontend Assets

**Objetivo.** Cadastro de ativo (raiz e componente), visualização de **filhos diretos**, filtros
por tipo/cliente/status. `parent` definido só na criação (M5). Sem árvore recursiva (B1).

**Arquivos impactados**
- `frontend/src/types/assets.ts`, `services/assets.service.ts`, `stores/assets/assets.store.ts`,
  `views/assets/AssetsView.vue` (+ componente de criação de componente) (novos)
- `frontend/src/router/index.ts` (rota `/assets`)
- `frontend/src/__tests__/assets.{store,service}.test.ts`; `frontend/e2e/assets.spec.ts`

**Critérios de aceite**
- Criar raiz com `client_id` opcional; criar componente sob uma raiz; ver filhos diretos;
  filtrar lista; desativar (cascata feita no backend). UI não expõe edição de `parent`.
- Build/test verdes; `http` central; rota `/app/`.

**Testes necessários**
- Vitest store/service; E2E: criar raiz, adicionar componente, filtrar por cliente, desativar.

---

## T9 — Finalização: ADR → Aceita + docs

**Objetivo.** Consolidar a decisão na documentação após a implementação.

**Arquivos impactados**
- `docs/adr/0015-modelo-de-ativos-genericos.md` (Status → **Aceita**, citar pontos do código)
- `docs/adr/README.md` (status 0015 → Aceita)
- `docs/DER_Smart_Audit.md` (3 tabelas novas + relacionamentos + migration na lista)
- `docs/Arquitetura_Smart_Audit.md` (bounded contexts `clients`/`asset_types`/`assets`, rotas,
  consolidado)

**Critérios de aceite**
- ADR-0015 Aceita citando arquivos/símbolos reais; DER e Arquitetura refletem o implementado;
  contagens de teste atualizadas.

**Testes necessários** — n/a (documentação); verificação de consistência docs × código.

---

## Definition of Done da Fase 1 (agregado)

- T1–T5: backend completo; `ruff`/`mypy`/`pytest` verdes; migration reversível; soft delete de
  árvore (V6) e reativação top-down (V7) cobertos.
- T6–T8: frontend completo; `npm run build`/`npm test`/E2E verdes.
- T9: ADR-0015 Aceita; DER/Arquitetura atualizados.
