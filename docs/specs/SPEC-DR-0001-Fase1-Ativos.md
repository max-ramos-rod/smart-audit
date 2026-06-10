# Spec Técnica — DR-0001 Fase 1 (Clients + AssetTypes + Assets)

**Status:** Proposta · **Data:** 2026-06-08
**Origem:** [DR-0001](../design-records/DR-0001-ativos-genericos.md) ·
[ADR-0015](../adr/0015-modelo-de-ativos-genericos.md)
**Escopo:** **somente a Fase 1** do DR-0001 — cadastro de `clients` (mínimo), `asset_types`
(sem blueprint automático) e `assets` (árvore, `client_id` nullable). **Fora desta fase:**
`asset_type_components` (Fase 2) e `submissions.asset_id` (Fase 3).

> Esta spec desce ao "como" concreto (schema, migration, API, camadas) respeitando os padrões
> verificados em `CLAUDE.md`, `docs/DER_Smart_Audit.md` e os ADRs. Ainda **não é implementação**;
> é o contrato a partir do qual se geram tasks/testes/código.

---

## 1. Visão geral

Três novos bounded contexts em `backend/app/modules/`: `clients`, `asset_types`, `assets`
(cada um `service.py` / `repository.py` / `schemas.py`, padrão ADR-0001). Três tabelas novas.
Nenhuma alteração em tabelas existentes nesta fase.

Regras transversais (ADRs): tudo isolado por `company_id` (ADR-0003); escrita = `MANAGER+`
(`get_manager_membership`), leitura = qualquer membro (`get_current_membership`) (ADR-0004);
soft delete (ADR-0009); commit no service, flush no repository (ADR-0001); envelope `{data,meta}`
+ RFC 7807 (ADR-0011); schemas de request com `Field(min_length/max_length)`.

---

## 2. Modelo de dados (DDL conceitual)

> Todas herdam `UUIDPrimaryKeyMixin` (`id UUID PK server_default gen_random_uuid()`) e
> `TimestampMixin` (`created_at`/`updated_at TIMESTAMPTZ server_default now()`).

### 2.1 `clients`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | `gen_random_uuid()` |
| `company_id` | UUID FK → `companies.id` ON DELETE CASCADE | NOT NULL |
| `name` | VARCHAR(150) | NOT NULL |
| `is_active` | BOOLEAN | NOT NULL, `server_default 'true'` (soft delete) |
| `created_at`/`updated_at` | TIMESTAMPTZ | mixin |

Índices/constraints: `INDEX ix_clients_company_id (company_id)`.

### 2.2 `asset_types`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → `companies.id` ON DELETE CASCADE | NOT NULL |
| `name` | VARCHAR(150) | NOT NULL |
| `slug` | VARCHAR(120) | NOT NULL — chave humana estável |
| `description` | TEXT | NULL |
| `attributes_schema` | JSONB | **NULL** (opcional, Q5) — quando presente, valida `attributes_json` |
| `is_active` | BOOLEAN | NOT NULL, `server_default 'true'` (soft delete) |
| `created_at`/`updated_at` | TIMESTAMPTZ | |

Constraints: `UNIQUE(company_id, slug)` (`uq_asset_types_company_slug`);
`INDEX ix_asset_types_company_id (company_id)`.

### 2.3 `assets`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → `companies.id` ON DELETE CASCADE | NOT NULL |
| `asset_type_id` | UUID FK → `asset_types.id` | NOT NULL |
| `parent_asset_id` | UUID FK → `assets.id` ON DELETE CASCADE | **NULL** = raiz; preenchido = componente |
| `client_id` | UUID FK → `clients.id` | **NULL** = patrimônio próprio; preenchido = ativo de cliente (discriminador) |
| `identifier` | VARCHAR(180) | NOT NULL — "Placa ABC-1234", "Roda DD" |
| `attributes_json` | JSONB | NOT NULL, `server_default '{}'::jsonb` |
| `status` | VARCHAR(20) | NOT NULL, `server_default 'active'`, `CHECK status IN ('active','inactive','retired')` |
| `created_at`/`updated_at` | TIMESTAMPTZ | |

Índices: `ix_assets_company_parent (company_id, parent_asset_id)`,
`ix_assets_company_type (company_id, asset_type_id)`,
`ix_assets_company_client (company_id, client_id)`.

> **Integridade que a FK NÃO garante** (validar no service): `asset_type_id`, `parent_asset_id` e
> `client_id` devem pertencer à **mesma** `company_id`; a árvore não pode formar ciclo. Ver §6.

---

## 3. Migration Alembic

- **Uma** revisão criando as três tabelas **na ordem de dependência**: `clients` → `asset_types`
  → `assets` (assets referencia ambas + a si mesma).
- `down_revision = "b0c1d2e3f4a5"` (head atual = `create_audit_logs`).
- Escrita **à mão** (sem autogenerate), `id` listado primeiro em cada `create_table` (padrão do
  projeto). `downgrade` faz `drop_table` na ordem inversa (`assets` → `asset_types` → `clients`).
- `CHECK` de `status` e `UNIQUE(company_id, slug)` declarados na criação.
- Requer extensão `pgcrypto`/PG13+ para `gen_random_uuid()` (já assumido no projeto).

Sugestão de nome: `c1d2e3f4a5b6_add_assets_clients_asset_types.py`.

---

## 4. Modelos ORM (`backend/app/db/models/`)

Padrão idêntico ao `teams.py`: herdar `(UUIDPrimaryKeyMixin, TimestampMixin, Base)`,
`__tablename__`, `__table_args__` com `Index`/`UniqueConstraint`/`CheckConstraint`, FKs com
`ondelete`, `relationship` com `back_populates`.

- `Client` (`clients`) — `company = relationship("Company", back_populates="clients")`.
- `AssetType` (`asset_types`) — `company = relationship(...)`; `assets = relationship("Asset", back_populates="asset_type")`.
- `Asset` (`assets`):
  - `asset_type = relationship("AssetType", back_populates="assets")`
  - `client = relationship("Client")`
  - **árvore:** `parent = relationship("Asset", remote_side=[id], back_populates="components")`;
    `components = relationship("Asset", back_populates="parent", cascade="all, delete-orphan")`
- Registrar os três em `app/db/models/__init__.py` (imports + `__all__`).
- `Company` ganha `back_populates` para `clients` (e opcionalmente `asset_types`).

> Regra async (ADR-0002): nada de lazy load. Onde a árvore/relacionamentos forem acessados após
> a query, usar `selectinload` (ex.: `selectinload(Asset.components)`,
> `selectinload(Asset.asset_type)`).

---

## 5. Schemas Pydantic (`schemas.py` por módulo)

Todo campo `str` de request com `Field(min_length=…, max_length=…)`. Serialização com
`model_dump(mode="json")` nos routers.

### Clients
```
ClientCreateRequest:   name: Field(2,150)
ClientUpdateRequest:   name?: Field(2,150); is_active?: bool
ClientResponse:        id; name; is_active
ClientListItemResponse: id; name; is_active
```

### AssetTypes
```
AssetTypeCreateRequest: name: Field(2,150); slug: Field(2,120);
                        description?: Field(max=2000); attributes_schema?: dict
AssetTypeUpdateRequest: name?; description?; attributes_schema?; is_active?
AssetTypeResponse:      id; name; slug; description; attributes_schema; is_active
```

### Assets
```
AssetCreateRequest: asset_type_id: Field(1,36); identifier: Field(2,180);
                    parent_asset_id?: Field(1,36); client_id?: Field(1,36);
                    attributes_json?: dict
AssetUpdateRequest: identifier?: Field(2,180); parent_asset_id?; client_id?;
                    attributes_json?; status?: Field(1,20)
AssetResponse:      id; asset_type_id; identifier; parent_asset_id; client_id;
                    attributes_json; status
AssetDetailResponse(AssetResponse): components: list[AssetResponse]   # filhos diretos
```

`status` validado por `field_validator` contra `{active, inactive, retired}` (espelha o padrão
de `submission_conformities`).

---

## 6. Repositórios (`repository.py`) — flush, sem commit

Cada um estende `SQLAlchemyRepository[Model]` e expõe **métodos nomeados** (não chamar `_save`
do service). Reads filtram por `company_id` e usam `populate_existing` (base).

- **ClientRepository:** `list_by_company(db, company_id, params, is_active?)`,
  `get_company_client(db, company_id, client_id)`, `create_client(db, client)`,
  `get_by_id_in_company(...)`.
- **AssetTypeRepository:** `list_by_company(...)`, `get_company_type(...)`,
  `get_by_slug(db, company_id, slug)`, `create_asset_type(...)`.
- **AssetRepository:** `list_by_company(db, company_id, params, filters)` (filtros:
  `asset_type_id`, `client_id`, `parent_asset_id`, `status`), `get_company_asset(db, company_id,
  asset_id)` (com `selectinload(components, asset_type, client)`), `list_children(db, parent_id)`,
  `create_asset(...)`, `is_descendant(db, asset_id, candidate_ancestor_id)` (para checagem de
  ciclo via CTE recursiva ou walk de ancestrais).

---

## 7. Serviços (`service.py`) — regras de negócio + commit

### Validações (invariantes do ADR-0015 / CA do DR-0001)

- **V1 (isolamento).** Ao criar/editar `Asset`: `asset_type_id`, `parent_asset_id` e `client_id`
  (quando informados) devem existir e pertencer à `membership.company_id`. Senão → 400/404.
- **V2 (ciclo).** No `create`/`update` com `parent_asset_id`: o pai não pode ser o próprio ativo
  nem um descendente dele (`AssetRepository.is_descendant`). Senão → 400 (INV3).
- **V3 (atributos).** Se o `AssetType.attributes_schema` estiver presente, validar
  `attributes_json` contra ele (chaves/typing) no service; ausente ⇒ aceitar livre (Q5).
- **V4 (slug único).** `AssetType.slug` único por empresa (validar antes de inserir; o
  `UNIQUE` do banco é a barreira final).
- **V5 (soft delete).** `DELETE /clients/{id}` e `/asset-types/{id}` ⇒ `is_active = false`;
  `DELETE /assets/{id}` ⇒ `status = 'inactive'`. Nunca remover fisicamente (ADR-0009).
- **V6 (tipo ativo).** Criar `Asset` exige `AssetType.is_active = true` (tipo arquivado bloqueia
  novas instâncias; instâncias existentes permanecem).
- **V7 (cliente ativo).** `client_id`, se informado, deve referenciar `Client.is_active = true`.

Cada método de escrita faz as validações, chama o método nomeado do repositório (flush) e dá
`await db.commit()` ao final. Auditoria via `AuditLogRepository.log` (ver §9) antes do commit.

---

## 8. Endpoints REST (`backend/app/api/v1/routers/`)

Registrar três routers em `api/v1/router.py`. Envelope `{data, meta}` / `paginated_response`.
Escrita = `Depends(get_manager_membership)`; leitura = `Depends(get_current_membership)`.

### Clients — `/api/v1/clients`
| Método | Rota | Guard | Descrição |
|---|---|---|---|
| GET | `/clients?page&page_size&is_active` | current | Lista paginada |
| GET | `/clients/{id}` | current | Detalhe |
| POST | `/clients` | manager | Cria |
| PATCH | `/clients/{id}` | manager | Atualiza nome/is_active |
| DELETE | `/clients/{id}` | manager | Soft delete (`is_active=false`) |

### Asset Types — `/api/v1/asset-types`
| Método | Rota | Guard | Descrição |
|---|---|---|---|
| GET | `/asset-types?page&page_size&is_active` | current | Lista |
| GET | `/asset-types/{id}` | current | Detalhe |
| POST | `/asset-types` | manager | Cria (valida slug único) |
| PATCH | `/asset-types/{id}` | manager | Atualiza |
| DELETE | `/asset-types/{id}` | manager | Soft delete (`is_active=false`) |

### Assets — `/api/v1/assets`
| Método | Rota | Guard | Descrição |
|---|---|---|---|
| GET | `/assets?page&page_size&asset_type_id&client_id&parent_asset_id&status` | current | Lista filtrada |
| GET | `/assets/{id}` | current | Detalhe + filhos diretos (`components`) |
| GET | `/assets/{id}/tree` | current | (opcional) subárvore recursiva |
| POST | `/assets` | manager | Cria (raiz ou componente; valida V1–V3,V6,V7) |
| PATCH | `/assets/{id}` | manager | Atualiza (reparent valida ciclo) |
| DELETE | `/assets/{id}` | manager | Soft delete (`status='inactive'`) |

---

## 9. Auditoria

Eventos em `audit_logs` (padrão existente), antes do commit:
`client.created`, `asset_type.created`, `asset.created` (mínimo); opcionalmente `*.updated` e
`*.deactivated`. `meta` carrega nome/identificador e ids relevantes.

---

## 10. Frontend (resumo — detalhe em spec de UI)

- `types/`: `Client`, `AssetType`, `Asset` (+ payloads create/update).
- `services/`: `clients.service.ts`, `asset-types.service.ts`, `assets.service.ts` (via `http`).
- `stores/`: store por domínio (Pinia), padrão dos existentes.
- `views/`: `clients/`, `asset-types/` (com editor de `attributes_schema`), `assets/` (cadastro
  + visualização de árvore + filtro por tipo/cliente). Base `/app/`. `vue-tsc` no build.

---

## 11. Testes (`backend/tests/integration/`)

Convenção: savepoint isolation, fixtures `auth_headers` (OWNER/MANAGER+) e `inspector_headers`
(para checar 403), `python -m pytest`. Casos mínimos (mapeados aos CA do DR-0001):

- **Clients/AssetTypes:** CRUD; soft delete some da listagem ativa; slug duplicado → 400 (CA?);
  escrita por INSPECTOR → 403; isolamento multiempresa.
- **Assets:** criar raiz e componente (árvore profundidade ≥2) → CA2; criar de dois domínios
  sem schema novo → CA1; `client_id` de outra empresa → rejeitado (CA4); criar com/sem
  `client_id` e listar por cliente → CA4; ciclo na árvore → 400 (CA7); `attributes_json` válido
  contra `attributes_schema` quando presente; tipo arquivado bloqueia nova instância (V6).
- **Isolamento (CA6):** nenhuma entidade vaza entre empresas.

---

## 12. Fora desta fase (referência)

- **`asset_type_components` (blueprint) + expansão automática** → Fase 2.
- **`submissions.asset_id` (vínculo inspeção→ativo)** → Fase 3 (destrava DR-0002).
- **Atributos ricos de `Client` (CNPJ, contato)** → Fase 4 / DR-0005.
- **Inspeção por componente** (asset_id em values/conformities) → DR-0002 (toca ADR-0006).

---

## 13. Decisões resolvidas nesta spec (refinamentos do DR-0001)

- **Cadastro de ativo em campo por INSPECTOR:** **não** na Fase 1 — escrita permanece MANAGER+.
  Revisitar quando houver demanda real de campo (evita ampliar superfície de escrita cedo).
- **Excluir tipo em uso:** **soft delete simples** (`is_active=false`); não bloqueia por
  instâncias existentes. A barreira é V6 (não cria **nova** instância de tipo inativo);
  instâncias e histórico permanecem. Sem aviso de impacto na Fase 1 (pode entrar depois).

---

## 14. Critérios de pronto (Definition of Done da Fase 1)

- Migration aplica e reverte limpo (`alembic upgrade head` / `downgrade`).
- `ruff check backend` e `mypy` sem erros; `python -m pytest` verde (novos testes inclusos).
- Endpoints respeitam envelope/RFC 7807, guards e isolamento por empresa.
- Frontend: `npm run build` (vue-tsc) e `npm test` verdes; telas de CRUD funcionais.
- ADR-0015 atualizada para **Aceita**, citando os pontos do código que a sustentam.
