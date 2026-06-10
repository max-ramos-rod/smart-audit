# Spec Técnica (ESBOÇO) — DR-0002 Fases 2–4 (Inspeção por Componente)

**Status:** Rascunho · **Data:** 2026-06-10
**Origem:** [DR-0002](../design-records/DR-0002-inspecao-por-componente.md) ·
[SPEC Fase 1](SPEC-DR-0002-Fase1-SubmissionAsset.md) ·
[ADR-0006](../adr/0006-modelo-hibrido-de-respostas.md) · [ADR-0008](../adr/0008-score-via-conformities.md)
**Escopo:** as **Fases 2–4** do DR-0002 — repetir campo por componente do ativo. **Toca o core**
(modelo híbrido, ADR-0006). A **Fase 1** (vínculo `submissions.asset_id`) já está implementada.

> ⚠️ **Esboço, não pronto para implementar.** Este documento organiza o trabalho e expõe as
> decisões a ratificar. A principal — o **formato do `answers_json` com componentes** — **revisa o
> ADR-0006** e precisa de uma **nova ADR aprovada antes de codar** (ver §2 e §10). Maior risco de
> regressão do roadmap: a mudança de unicidade no core.

---

## 1. Visão geral

Permitir que um `form_field` (ou seção) seja **repetido por componente** do ativo inspecionado:
ao inspecionar um Veículo com 4 Rodas, "Pressão do pneu" expande em 4 instâncias, cada uma com
resposta, conformidade e evidência próprias (vinculadas ao `asset_id` do componente).

**Estado atual do core (verificado):**
- `submission_values` — `UniqueConstraint("submission_id","form_field_id")` =
  `uq_submission_values_submission_field`; uma resposta por campo.
- `submission_conformities` — `uq_submission_conformities_submission_field`; uma conformidade por
  campo; `CHECK status IN ('conforme','nao_conforme')`; **score deriva daqui** (ADR-0008).
- `form_fields` — `CHECK field_type IN (boolean,text,number,select,date,section)`; sem dimensão de
  componente.
- `submissions.answers_json` — snapshot `{ field_key: valor }`, escrito junto com o relacional em
  `SubmissionService.save_answers` (ADR-0006). Anexos também escrevem no snapshot.

**Mudança central:** introduzir a dimensão **componente** (`asset_id`) em values/conformities e no
snapshot, mantendo `asset_id = NULL` como o comportamento atual (retrocompat).

---

## 2. Decisões a ratificar (antes de implementar)

Originadas das questões abertas do DR-0002. **Q1 é bloqueante** (exige a nova ADR):

- **Q1 — formato do `answers_json` (REVISA ADR-0006).** Recomendado (DR-0002 §5.3-A): **aninhado**
  — campo geral continua escalar; campo escopado vira `{ <asset_id>: valor }`.
  `answers_json = { "placa": "ABC", "pressao_pneu": { "<roda1>": 32, "<roda2>": 30 } }`.
  *Alternativa rejeitada:* chave composta plana (`"pressao_pneu::<roda1>"`).
- **Q2 — campo escopado sem componentes** do tipo no ativo: omitir vs. sinalizar inconsistência.
  *(Proposta de esboço: omitir da execução e exibir aviso não-bloqueante no builder/inspeção.)*
- **Q3 — campo escopado em inspeção sem `asset_id`:** erro de configuração vs. ignorar.
  *(Proposta: bloquear a finalização com mensagem clara; permitir salvar rascunho.)*
- **Q4 — escopo por campo apenas, ou também por seção** (grupo repetível). *(Proposta: começar por
  **campo**; seção repetível como evolução.)*
- **Q5 — declaração do escopo:** coluna `form_fields.component_type_id` (recomendado, integridade)
  vs. `config_json`. *(Proposta: coluna explícita.)*
- **Q6 — peso por componente:** sempre o `weight` do campo (default) vs. peso por componente.
  *(Proposta: peso do campo para todas as instâncias.)*

---

## 3. Modelo de dados (DDL conceitual)

```text
form_fields
  + component_type_id  UUID NULL  FK -> asset_types(id)   -- NULL = campo geral (atual)

submission_values
  + asset_id  UUID NULL  FK -> assets(id)
  UNIQUE(submission_id, form_field_id)  ->  UNIQUE(submission_id, form_field_id, asset_id)
  (uq_submission_values_submission_field  ->  uq_submission_values_submission_field_asset)

submission_conformities
  + asset_id  UUID NULL  FK -> assets(id)
  UNIQUE(submission_id, form_field_id)  ->  UNIQUE(submission_id, form_field_id, asset_id)
  (uq_submission_conformities_submission_field  ->  ..._field_asset)
```

> **Nota Postgres (sensível):** `UNIQUE` trata `NULL` como distinto, então linhas com `asset_id
> NULL` permanecem únicas por `(submission_id, form_field_id)` — o histórico (uma linha por campo)
> continua válido sem ajuste. Validar esse comportamento em teste antes de promover a migração.

---

## 4. Migration Alembic (Fase 2 — aditiva)

- `down_revision = "d2e3f4a5b6c7"` (head da Fase 1).
- `upgrade`: add `form_fields.component_type_id` (FK nullable → asset_types); add
  `submission_values.asset_id` e `submission_conformities.asset_id` (FK nullable → assets);
  **drop** os `UNIQUE` antigos e **create** os novos com `asset_id`; índices auxiliares.
- Histórico fica com `asset_id = NULL` (sem mudança de comportamento). **Reversível.**
- **Sem CASCADE** nos novos FKs de `asset_id` (ativos são soft-deletados; ADR-0009/0015).

---

## 5. Backend

- **Motor de expansão do checklist (Fase 2).** Ao montar a inspeção de um `asset` alvo: campos
  gerais (`component_type_id` nulo) → uma instância (`asset_id = NULL`); campos escopados → uma
  instância por componente do ativo alvo cujo `asset_type_id = component_type_id`
  (`asset_id = <componente>`). Reusa `AssetRepository` (subárvore do alvo).
- **`save_answers` (Fase 2).** Passa a aceitar `asset_id` por resposta; a chave de upsert vira
  `(submission_id, form_field_id, asset_id)`; mantém o snapshot no formato Q1 na mesma operação
  (invariante ADR-0006). Tocar `normalize_value`/`serialize_raw_value`/`extract_value` apenas se o
  formato do snapshot exigir (provável no agrupamento por componente).
- **Score (Fase 3).** `calculate_score`/`calculate_score_breakdown` iteram por **(campo,
  componente)**; cada par booleano avaliado é uma unidade; fórmula ponderada do ADR-0008
  **inalterada** (só muda a cardinalidade). `weight` do `config_json` do campo (Q6).
- **Finalização (Fase 3).** Validação de obrigatórios passa a considerar **cada instância
  expandida** (RN4 do DR): não finaliza com um componente obrigatório pendente.
- **Validação (INV1).** `asset_id` de uma resposta/conformidade deve pertencer à **subárvore** do
  `submissions.asset_id` e ter `asset_type_id = component_type_id` do campo → senão 400 (RFC 7807).

---

## 6. APIs

- `PUT /submissions/{id}/answers` e `PUT /submissions/{id}/conformity` passam a aceitar `asset_id`
  por item (nullable = geral). Envelope `{data,meta}` + RFC 7807 mantidos (ADR-0011).
- `GET /submissions/{id}` retorna respostas/conformidades **agrupadas por componente** para os
  campos escopados (shape a definir junto da decisão Q1).

---

## 7. Frontend (Fase 4)

- **Builder** (`FormFieldEditor.vue`): marcar o **escopo de componente** de um campo (seleção de
  `asset_type`); parte da versão publicada imutável (ADR-0005).
- **Inspeção** (`SubmissionDetailView` + `InspectionListRow`/`InspectionFieldRow`): renderizar
  campos escopados como **grupo por componente** (Roda DD/DE/TD/TE), cada um com resposta +
  conformidade + evidência; reusar o padrão de lista existente.
- **Relatório/PDF**: seções por componente; score breakdown por componente.

---

## 8. Invariantes (do DR-0002 §9)

- **INV1.** `asset_id` da resposta/conformidade ∈ subárvore do `submissions.asset_id`, e do tipo
  `component_type_id` do campo.
- **INV2.** Campo geral (`component_type_id` nulo) ⇒ resposta/conformidade com `asset_id` nulo.
- **INV3.** Snapshot e relacional sempre sincronizados na mesma operação (preserva ADR-0006).
- **INV4.** Score deriva só de `submission_conformities` (ADR-0008), agora por (campo, componente).
- **INV5.** Versões publicadas imutáveis (ADR-0005); `component_type_id` é parte da versão.

---

## 9. Impacto em ADRs

- **ADR-0006 (modelo híbrido) — REVISÃO OBRIGATÓRIA.** Nova ADR documentando o `UNIQUE` com
  `asset_id` e o formato do `answers_json` (Q1). **Pré-requisito do código.**
- **ADR-0008 (score) — extensão leve.** Fórmula igual; cardinalidade por componente. Atualizar o
  texto/nota.
- **ADR-0005 (versionamento) — mantido.** `component_type_id` na versão imutável.
- **ADR-0007 (config_json) — mantido.** Escopo via coluna (Q5), não em `config_json`.

---

## 10. Faseamento e ordem (mapeado ao DR-0002 §12)

1. **Fase 2a — nova ADR (revisão do 0006)**: ratificar Q1 (formato do snapshot) + `UNIQUE`. **Bloqueante.**
2. **Fase 2b — migração aditiva**: `component_type_id` + `asset_id` em values/conformities + novos `UNIQUE` (tudo NULL no histórico). Bateria de **retrocompatibilidade** antes de seguir.
3. **Fase 2c — motor de expansão + `save_answers` com `asset_id`** + snapshot no novo formato.
4. **Fase 3 — score/breakdown por componente + validação de finalização por instância.**
5. **Fase 4 — frontend** (builder marca escopo; inspeção renderiza por componente; relatório/PDF).

> Cada fase ≤ 1 PR quando possível; retrocompatibilidade verificada a cada passo (`asset_id NULL` =
> comportamento atual). Um **PLANO** de tarefas será derivado deste esboço após a ADR de Q1.

---

## 11. Critérios de pronto (da seção 13 do DR-0002)

- **CA1.** Inspeção sem `asset_id` e formulário sem campo escopado: idêntico ao atual (retrocompat).
- **CA2.** Ativo com 4 componentes do tipo X e campo escopado a X ⇒ 4 respostas/conformidades;
  finalizar com uma pendente é bloqueado.
- **CA3.** Score soma cada par campo×componente avaliado (exclui N/A e não avaliados; ADR-0008).
- **CA4.** Snapshot `answers_json` e `submission_values` consistentes para campos escopados.
- **CA5.** Resposta com `asset_id` fora da subárvore/tipo é rejeitada (RFC 7807).
- **CA6.** Migração reversível; nenhuma inspeção histórica alterada.

---

## 12. Riscos (do DR-0002 §11)

- **R-T1 (alto).** Mudança de `UNIQUE` no core → regressão em `save_answers`/score. *Mitigação:*
  migração reversível; `asset_id NULL` preserva o passado; testes de retrocompat antes de tudo.
- **R-T2.** Sincronização do snapshot aninhado (ADR-0006). *Mitigação:* único ponto de escrita
  (`save_answers`); testes que comparam relacional × snapshot.
- **R-T3.** Acoplamento `forms` ↔ `asset_types` (form escopado só serve a ativos com aqueles tipos).
  *Mitigação:* validar compatibilidade ao vincular ativo×formulário.
- **R-N1.** UX de grupos por componente. *Mitigação:* agrupamento visual claro; reusar lista atual.
- **R-O1.** Crescimento de volume de values/conformities. *Mitigação:* índices; monitorar tamanho
  do `answers_json`.

---

## 13. Próximo passo

Antes de qualquer código: **abrir a nova ADR que revisa o ADR-0006** (formato do snapshot +
`UNIQUE` com `asset_id`), ratificando Q1. Aprovada a ADR, derivar o **PLANO-DR-0002-Fases2-4** com
as tarefas das Fases 2–4 acima.
