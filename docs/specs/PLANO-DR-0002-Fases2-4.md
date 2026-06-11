# Plano de Implementação — DR-0002 Fases 2–4 (Inspeção por Componente)

**Status:** Proposta · **Data:** 2026-06-11
**Origem:** [SPEC Fases 2–4](SPEC-DR-0002-Fases2-4-InspecaoPorComponente.md) ·
[DR-0002](../design-records/DR-0002-inspecao-por-componente.md) ·
[ADR-0016](../adr/0016-inspecao-por-componente-revisao-modelo-hibrido.md) ·
[ADR-0006](../adr/0006-modelo-hibrido-de-respostas.md) ·
[ADR-0008](../adr/0008-score-via-conformities.md)

Tarefas pequenas e independentes, cada uma ≤ 1 PR, com critério de aceite, arquivos impactados
e testes. **Escopo: o núcleo do DR-0002 — repetir campo por componente.** **Toca o core**
(modelo híbrido, ADR-0006, revisado pela ADR-0016). Decisões já fechadas na SPEC §2 — este plano
**não** rediscute arquitetura, apenas sequencia a execução.

> **Estado de partida (verificado em 2026-06-11):** Fase 1 (`submissions.asset_id`) implementada;
> Alembic head = `d2e3f4a5b6c7`; ADR-0016 e SPEC Fases 2–4 mergeadas. Modelos atuais **sem**
> dimensão de componente: `submission_values`/`submission_conformities` com
> `UNIQUE(submission_id, form_field_id)`; `form_fields` sem `component_type_id`; `answers_json` =
> `{ field_key: valor }`; não há `submissions.components_snapshot`.
>
> **Fase 2a (revisão do ADR-0006) NÃO é tarefa** — concluída na ADR-0016.

## Princípio condutor

`asset_id NULL` = comportamento atual. Cada tarefa preserva retrocompatibilidade total e é
verificada contra a suíte existente **antes** de avançar. O maior risco do roadmap está em T1
(troca de `UNIQUE` no core) e T4 (`save_answers`) — bateria de retrocompat obrigatória.

## Grafo de dependências

```
T1 (migration + ORM: asset_id, component_type_id, components_snapshot, novos UNIQUE)
 ├─ T2 (forms: declarar component_type_id na versão + validação)
 └─ T3 (motor de expansão do checklist por componente)
      └─ T4 (save_answers com asset_id + answers_json aninhado + components_snapshot)
           ├─ T5 (score/breakdown por componente)
           └─ T6 (validação de finalização por instância)
                └─ T7 (frontend: builder marca escopo)        [dep. T2]
                   T8 (frontend: inspeção por componente)      [dep. T3–T6]
                   T9 (frontend: relatório/PDF por componente) [dep. T4–T5]
T10 (docs: DER/Arquitetura + ADR-0016 → Aceita + DR/SPEC fases concluídas) ← T1–T9
```

| # | Tarefa | Depende | Camada | Fase | Tamanho |
|---|---|---|---|---|---|
| T1 | Migration aditiva + ORM (`asset_id`, `component_type_id`, `components_snapshot`, novos `UNIQUE`) | — | DB | 2b | M |
| T2 | Forms: declarar `component_type_id` na versão publicada + validação cross-context | T1 | Backend | 2c | M |
| T3 | Motor de expansão do checklist por componente | T1 | Backend | 2c | M |
| T4 | `save_answers` com `asset_id` + `answers_json` aninhado + `components_snapshot` | T3 | Backend | 2c | L |
| T5 | Score/breakdown por componente | T4 | Backend | 3 | M |
| T6 | Validação de finalização por instância expandida | T4 | Backend | 3 | S |
| T7 | Frontend: builder marca escopo de componente | T2 | Frontend | 4 | M |
| T8 | Frontend: inspeção renderiza por componente | T3–T6 | Frontend | 4 | L |
| T9 | Frontend: relatório/PDF por componente | T4–T5 | Frontend | 4 | M |
| T10 | Docs: DER/Arquitetura + ADR-0016→Aceita + DR/SPEC concluídas | T1–T9 | Docs | — | S |

---

## T1 — Migration aditiva + ORM

**Objetivo.** Introduzir a dimensão de componente no schema, sem mudar comportamento (tudo `NULL`
no histórico). Implementa a SPEC §3–§4.

**Arquivos impactados**
- `backend/alembic/versions/<rev>_add_component_dimension.py` (novo; `down_revision = "d2e3f4a5b6c7"`)
- `backend/app/db/models/form_fields.py` — `component_type_id: Mapped[str | None]` (FK nullable →
  `asset_types.id`, **sem CASCADE**) + `relationship` opcional
- `backend/app/db/models/submission_values.py` — `asset_id` (FK nullable → `assets.id`, sem
  CASCADE); trocar `uq_submission_values_submission_field` →
  `uq_submission_values_submission_field_asset` em `(submission_id, form_field_id, asset_id)`
- `backend/app/db/models/submission_conformities.py` — idem (`asset_id` + novo `UNIQUE`)
- `backend/app/db/models/submissions.py` — `components_snapshot: Mapped[dict | None]` (JSONB,
  nullable)

**Conteúdo da migration (`upgrade`)**
- `add_column` `form_fields.component_type_id` (FK nullable → `asset_types`).
- `add_column` `submission_values.asset_id`, `submission_conformities.asset_id` (FK nullable →
  `assets`, **sem CASCADE** — ativos são soft-deletados, ADR-0009/0015).
- `add_column` `submissions.components_snapshot` (JSONB nullable).
- `drop_constraint` dos dois `UNIQUE` antigos; `create_unique_constraint` dos novos incluindo
  `asset_id`.
- Índices auxiliares: `ix_submission_values_asset`, `ix_submission_conformities_asset`,
  `ix_form_fields_component_type`.
- `downgrade` reverte na ordem inversa (recria `UNIQUE` antigos, dropa colunas/índices).

**Critérios de aceite**
- `alembic upgrade head` e `downgrade -1` rodam limpos; head novo aponta para esta revisão.
- Postgres: duas linhas com `asset_id NULL` no mesmo `(submission_id, form_field_id)` continuam
  **violando** o `UNIQUE` — graças a **`NULLS NOT DISTINCT`** (PG 15+), que preserva "uma linha por
  campo" no histórico; o padrão `NULLS DISTINCT` perderia essa garantia — **provar em teste**
  (SPEC §3 nota).
- Histórico fica com `asset_id = NULL`, `component_type_id = NULL`, `components_snapshot = NULL`.
- `ruff`/`mypy` verdes; toda a suíte existente verde **sem alteração de teste** (retrocompat
  estrutural).

**Testes necessários**
- Migração up/down limpa.
- Retrocompat: suíte atual de submissions/conformities verde inalterada.
- Unicidade: inserir 2 valores `asset_id NULL` no mesmo campo → `IntegrityError`; inserir 2 com
  `asset_id` distinto no mesmo campo → ok.

---

## T2 — Forms: declarar `component_type_id` na versão publicada

**Objetivo.** Permitir que um `FormField` carregue `component_type_id` ao publicar uma versão, como
parte da versão imutável (ADR-0005). Validar que o tipo referenciado existe na empresa.

**Arquivos impactados**
- `backend/app/modules/forms/schemas.py` — `component_type_id` opcional em `FormFieldCreate` e nas
  responses de campo
- `backend/app/modules/forms/service.py` — em `publish_new_version`: validar
  `component_type_id ∈ asset_types` da empresa (senão 400 RFC 7807); persistir no novo `FormField`
- `backend/app/modules/forms/repository.py` — incluir `component_type_id` na criação de campos;
  `selectinload` se necessário para expor
- `backend/tests/integration/test_forms*.py`

**Critérios de aceite**
- Publicar versão com campo `component_type_id` válido → 200; campo persiste o vínculo e o expõe.
- `component_type_id` de outra empresa ou inexistente → 400 (`"Tipo de componente invalido."`).
- Campo sem `component_type_id` → comportamento atual idêntico.
- `section` **não** aceita `component_type_id` (Q4: escopo por campo) → 400 se enviado.
- `ruff`/`mypy`/`pytest` verdes.

**Testes necessários**
- Publicar com/sem `component_type_id`; cross-company → 400; em `section` → 400; versão anterior
  permanece imutável.

---

## T3 — Motor de expansão do checklist por componente

**Objetivo.** Ao montar a inspeção de um `asset` alvo, expandir os campos escopados em uma instância
por componente do tipo correspondente sob a subárvore do alvo (SPEC §5). Leitura apenas — não grava.

**Arquivos impactados**
- `backend/app/modules/submissions/service.py` — função de montagem do checklist/detalhe: campos
  gerais (`component_type_id` nulo) → uma instância (`asset_id=NULL`); campos escopados → uma
  instância por componente cujo `asset_type_id = component_type_id` na subárvore de
  `submissions.asset_id`
- `backend/app/modules/assets/repository.py` — método de subárvore por tipo (reuso/extensão) se não
  existir; sem lazy load (selectinload)
- `backend/app/modules/submissions/schemas.py` — response de detalhe agrupada por componente para
  campos escopados (`component_id`, `label`/`type`/`path` quando houver `components_snapshot`)
- `backend/tests/integration/test_submissions*.py`

**Regras (SPEC §2)**
- **Q2:** campo escopado sem componentes correspondentes → **omitido** da execução + aviso
  não-bloqueante no payload.
- **Q3:** campo escopado em inspeção **sem** `asset_id` → não expande; sinalizado como erro de
  **configuração** (bloqueia finalização em T6, não a leitura aqui).

**Critérios de aceite**
- Ativo com 4 componentes do tipo X + campo escopado a X → detalhe expõe 4 instâncias do campo,
  cada uma com seu `component_id`/label.
- Campo geral → uma instância, como hoje.
- Sem componentes do tipo → campo omitido + aviso; sem `asset_id` → aviso de configuração.
- Sem lazy load (`MissingGreenlet`); envelope/RFC 7807; `ruff`/`mypy`/`pytest` verdes.

**Testes necessários**
- Expansão 1 campo → N componentes; campo geral inalterado; zero componentes (omite+avisa);
  inspeção sem `asset_id` com campo escopado (aviso).

---

## T4 — `save_answers` com `asset_id` + snapshot aninhado + `components_snapshot`

**Objetivo.** Núcleo da escrita. `save_answers` aceita `asset_id` por resposta/conformidade; chave
de upsert vira `(submission_id, form_field_id, asset_id)`; `answers_json` aninhado com **valores
puros**; `components_snapshot` congela identidade 1× por componente (SPEC §5, Q1/Q1.1).

**Arquivos impactados**
- `backend/app/modules/submissions/schemas.py` — `asset_id` opcional por item em answers/conformity
- `backend/app/modules/submissions/service.py` — `save_answers`/`save_conformities`: upsert por
  `(submission_id, form_field_id, asset_id)`; `answers_json` = campo geral escalar, campo escopado
  `{ <asset_id>: valor }` (valores puros); congelar `components_snapshot[asset_id] =
  { label: asset.identifier, type: asset_type.name, path: <cadeia de ancestrais> }` 1× por
  componente, no mesmo ponto de escrita; validação INV1 (asset na subárvore + tipo bate)
- `backend/app/modules/submissions/repository.py` — upsert/`selectinload` com `asset_id`
- `backend/tests/integration/test_submissions*.py`

**Regras (invariantes SPEC §8)**
- **INV1:** `asset_id` ∈ subárvore de `submissions.asset_id` e `asset_type_id = component_type_id`
  do campo → senão 400 RFC 7807.
- **INV3:** relacional × snapshot escritos na **mesma operação**.
- **INV6:** todo `asset_id` em campo escopado de `answers_json` tem `components_snapshot[asset_id]`;
  congelado uma vez e **nunca reescrito**.

**Critérios de aceite**
- Responder o mesmo campo para 4 componentes → 4 linhas em `submission_values`/`conformities`;
  `answers_json["campo"]` = `{ <asset_id>: valor }`; `components_snapshot` com 4 entradas.
- Resposta com `asset_id` fora da subárvore/tipo → 400.
- Campo geral → escalar em `answers_json`, `asset_id NULL` (idêntico ao atual).
- Relacional e snapshot consistentes (mesma fonte) — teste comparativo.
- `components_snapshot[asset_id]` não muda após renomear o ativo (fidelidade histórica).
- `ruff`/`mypy`/`pytest` verdes.

**Testes necessários**
- Upsert por componente; `answers_json` aninhado; `components_snapshot` 1× por componente e imutável;
  INV1 (fora da árvore/tipo → 400); retrocompat campo geral; consistência relacional×snapshot.

---

## T5 — Score/breakdown por componente

**Objetivo.** `calculate_score`/`calculate_score_breakdown` iteram por **(campo booleano ×
componente)**; fórmula ponderada do ADR-0008 **inalterada**, só muda a cardinalidade (SPEC §5, Q6).

**Arquivos impactados**
- `backend/app/modules/submissions/service.py` — `calculate_score`/`calculate_score_breakdown`
  agregam por par `(form_field_id, asset_id)`; `weight` do `config_json` do campo (igual para todas
  as instâncias); N/A e não avaliados excluídos
- `backend/tests/unit/` (cálculo de score) + `backend/tests/integration/`

**Critérios de aceite**
- Score de inspeção com componentes = `Σ weight(conforme) / Σ weight(avaliado) * 100` sobre todos os
  pares campo×componente (exclui N/A e não avaliados) — consistente com ADR-0008.
- Inspeção sem componentes → score idêntico ao atual (retrocompat).
- Breakdown lista contribuição por componente.
- `ruff`/`mypy`/`pytest` verdes.

**Testes necessários**
- Score com N componentes (mistura conforme/não conforme/N/A); peso por campo aplicado a todas as
  instâncias; retrocompat sem componente; breakdown por componente.

---

## T6 — Validação de finalização por instância expandida

**Objetivo.** Bloquear a finalização se qualquer instância obrigatória (por componente) estiver
pendente — o inspetor não pode esquecer um componente (RN4). Tratar Q3 (campo escopado sem
`asset_id` → erro de configuração na finalização).

**Arquivos impactados**
- `backend/app/modules/submissions/service.py` — validação de finalização considera cada instância
  expandida (de T3); campo escopado em inspeção sem `asset_id` → 400 com mensagem clara
- `backend/tests/integration/test_submissions*.py`

**Critérios de aceite**
- Finalizar com um componente obrigatório pendente → 400 (RFC 7807) listando o que falta.
- Rascunho pode ser salvo incompleto (Q3); só a **finalização** bloqueia.
- Inspeção sem componentes → finalização idêntica ao atual.
- `ruff`/`mypy`/`pytest` verdes.

**Testes necessários**
- 4 componentes, 1 pendente → bloqueia; todos respondidos → finaliza; campo escopado sem `asset_id`
  → erro de configuração; retrocompat sem componente.

---

## T7 — Frontend: builder marca escopo de componente

**Objetivo.** No composer, marcar o `component_type_id` de um campo (seleção de `asset_type`); parte
da versão publicada imutável (ADR-0005).

**Arquivos impactados**
- `frontend/src/components/forms/FormFieldEditor.vue` — seletor opcional de tipo de componente
  (apenas para campos não-`section`)
- `frontend/src/types/forms.ts` — `component_type_id?` em `FormField`/`FormFieldCreatePayload`
- `frontend/src/services/forms.service.ts` — enviar `component_type_id` no publish
- reuso de `assetTypes.service`/store para listar tipos
- Vitest + e2e

**Critérios de aceite**
- Marcar escopo num campo e publicar; o vínculo persiste e reabre corretamente.
- `section` não oferece escopo.
- `http` central; rota sob `/app/`; `npm run build`/`test`/`format:check`/`lint` verdes.

**Testes necessários**
- Vitest: editor emite `component_type_id`; service envia. E2E: marcar escopo + publicar.

---

## T8 — Frontend: inspeção renderiza por componente

**Objetivo.** Renderizar campos escopados como **grupo por componente** (Roda DD/DE/TD/TE), cada um
com resposta + conformidade + evidência próprias, reusando o padrão de lista existente.

**Arquivos impactados**
- `frontend/src/views/submissions/SubmissionDetailView.vue` — agrupar instâncias por componente nos
  três modos (lista normal, card, lista de inspeção)
- `frontend/src/components/submissions/InspectionListRow.vue` e `InspectionFieldRow.vue` — suportar
  instância com `component_id`/label; evidência por componente
- `frontend/src/types/submissions.ts` — instância expandida (`component_id`, `component_label`)
- `frontend/src/services/submissions.service.ts` — enviar `asset_id` por resposta/conformidade
- Vitest + e2e

**Critérios de aceite**
- Ativo com 4 componentes → 4 sub-itens por campo escopado, cada um respondível/avaliável; evidência
  por componente.
- Campo geral inalterado; inspeção sem ativo inalterada.
- Aviso não-bloqueante quando não há componentes (Q2); progresso/score refletem instâncias.
- `build`/`test`/`format:check`/`lint` verdes.

**Testes necessários**
- Vitest: render por componente; envio de `asset_id`. E2E: responder 4 rodas; finalizar bloqueado
  com 1 pendente.

---

## T9 — Frontend: relatório/PDF por componente

**Objetivo.** Relatório e PDF mostram seções por componente e breakdown por componente, lendo a
identidade de `components_snapshot` (sem depender do estado vivo do ativo).

**Arquivos impactados**
- `frontend/src/views/submissions/SubmissionReportView.vue` — agrupar resultados por componente;
  label/path de `components_snapshot`
- backend export PDF (`/submissions/{id}/export`) — seções por componente, score breakdown por
  componente
- Vitest + e2e

**Critérios de aceite**
- Relatório/PDF de inspeção com componentes lista cada componente com suas respostas/conformidade/
  evidência; usa label congelado (imune a renomeação).
- Inspeção sem componentes → relatório idêntico ao atual.
- `build`/`test`/`format:check`/`lint` verdes.

**Testes necessários**
- Vitest: render do relatório por componente. E2E: relatório com 4 componentes.

---

## T10 — Docs

**Objetivo.** Refletir o implementado e fechar o ciclo doc-first.

**Arquivos impactados**
- `docs/DER_Smart_Audit.md` — novas colunas (`asset_id`, `component_type_id`, `components_snapshot`),
  novos `UNIQUE`, migration na lista
- `docs/Arquitetura_Smart_Audit.md` — nota no bounded context de Inspeções (dimensão de componente);
  contagens de teste
- `docs/adr/0016-inspecao-por-componente-revisao-modelo-hibrido.md` — Status **Proposta → Aceita**;
  citar os símbolos do código que a sustentam
- `docs/design-records/DR-0002-inspecao-por-componente.md` e `docs/specs/SPEC-DR-0002-Fases2-4-*.md`
  — marcar Fases 2–4 como **implementadas**
- `docs/design-records/README.md` e `docs/Design_Record_Evolutivo.md` — atualizar status do DR-0002
- `CLAUDE.md` — atualizar a seção de field types / modelo híbrido com a dimensão de componente

**Critérios de aceite**
- DER/Arquitetura refletem o schema final; ADR-0016 "Aceita" com símbolos reais; DR-0002/SPEC com
  fases concluídas; `CLAUDE.md` coerente com o código.

**Testes necessários** — n/a (docs); verificação de consistência docs × código.

---

## Definition of Done (agregado das Fases 2–4)

- **DB (T1):** migração aditiva reversível; novos `UNIQUE` com `asset_id`; `NULL` preserva o
  histórico; suíte existente verde sem alteração.
- **Backend (T2–T6):** escopo declarável e validado; motor de expansão; `save_answers` com
  `asset_id` + `answers_json` aninhado + `components_snapshot` sincronizados; score e finalização por
  componente; INV1–INV6 cobertos por teste.
- **Frontend (T7–T9):** builder marca escopo; inspeção e relatório renderizam por componente lendo o
  snapshot congelado; `build`/`test`/`format:check`/`lint` verdes.
- **Docs (T10):** DER/Arquitetura/ADR-0016/DR/SPEC/CLAUDE.md atualizados.
- **Retrocompatibilidade (CA1/CA6):** inspeções e formulários sem componente idênticos ao atual, e
  nenhuma inspeção histórica alterada — verificado a cada PR.
</content>
</invoke>
