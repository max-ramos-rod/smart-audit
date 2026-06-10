# Plano de Implementação — DR-0002 Fase 1 (vínculo `submissions.asset_id`)

**Status:** Proposta · **Data:** 2026-06-10
**Origem:** [SPEC](SPEC-DR-0002-Fase1-SubmissionAsset.md) ·
[DR-0002](../design-records/DR-0002-inspecao-por-componente.md) ·
[ADR-0015](../adr/0015-modelo-de-ativos-genericos.md)

Tarefas pequenas e independentes, cada uma ≤ 1 PR, com critério de aceite, arquivos impactados
e testes. **Escopo: apenas o vínculo aditivo inspeção→ativo.** Não toca o core (ADR-0006).

## Grafo de dependências

```
T1 (migration + modelo asset_id)
 └─ T2 (backend: schema + service + repo + endpoints) ─ T3 (frontend)
T4 (docs: DER/Arquitetura + DR-0002 Fase 1 registrada)  ← depende de T1–T2
```

| # | Tarefa | Depende | Camada | Tamanho |
|---|---|---|---|---|
| T1 | Migration + coluna `submissions.asset_id` + ORM | — | DB | S |
| T2 | Backend: create aceita/valida `asset_id`, expõe e filtra | T1 | Backend | M |
| T3 | Frontend: seleção de ativo na criação + exibição no detalhe/relatório | T2 | Frontend | M |
| T4 | Docs: DER + Arquitetura + DR-0002 (Fase 1 → implementada) | T1–T2 | Docs | S |

---

## T1 — Migration + coluna `submissions.asset_id` + ORM

**Objetivo.** Adicionar a coluna aditiva e mapeá-la no ORM. Sem rota nem lógica nova.

**Arquivos impactados**
- `backend/alembic/versions/<rev>_add_submissions_asset_id.py` (novo; `down_revision = "c1d2e3f4a5b6"`)
- `backend/app/db/models/submissions.py` (coluna `asset_id`, `relationship` `asset`, índice
  `ix_submissions_company_asset`)

**Critérios de aceite**
- `alembic upgrade head` e `downgrade -1` rodam limpos; coluna `asset_id UUID NULL FK → assets(id)`
  (sem CASCADE); índice criado.
- Modelo importa; `ruff`/`mypy` verdes; inspeções existentes ficam com `asset_id = NULL`.

**Testes necessários**
- Mínimo: suíte existente continua verde após a migração (retrocompat estrutural).

---

## T2 — Backend: `asset_id` no create, exposição e filtro

**Objetivo.** `POST /submissions` aceita `asset_id` opcional e o valida (V1 isolamento, V2 ativo
ativo); detalhe e lista expõem `asset_id`/`asset_identifier`; lista filtra por `asset_id`.

**Arquivos impactados**
- `backend/app/modules/submissions/schemas.py` (`asset_id` em create; `asset_id`/
  `asset_identifier` nas responses)
- `backend/app/modules/submissions/service.py` (validação no `create_submission`; serialização)
- `backend/app/modules/submissions/repository.py` (`selectinload(asset)`; filtro `asset_id`)
- `backend/app/api/v1/routers/submissions.py` (query param `asset_id` no `GET`)
- `backend/tests/integration/test_submissions*.py`

**Critérios de aceite**
- Criar sem `asset_id` → 200 idêntico ao atual; com `asset_id` válido → 200 e vínculo exposto.
- `asset_id` de outra empresa → 400 (`"Ativo invalido."`); ativo inativo → 400
  (`"Ativo nao esta ativo."`).
- `GET /submissions?asset_id=` retorna só as daquele ativo; envelope/RFC 7807; sem lazy load.
- `ruff`/`mypy`/`pytest` verdes.

**Testes necessários**
- Criar sem/with `asset_id`; foreign → 400; inativo → 400; filtro por `asset_id`; detalhe e item
  de lista trazem `asset_identifier`.

---

## T3 — Frontend: seleção de ativo + exibição

**Objetivo.** Escolher um ativo (opcional) ao criar inspeção e mostrar o vínculo no detalhe e no
relatório. Sem ativo = comportamento atual.

**Arquivos impactados**
- `frontend/src/types/submissions.ts` (campos `asset_id`/`asset_identifier`)
- `frontend/src/services/submissions.service.ts` (enviar `asset_id` no create; filtro opcional)
- store/views de submissions (seletor de ativo na criação; exibir ativo no detalhe e no relatório)
- reuso de `assets.service`/store (T8) para listar ativos ativos
- Vitest (store/service) + e2e

**Critérios de aceite**
- Criar inspeção com e sem ativo; ativo aparece no detalhe e no relatório (link para `/assets`).
- `http` central; rota sob `/app/`; `npm run build`/`npm test`/`format:check` verdes.

**Testes necessários**
- Vitest: service envia `asset_id`; store repassa. E2E: criar com ativo selecionado; detalhe
  mostra o ativo.

---

## T4 — Docs

**Objetivo.** Refletir o vínculo no DER e na Arquitetura e marcar a Fase 1 do DR-0002 como
implementada.

**Arquivos impactados**
- `docs/DER_Smart_Audit.md` (coluna `submissions.asset_id` + relacionamento `assets 1:N
  submissions`; migration na lista; Mermaid/DER textual)
- `docs/Arquitetura_Smart_Audit.md` (nota no bounded context de Inspeções/Ativos; contagens de
  teste atualizadas)
- `docs/design-records/DR-0002-inspecao-por-componente.md` (nota: Fase 1 — vínculo — implementada;
  Fases 2–4 pendentes) e `docs/design-records/README.md` se necessário

**Critérios de aceite**
- DER e Arquitetura refletem o implementado; DR-0002 indica claramente o que já existe (vínculo)
  vs. o que falta (dimensão de componente, revisão do ADR-0006).

**Testes necessários** — n/a (documentação); verificação de consistência docs × código.

---

## Definition of Done da Fase 1 (agregado)

- T1–T2: backend aditivo; migração reversível; `asset_id` validado, exposto e filtrável;
  retrocompatibilidade total; `ruff`/`mypy`/`pytest` verdes.
- T3: frontend permite vincular ativo e exibe o vínculo; `build`/`test`/`format:check` verdes.
- T4: DER/Arquitetura atualizados; DR-0002 com a Fase 1 marcada como implementada.
- **Núcleo (ADR-0006) intocado** — a inspeção por componente permanece nas Fases 2–4.
