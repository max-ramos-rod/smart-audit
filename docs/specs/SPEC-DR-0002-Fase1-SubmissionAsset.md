# Spec Técnica — DR-0002 Fase 1 (vínculo `submissions.asset_id`)

**Status:** Proposta · **Data:** 2026-06-10
**Origem:** [DR-0002](../design-records/DR-0002-inspecao-por-componente.md) ·
[DR-0001](../design-records/DR-0001-ativos-genericos.md) ·
[ADR-0015](../adr/0015-modelo-de-ativos-genericos.md)
**Escopo:** **somente a Fase 1** do DR-0002 — o **vínculo da inspeção ao ativo**
(`submissions.asset_id`), aditivo e retrocompatível. **Fora desta fase:** a dimensão de
componente nas respostas/conformidades, `form_fields.component_type_id`, mudança de unicidade
de `submission_values`/`submission_conformities`, e o novo formato de `answers_json` — tudo isso
é o núcleo do DR-0002 (Fases 2–4) e **revisa o ADR-0006**; **esta spec não toca o core.**

> **Por que esta fase existe.** O DR-0002 (seção 2) assume que `submissions.asset_id` já existe,
> mas a [SPEC do DR-0001](SPEC-DR-0001-Fase1-Ativos.md) o **adiou** explicitamente (era "Fase
> 3"). Este é o degrau aditivo e seguro que **destrava** o DR-0002 sem mexer no modelo híbrido
> (ADR-0006): liga cada inspeção a um ativo, sem ainda repetir campo por componente.

---

## 1. Visão geral

Uma única tabela alterada (`submissions`), de forma **puramente aditiva**: nova coluna
`asset_id` (FK nullable → `assets`). Nenhuma mudança de unicidade, de `answers_json`, de score,
nem de `submission_values`/`submission_conformities`. `asset_id = NULL` ⇒ comportamento atual
idêntico (retrocompatibilidade total).

Regras transversais (ADRs): isolamento por `company_id` (ADR-0003); escrita de inspeção segue o
guard atual do endpoint (sem mudança de papel); commit no service, flush no repository
(ADR-0001); envelope `{data, meta}` + RFC 7807 (ADR-0011); schemas de request com
`Field(min_length/max_length)`.

---

## 2. Modelo de dados (DDL conceitual)

```text
submissions
  + asset_id  UUID NULL  REFERENCES assets(id)   -- NULL = inspeção sem ativo (comportamento atual)
  índice: ix_submissions_company_asset (company_id, asset_id)
```

- **Sem `ON DELETE CASCADE`.** Ativos são soft-deletados (`status`), nunca removidos
  fisicamente (ADR-0009/ADR-0015); a FK não precisa cascatear. Desativar um ativo **não** apaga
  nem altera inspeções históricas — o vínculo permanece para leitura.
- **Nullable e sem default.** Inspeções existentes ficam com `asset_id = NULL`.

---

## 3. Migration Alembic

- Arquivo novo: `<rev>_add_submissions_asset_id.py`, `down_revision = "c1d2e3f4a5b6"`
  (rev sugerida: `d2e3f4a5b6c7`).
- `upgrade`: `op.add_column("submissions", Column("asset_id", UUID, ForeignKey("assets.id"),
  nullable=True))` + `op.create_index("ix_submissions_company_asset", "submissions",
  ["company_id", "asset_id"])`.
- `downgrade`: drop do índice + drop da coluna. **Reversível**; nenhuma linha histórica tocada.

---

## 4. Modelo ORM

`backend/app/db/models/submissions.py` — em `Submission`:

- `asset_id: Mapped[str | None] = mapped_column(ForeignKey("assets.id"), nullable=True)`
- `asset = relationship("Asset")` (carregar com `selectinload` onde o detalhe for serializado —
  regra async ADR-0002, sem lazy load).
- novo `Index("ix_submissions_company_asset", "company_id", "asset_id")` em `__table_args__`.

---

## 5. Schemas Pydantic (`submissions/schemas.py`)

- **`SubmissionCreateRequest`** + `asset_id: str | None = Field(default=None, min_length=1,
  max_length=36)`. Opcional — ausência preserva o comportamento atual.
- **`SubmissionResponse`** + `asset_id: str | None` e `asset_identifier: str | None`
  (conveniência de leitura, resolvido de `submission.asset.identifier`).
- **`SubmissionListItemResponse`** + `asset_id: str | None` e `asset_identifier: str | None`
  (para exibir/filtrar na listagem).

---

## 6. Serviço (`submissions/service.py`) — regras + commit

- **`create_submission`** passa a receber `payload.asset_id`:
  - **V1 (isolamento).** Se `asset_id` informado, validar via
    `AssetRepository.get_company_asset(db, asset_id, company_id)`; inexistente/de outra empresa →
    **400** (`"Ativo invalido."`).
  - **V2 (ativo elegível).** Ativo com `status != 'active'` → **400** (`"Ativo nao esta
    ativo."`). Não se inicia inspeção nova sobre ativo desativado/baixado; inspeções históricas
    preservam o vínculo.
  - Persistir `asset_id` no `Submission`.
- **`serialize_submission`** inclui `asset_id` e `asset_identifier` (de `submission.asset`).
- `asset_id` é definido **apenas na criação** nesta fase (não há PATCH de metadados de inspeção);
  editar o vínculo fica fora de escopo.

---

## 7. Repositório (`submissions/repository.py`)

- `get_submission` / `get_submissions` (listagem): adicionar `selectinload(Submission.asset)` para
  o detalhe e a lista carregarem o identificador sem lazy load.
- Listagem aceita filtro opcional `asset_id` (`WHERE asset_id = :asset_id`), análogo aos filtros
  já existentes.

---

## 8. Endpoints REST (`/api/v1/submissions`)

- **`POST /submissions`** — body aceita `asset_id` opcional (validado no service). Envelope e
  RFC 7807 mantidos.
- **`GET /submissions?asset_id=`** — filtro opcional por ativo (além dos filtros atuais). Itens
  trazem `asset_id`/`asset_identifier`.
- **`GET /submissions/{id}`** — resposta inclui `asset_id`/`asset_identifier`.
- Sem novos guards: as permissões de inspeção permanecem as atuais.

---

## 9. Frontend (resumo)

- **Criar inspeção:** seletor de **ativo opcional** (lista ativos ativos via
  `assets.service`/store; reuso do T8). Vazio = inspeção sem ativo (comportamento atual).
- **Detalhe e relatório da inspeção:** exibir o ativo vinculado (`asset_identifier`), como link
  para `/assets` quando houver.
- **Listagem de inspeções:** opcional — filtro/coluna por ativo.
- **`AssetsView`:** opcional — atalho "ver inspeções deste ativo" (link para
  `/submissions?asset_id=`). Pode ficar para uma iteração seguinte se aumentar o escopo.
- `http` central; rotas sob `/app/`; `npm run build`/`npm test`/`format:check` verdes.

---

## 10. Impacto em ADRs

- **Nenhuma revisão de core nesta fase.** O `submissions.asset_id` é aditivo e já era
  **antecipado** pelo ADR-0015 ("o `submissions.asset_id` é a fronteira que destrava o DR-0002").
- A **revisão do ADR-0006** (unicidade + formato de `answers_json`) e a nova ADR "Inspeção por
  componente" pertencem às **Fases 2–4** do DR-0002 — fora desta spec.

---

## 11. Testes (`backend/tests/integration/`)

- `test_submissions.py` (ou arquivo dedicado):
  - criar inspeção **sem** `asset_id` → 200, comportamento idêntico ao atual (retrocompat).
  - criar **com** `asset_id` válido → 200; detalhe e item de lista trazem `asset_id`/
    `asset_identifier`.
  - `asset_id` de outra empresa → 400 (`"Ativo invalido."`) (V1).
  - `asset_id` de ativo inativo → 400 (`"Ativo nao esta ativo."`) (V2).
  - `GET /submissions?asset_id=` retorna só as inspeções daquele ativo.
- Migração: `alembic upgrade head` + `downgrade -1` limpos; inspeções históricas com
  `asset_id = NULL` intactas.

---

## 12. Fora desta fase (referência — Fases 2–4 do DR-0002)

- `form_fields.component_type_id` (escopo de componente no campo).
- `asset_id` em `submission_values`/`submission_conformities` + novo
  `UNIQUE(submission_id, form_field_id, asset_id)`.
- Motor de expansão do checklist por componente; `save_answers` com `asset_id`.
- Novo formato de `answers_json` (mapa por componente) — **revisa o ADR-0006** (Q1 do DR-0002).
- Score/breakdown por componente; validação de finalização por instância.

---

## 13. Critérios de pronto (Definition of Done)

- Migração aditiva e **reversível**; nenhuma inspeção histórica alterada (`asset_id = NULL`).
- `POST /submissions` aceita `asset_id` opcional, validado (V1/V2); `GET` (detalhe e lista)
  expõe `asset_id`/`asset_identifier`; lista filtra por `asset_id`.
- Retrocompatibilidade: inspeção sem `asset_id` funciona idêntico ao atual.
- `ruff`/`mypy`/`pytest` verdes (backend); `build`/`test`/`format:check` verdes (frontend).
- Núcleo (ADR-0006) **intocado**.
