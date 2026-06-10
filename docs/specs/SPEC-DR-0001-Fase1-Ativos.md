# Spec Técnica — DR-0001 Fase 1 (Clients + AssetTypes + Assets)

**Status:** Proposta · **Data:** 2026-06-08 · **Revisão:** r2 (2026-06-08, pós revisão crítica)
**Origem:** [DR-0001](../design-records/DR-0001-ativos-genericos.md) ·
[ADR-0015](../adr/0015-modelo-de-ativos-genericos.md)
**Escopo:** **somente a Fase 1** do DR-0001 — cadastro de `clients` (mínimo), `asset_types`
(sem blueprint automático) e `assets` (árvore, `client_id` nullable). **Fora desta fase:**
`asset_type_components` (Fase 2) e `submissions.asset_id` (Fase 3).

> **Mudanças da revisão r2** (revisão crítica aprovada): **M1** removida a validação de
> `attributes_json` contra `attributes_schema` (coluna mantida, validação adiada); **M2**
> removido `slug` de `asset_types`; **M5** `parent_asset_id` **imutável após o create** (sem
> reparent → sem cycle-check); **B1** removido `GET /assets/{id}/tree`; **M4** soft delete de
> ativo-pai **cascateia** a subárvore (transacional; reativação manual top-down); **M6**
> `client_id` **apenas na raiz** (componentes herdam; garantido por `CHECK`).
> (M3 não aprovado: `assets.status` permanece enum.)

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

Índices: `INDEX ix_clients_company_id (company_id)`.

### 2.2 `asset_types`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → `companies.id` ON DELETE CASCADE | NOT NULL |
| `name` | VARCHAR(150) | NOT NULL |
| `description` | TEXT | NULL |
| `attributes_schema` | JSONB | **NULL** (opcional, Q5). **r2:** coluna mantida; **a validação de `attributes_json` contra este schema NÃO faz parte da Fase 1** (M1) — fica reservada para fase posterior. |
| `is_active` | BOOLEAN | NOT NULL, `server_default 'true'` (soft delete) |
| `created_at`/`updated_at` | TIMESTAMPTZ | |

Índices: `INDEX ix_asset_types_company_id (company_id)`.
**r2 (M2):** sem `slug` e sem `UNIQUE(company_id, slug)` nesta fase. (Reintroduzir quando algo
referenciar tipo por chave estável — ex.: blueprint da Fase 2.)

### 2.3 `assets`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | UUID PK | |
| `company_id` | UUID FK → `companies.id` ON DELETE CASCADE | NOT NULL |
| `asset_type_id` | UUID FK → `asset_types.id` | NOT NULL |
| `parent_asset_id` | UUID FK → `assets.id` ON DELETE CASCADE | **NULL** = raiz; preenchido = componente. **Imutável após o create (M5).** |
| `client_id` | UUID FK → `clients.id` | **NULL** = patrimônio próprio; preenchido = ativo de cliente. **Só permitido em raiz (M6).** |
| `identifier` | VARCHAR(180) | NOT NULL — "Placa ABC-1234", "Roda DD" |
| `attributes_json` | JSONB | NOT NULL, `server_default '{}'::jsonb` |
| `status` | VARCHAR(20) | NOT NULL, `server_default 'active'`, `CHECK status IN ('active','inactive','retired')` |
| `created_at`/`updated_at` | TIMESTAMPTZ | |

Constraints:
- `CHECK (parent_asset_id IS NULL OR client_id IS NULL)` (`ck_assets_client_only_on_root`) —
  **M6**: um componente (com pai) não pode ter `client_id`; o cliente é derivado da raiz.
- `CHECK status IN ('active','inactive','retired')` (`ck_assets_status`).

Índices: `ix_assets_company_parent (company_id, parent_asset_id)`,
`ix_assets_company_type (company_id, asset_type_id)`,
`ix_assets_company_client (company_id, client_id)`.

> **Integridade que a FK NÃO garante** (validar no service): `asset_type_id`, `parent_asset_id`
> e `client_id` devem pertencer à **mesma** `company_id`. Ver §6.
> O `ON DELETE CASCADE` em `parent_asset_id` é **dormente** (hard delete é proibido — §7 V5); a
> remoção de subárvore acontece por **soft delete em cascata** (M4), não por delete físico.

---

## 3. Migration Alembic

- **Uma** revisão criando as três tabelas **na ordem de dependência**: `clients` → `asset_types`
  → `assets` (assets referencia ambas + a si mesma).
- `down_revision = "b0c1d2e3f4a5"` (head atual = `create_audit_logs`).
- Escrita **à mão** (sem autogenerate), `id` listado primeiro em cada `create_table`. `downgrade`
  faz `drop_table` na ordem inversa (`assets` → `asset_types` → `clients`).
- Declarar na criação: os dois `CHECK` de `assets` e os índices. (Sem `UNIQUE` de slug — r2.)
- Requer `gen_random_uuid()` (já assumido no projeto).

Sugestão de nome: `c1d2e3f4a5b6_add_assets_clients_asset_types.py`.

---

## 4. Modelos ORM (`backend/app/db/models/`)

Padrão idêntico ao `teams.py`: herdar `(UUIDPrimaryKeyMixin, TimestampMixin, Base)`,
`__tablename__`, `__table_args__` com `Index`/`CheckConstraint`, FKs com `ondelete`,
`relationship` com `back_populates`.

- `Client` (`clients`) — `company = relationship("Company", back_populates="clients")`.
- `AssetType` (`asset_types`) — `company = relationship(...)`;
  `assets = relationship("Asset", back_populates="asset_type")`. **Sem `slug`.**
- `Asset` (`assets`):
  - `asset_type = relationship("AssetType", back_populates="assets")`
  - `client = relationship("Client")`
  - **árvore:** `parent = relationship("Asset", remote_side=[id], back_populates="components")`;
    `components = relationship("Asset", back_populates="parent")`
    *(sem `cascade="all, delete-orphan"` — não há delete físico; a desativação em cascata é
    lógica, feita no service — M4)*.
- Registrar os três em `app/db/models/__init__.py`. `Company` ganha `back_populates` para
  `clients`.

> Regra async (ADR-0002): nada de lazy load. Usar `selectinload` onde a árvore/relacionamentos
> forem acessados após a query (`selectinload(Asset.components)`, `selectinload(Asset.asset_type)`).

---

## 5. Schemas Pydantic (`schemas.py` por módulo)

Todo campo `str` de request com `Field(min_length=…, max_length=…)`. Serialização com
`model_dump(mode="json")`.

### Clients
```
ClientCreateRequest:    name: Field(2,150)
ClientUpdateRequest:    name?: Field(2,150); is_active?: bool
ClientResponse:         id; name; is_active
```

### AssetTypes  (sem slug — r2)
```
AssetTypeCreateRequest: name: Field(2,150); description?: Field(max=2000);
                        attributes_schema?: dict
AssetTypeUpdateRequest: name?; description?; attributes_schema?; is_active?
AssetTypeResponse:      id; name; description; attributes_schema; is_active
```

### Assets  (parent só no create; client_id só em raiz — M5/M6)
```
AssetCreateRequest: asset_type_id: Field(1,36); identifier: Field(2,180);
                    parent_asset_id?: Field(1,36); client_id?: Field(1,36);
                    attributes_json?: dict
AssetUpdateRequest: identifier?: Field(2,180); client_id?: Field(1,36);
                    attributes_json?; status?: Field(1,20)
                    # NÃO inclui parent_asset_id — imutável após o create (M5)
AssetResponse:      id; asset_type_id; identifier; parent_asset_id; client_id;
                    attributes_json; status
AssetDetailResponse(AssetResponse): components: list[AssetResponse]   # filhos diretos
```

`status` validado por `field_validator` contra `{active, inactive, retired}`.

---

## 6. Repositórios (`repository.py`) — flush, sem commit

Cada um estende `SQLAlchemyRepository[Model]` e expõe **métodos nomeados**. Reads filtram por
`company_id` e usam `populate_existing` (base).

- **ClientRepository:** `list_by_company(db, company_id, params, is_active?)`,
  `get_company_client(...)`, `create_client(...)`.
- **AssetTypeRepository:** `list_by_company(...)`, `get_company_type(...)`, `create_asset_type(...)`.
  *(sem `get_by_slug` — r2.)*
- **AssetRepository:** `list_by_company(db, company_id, params, filters)` (filtros:
  `asset_type_id`, `client_id`, `parent_asset_id`, `status`), `get_company_asset(...)` (com
  `selectinload(components, asset_type, client)`), `list_children(db, parent_id)`,
  `create_asset(...)`, **`deactivate_subtree(db, root_asset_id)`** (M4 — `UPDATE` recursivo
  via CTE marcando `status='inactive'` no nó e em todos os descendentes, na mesma transação).
  *(sem `is_descendant` — não há mais cycle-check, M5.)*

---

## 7. Serviços (`service.py`) — regras de negócio + commit

### Validações (invariantes do ADR-0015 / CA do DR-0001, revisadas r2)

- **V1 (isolamento).** Ao criar/editar `Asset`: `asset_type_id`, `parent_asset_id` e `client_id`
  (quando informados) devem existir e pertencer à `membership.company_id`. Senão → 400/404.
- **V2 (parent imutável — M5).** `parent_asset_id` é definido **apenas no create**. `PATCH` que
  tente alterá-lo → 400. (Sem reparent ⇒ sem possibilidade de ciclo ⇒ sem cycle-check.)
- **V3 (client só na raiz — M6).** `client_id` só é aceito quando `parent_asset_id` é nulo
  (ativo raiz). Tentar definir `client_id` num componente → 400 (reforçado pelo `CHECK` do banco).
  O cliente efetivo de um componente é **derivado** da raiz.
- **V4 (atributos livres — M1).** `attributes_json` é aceito **livre** na Fase 1; **não há
  validação contra `attributes_schema`** (coluna existe, mas o validador é de fase posterior).
- **V5 (soft delete).** `DELETE /clients/{id}` e `/asset-types/{id}` ⇒ `is_active=false`. Nunca
  remover fisicamente (ADR-0009).
- **V6 (soft delete de árvore — M4).** `DELETE /assets/{id}` ⇒ desativa o ativo **e toda a
  subárvore** (`deactivate_subtree`), de forma **transacional** (`status='inactive'`).
  **Invariante:** não pode existir ativo `active` cujo ancestral esteja `inactive`.
- **V7 (reativação top-down — M4).** `PATCH status='active'` só é permitido se o `parent_asset_id`
  for nulo **ou** o pai estiver `active`; reativar **não** cascateia para os filhos (preserva o
  estado prévio de cada componente). Reativar um nó com pai inativo → 400.
- **V8 (tipo ativo).** Criar `Asset` exige `AssetType.is_active=true`.
- **V9 (cliente ativo).** `client_id`, se informado, deve referenciar `Client.is_active=true`.

Cada método de escrita valida, chama o método nomeado do repositório (flush), registra auditoria
(§9) e dá `await db.commit()` ao final.

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
| POST | `/asset-types` | manager | Cria |
| PATCH | `/asset-types/{id}` | manager | Atualiza |
| DELETE | `/asset-types/{id}` | manager | Soft delete (`is_active=false`) |

### Assets — `/api/v1/assets`
| Método | Rota | Guard | Descrição |
|---|---|---|---|
| GET | `/assets?page&page_size&asset_type_id&client_id&parent_asset_id&status` | current | Lista filtrada |
| GET | `/assets/{id}` | current | Detalhe + filhos diretos (`components`) |
| POST | `/assets` | manager | Cria raiz ou componente (V1,V3,V8,V9; `parent_asset_id` só aqui) |
| PATCH | `/assets/{id}` | manager | Atualiza (sem `parent_asset_id`; reativação segue V7) |
| DELETE | `/assets/{id}` | manager | Soft delete em cascata da subárvore (V6) |

**r2 (B1):** sem `GET /assets/{id}/tree` nesta fase (basta o detalhe com filhos diretos).

---

## 9. Auditoria

Eventos em `audit_logs` (padrão existente), antes do commit: `client.created`,
`asset_type.created`, `asset.created` (mínimo); opcionalmente `*.updated`/`*.deactivated`.
A desativação em cascata (V6) registra o evento na raiz com `meta` contendo a contagem de
descendentes afetados.

---

## 10. Frontend (resumo — detalhe em spec de UI)

- `types/`: `Client`, `AssetType`, `Asset` (+ payloads). `AssetType` **sem slug**.
- `services/`: `clients.service.ts`, `asset-types.service.ts`, `assets.service.ts` (via `http`).
- `stores/`: store por domínio (Pinia).
- `views/`: `clients/`, `asset-types/` (editor opcional de `attributes_schema` como JSON livre —
  sem validação nesta fase), `assets/` (cadastro raiz/componente, visualização de filhos diretos,
  filtro por tipo/cliente/status). `parent` definido só na criação. Base `/app/`.

---

## 11. Testes (`backend/tests/integration/`)

Convenção: savepoint isolation, fixtures `auth_headers` (MANAGER+) e `inspector_headers` (403),
`python -m pytest`. Casos mínimos (mapeados aos CA do DR-0001, revisados r2):

- **Clients/AssetTypes:** CRUD; soft delete some da listagem ativa; escrita por INSPECTOR → 403;
  isolamento multiempresa (CA6).
- **Assets — criação/árvore:** criar raiz e componente (profundidade ≥2) → CA2; dois domínios
  sem schema novo → CA1; `attributes_json` aceito livre (M1, sem validação).
- **Assets — cliente (M6):** criar raiz com/sem `client_id` e listar por cliente → CA4;
  `client_id` de outra empresa → rejeitado (CA4/V1); definir `client_id` em **componente** →
  400 (V3 + `CHECK`).
- **Assets — parent imutável (M5):** `PATCH` alterando `parent_asset_id` → 400 (V2).
- **Assets — soft delete de árvore (M4):** desativar raiz desativa toda a subárvore
  transacionalmente (V6); não há filho `active` sob pai `inactive`. Reativar componente com pai
  inativo → 400; reativar não cascateia (V7).
- **Tipo arquivado** bloqueia nova instância (V8); cliente inativo recusado (V9).

---

## 12. Fora desta fase (referência)

- **`asset_type_components` (blueprint) + expansão automática** → Fase 2. *(O `slug` removido em
  r2 pode voltar aqui, se o blueprint referenciar tipo por chave estável.)*
- **Validação de `attributes_json` contra `attributes_schema`** → fase posterior (M1).
- **`submissions.asset_id` (vínculo inspeção→ativo)** → Fase 3 (destrava DR-0002).
- **Reparent (mudar `parent_asset_id`) + cycle-check** → quando houver demanda (M5).
- **Atributos ricos de `Client` (CNPJ, contato)** → DR-0005.
- **Inspeção por componente** (asset_id em values/conformities) → DR-0002 (toca ADR-0006).

---

## 13. Decisões consolidadas (revisão r2)

- **M1.** `attributes_schema` mantido na modelagem; **validação fora da Fase 1** — atributos
  livres.
- **M2.** `slug` **removido** de `asset_types` na Fase 1.
- **M4.** Soft delete de ativo-pai **cascateia** a subárvore (transacional, V6); **reativação
  não cascateia** e é top-down (V7); invariante "sem filho ativo sob pai inativo".
- **M5.** `parent_asset_id` **imutável após o create**; sem reparent ⇒ sem cycle-check.
- **M6.** `client_id` **só na raiz**, garantido por `CHECK (parent_asset_id IS NULL OR client_id
  IS NULL)`; cliente do componente é derivado da raiz.
- **B1.** `GET /assets/{id}/tree` removido da Fase 1.
- **M3 (não aprovado):** `assets.status` permanece enum (`active/inactive/retired`).

---

## 14. Critérios de pronto (Definition of Done da Fase 1)

- Migration aplica e reverte limpo (`alembic upgrade head` / `downgrade`).
- `ruff check backend` e `mypy` sem erros; `python -m pytest` verde (novos testes inclusos).
- Endpoints respeitam envelope/RFC 7807, guards e isolamento por empresa.
- Soft delete de árvore (V6) e reativação top-down (V7) cobertos por teste.
- Frontend: `npm run build` (vue-tsc) e `npm test` verdes; telas de CRUD funcionais.
- ADR-0015 atualizada para **Aceita**, citando os pontos do código que a sustentam.
