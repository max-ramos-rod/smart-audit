# Spec Técnica — DR-0002 Fases 2–4 (Inspeção por Componente)

**Status:** Decidida (pronta para derivar PLANO) · **Data:** 2026-06-10
**Origem:** [DR-0002](../design-records/DR-0002-inspecao-por-componente.md) ·
[SPEC Fase 1](SPEC-DR-0002-Fase1-SubmissionAsset.md) ·
[ADR-0006](../adr/0006-modelo-hibrido-de-respostas.md) ·
[ADR-0008](../adr/0008-score-via-conformities.md) ·
[ADR-0016](../adr/0016-inspecao-por-componente-revisao-modelo-hibrido.md)
**Escopo:** as **Fases 2–4** do DR-0002 — repetir campo por componente do ativo. **Toca o core**
(modelo híbrido, ADR-0006). A **Fase 1** (vínculo `submissions.asset_id`) já está implementada.

> ✅ **Discussão arquitetural encerrada (2026-06-10).** Todas as decisões estão fechadas (§2) e
> refletidas na **ADR-0016**. Próximo passo material: derivar o **PLANO-DR-0002-Fases2-4** e
> implementar. Maior risco de regressão do roadmap: a mudança de unicidade no core
> (`UNIQUE(submission_id, form_field_id, asset_id)`) — exige bateria de retrocompatibilidade.

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

## 2. Decisões (todas DECIDIDAS — 2026-06-10)

A discussão arquitetural foi encerrada. As questões do DR-0002 §14 estão **decididas** abaixo e
refletidas na ADR-0016; o catálogo fino fica em [`docs/ai/AI_DECISIONS.md`](../ai/AI_DECISIONS.md).

- **Q1 — formato do `answers_json`. DECIDIDO:** **aninhado** — campo geral escalar; campo escopado
  = mapa por componente `{ <asset_id>: valor }`. *Descartado:* chave composta plana
  (`"pressao_pneu::<roda1>"`); snapshot só geral. (Revisa o ADR-0006 — ADR-0016.)
- **Q1.1 — chave do mapa e onde mora a identidade. DECIDIDO (Alternativa C):** chave = **`asset_id`
  (UUID)**; `answers_json` carrega **valores puros**; a identidade congelada vai para a **coluna
  dedicada `submissions.components_snapshot`** = `{ <asset_id>: { label, type, path } }`, **1× por
  componente**, gravada no `save_answers`. *Descartado:* identidade por campo (Alt. A — duplica
  label × campos), mapa-irmão no `answers_json` (Alt. B — mistura/colisão de chave), `identifier`
  como chave (mutável/não-único).
- **Q1.2 — semântica de `NULL` na unicidade. DECIDIDO (2026-06-11, IMPLEMENTADO):** a unicidade
  `(submission_id, form_field_id, asset_id)` usa **`NULLS NOT DISTINCT`** (PG 15+). Trata `NULL`
  como igual: preserva a garantia histórica de **uma** resposta por campo geral (`asset_id NULL`),
  mantém a retrocompat do modelo anterior e permite **múltiplas** respostas por componente quando
  `asset_id` está preenchido. *Descartado:* `NULLS DISTINCT` (padrão — permitiria vários `NULL` no
  mesmo campo, regressão) e índice único parcial `WHERE asset_id IS NULL` (alternativa para PG < 15,
  desnecessária: prod PG 17, dev PG 18). Implementado na T1 (migration `e3f4a5b6c7d8`).
- **Q2 — campo escopado sem componentes. DECIDIDO:** **omitir** da execução + **aviso
  não-bloqueante** (builder/inspeção). *Descartado:* erro bloqueante (impediria inspeção legítima).
- **Q3 — campo escopado em inspeção sem `asset_id`. DECIDIDO:** **erro de configuração** — bloquear
  a **finalização** com mensagem clara; rascunho pode ser salvo. *Descartado:* ignorar
  silenciosamente.
- **Q4 — granularidade do escopo. DECIDIDO:** **por campo** nas Fases 2–4; seção repetível =
  evolução futura. *Descartado:* seção repetível agora (escopo/risco sem demanda).
- **Q5 — declaração do escopo. DECIDIDO:** coluna **`form_fields.component_type_id`** (FK nullable →
  `asset_types`). *Descartado:* `config_json` (FK não-enforced, referência solta).
- **Q6 — peso por componente. DECIDIDO:** sempre o **`weight` do `config_json` do campo**, igual
  para todas as instâncias. *Descartado:* peso por componente (evolução futura). Nota no ADR-0008.

---

## 3. Modelo de dados (DDL conceitual)

```text
form_fields
  + component_type_id  UUID NULL  FK -> asset_types(id)   -- NULL = campo geral (atual)

submission_values
  + asset_id  UUID NULL  FK -> assets(id)
  UNIQUE(submission_id, form_field_id)  ->  UNIQUE(submission_id, form_field_id, asset_id) NULLS NOT DISTINCT
  (uq_submission_values_submission_field  ->  uq_submission_values_submission_field_asset)

submission_conformities
  + asset_id  UUID NULL  FK -> assets(id)
  UNIQUE(submission_id, form_field_id)  ->  UNIQUE(submission_id, form_field_id, asset_id) NULLS NOT DISTINCT
  (uq_submission_conformities_submission_field  ->  ..._field_asset)

submissions
  + components_snapshot  JSONB NULL   -- Q1.1: identidade congelada por componente
                                      -- { <asset_id>: { label, type, path } }
```

**Forma do `answers_json` (Q1/Q1.1):** campo geral escalar; campo escopado = **valores puros**
`{ <asset_id>: valor }` (sem metadado). A identidade (label/type/path) vive **só** em
`components_snapshot`, 1× por componente.

> **Nota Postgres (sensível, corrigida em 2026-06-11):** o `UNIQUE` precisa de **`NULLS NOT
> DISTINCT`** (PG 15+) para tratar `NULL` como **igual**. Só assim o histórico (`asset_id NULL`)
> permanece com uma linha por `(submission_id, form_field_id)`, como o constraint antigo garantia.
> O padrão (`NULLS DISTINCT`) trataria cada `NULL` como distinto e permitiria **várias** linhas no
> mesmo campo geral — regressão. Comportamento validado em teste
> (`test_submissions_component.py`) antes de promover a migração; prod roda PG 17.

---

## 4. Migration Alembic (Fase 2 — aditiva)

- `down_revision = "d2e3f4a5b6c7"` (head da Fase 1).
- `upgrade`: add `form_fields.component_type_id` (FK nullable → asset_types); add
  `submission_values.asset_id` e `submission_conformities.asset_id` (FK nullable → assets);
  add `submissions.components_snapshot` (JSONB nullable); **drop** os `UNIQUE` antigos e **create**
  os novos com `asset_id` e **`NULLS NOT DISTINCT`** (ver Nota Postgres em §3); índices auxiliares.
- Histórico fica com `asset_id = NULL` e `components_snapshot = NULL` (sem mudança de
  comportamento). **Reversível.**
- **Sem CASCADE** nos novos FKs de `asset_id` (ativos são soft-deletados; ADR-0009/0015).

---

## 5. Backend

- **Motor de expansão do checklist (Fase 2).** Ao montar a inspeção de um `asset` alvo: campos
  gerais (`component_type_id` nulo) → uma instância (`asset_id = NULL`); campos escopados → uma
  instância por componente do ativo alvo cujo `asset_type_id = component_type_id`
  (`asset_id = <componente>`). Reusa `AssetRepository` (subárvore do alvo).
- **`save_answers` (Fase 2).** Passa a aceitar `asset_id` por resposta; a chave de upsert vira
  `(submission_id, form_field_id, asset_id)`; mantém o `answers_json` no formato Q1 (valores puros)
  na mesma operação (invariante ADR-0006). Tocar `normalize_value`/`serialize_raw_value`/
  `extract_value` apenas se o agrupamento por componente exigir.
- **`components_snapshot` (Fase 2 — Q1.1).** No mesmo `save_answers`, para cada `asset_id` escopado,
  congelar `{ label: asset.identifier, type: asset_type.name, path: <string dos ancestrais via
  cadeia parent> }` em `submissions.components_snapshot[asset_id]`. Gravado uma vez por componente;
  não reescrito após a finalização. Único ponto de escrita, junto com respostas (ADR-0006).
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
  campos escopados; o rótulo/tipo/caminho de cada componente vem de `components_snapshot` (Q1.1),
  sem join a `assets`.

---

## 7. Frontend (Fase 4)

- **Builder** (`FormFieldEditor.vue`): marcar o **escopo de componente** de um campo (seleção de
  `asset_type`); parte da versão publicada imutável (ADR-0005).
- **Inspeção** (`SubmissionDetailView` + `InspectionListRow`/`InspectionFieldRow`): renderizar
  campos escopados como **grupo por componente** (Roda DD/DE/TD/TE), cada um com resposta +
  conformidade própria; reusar o padrão de lista existente.
- **Relatório/PDF**: seções por componente; score breakdown por componente.

> **Limitação temporária (T8, decidida 2026-06-11 — Opção 1).** **Respostas e conformidades já são
> individualizadas por componente** (chave de instância `field_key@asset_id`, `asset_id` enviado em
> `PUT /answers` e `/conformity`). **Evidências permanecem associadas ao campo** (`field_key`),
> compartilhadas entre os componentes daquele campo, até a evolução do módulo de attachments para
> suportar `asset_id`. Motivo: o módulo de attachments tem contrato próprio (localiza/cria o
> `submission_value` apenas por `field_key`) e estendê-lo junto da refatoração da
> `SubmissionDetailView` aumentaria significativamente o tamanho e o risco do PR. **Follow-up:**
> abrir **T8.5** (ou ADR complementar) para adicionar `asset_id` ao fluxo de attachments
> (`AttachmentCreateRequest` → lookup do `submission_value` → `AttachmentResponse` →
> aninhamento no `answers_json`).

---

## 8. Invariantes (do DR-0002 §9)

- **INV1.** `asset_id` da resposta/conformidade ∈ subárvore do `submissions.asset_id`, e do tipo
  `component_type_id` do campo.
- **INV2.** Campo geral (`component_type_id` nulo) ⇒ resposta/conformidade com `asset_id` nulo.
- **INV3.** Snapshot e relacional sempre sincronizados na mesma operação (preserva ADR-0006).
- **INV4.** Score deriva só de `submission_conformities` (ADR-0008), agora por (campo, componente).
- **INV5.** Versões publicadas imutáveis (ADR-0005); `component_type_id` é parte da versão.
- **INV6.** Para todo `asset_id` presente em campos escopados de `answers_json`, existe
  `components_snapshot[asset_id]`; é congelado na finalização e nunca reescrito (fidelidade
  histórica do laudo).

---

## 9. Impacto em ADRs

- **ADR-0006 (modelo híbrido) — REVISADO pela ADR-0016.** A ADR-0016 documenta o `UNIQUE` com
  `asset_id`, o formato do `answers_json` (Q1) e o `components_snapshot` (Q1.1). Concluído.
- **ADR-0008 (score) — extensão leve.** Fórmula igual; cardinalidade por componente. Nota já
  adicionada ao ADR-0008 (Q6).
- **ADR-0005 (versionamento) — mantido.** `component_type_id` na versão imutável.
- **ADR-0007 (config_json) — mantido.** Escopo via coluna (Q5), não em `config_json`.

---

## 10. Faseamento e ordem (mapeado ao DR-0002 §12)

1. **Fase 2a — ADR (revisão do 0006): CONCLUÍDA** — ratificada na **ADR-0016** (formato do snapshot,
   `UNIQUE` com `asset_id`, `components_snapshot`).
2. **Fase 2b — migração aditiva**: `component_type_id` + `asset_id` em values/conformities + novos `UNIQUE` + `submissions.components_snapshot` (tudo NULL no histórico). Bateria de **retrocompatibilidade** antes de seguir.
3. **Fase 2c — motor de expansão + `save_answers` com `asset_id`** + `answers_json` (valores puros) + `components_snapshot`.
4. **Fase 3 — score/breakdown por componente + validação de finalização por instância.**
5. **Fase 4 — frontend** (builder marca escopo; inspeção renderiza por componente; relatório/PDF lê `components_snapshot`).

> Cada fase ≤ 1 PR quando possível; retrocompatibilidade verificada a cada passo (`asset_id NULL` =
> comportamento atual). O **PLANO-DR-0002-Fases2-4** deriva desta SPEC (decisões já fechadas, §2).

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

## 13. Performance e escala (projeção)

> Estimativas de engenharia a partir do schema proposto — **não medidas**. Premissa de formulário
> representativo: **10 campos gerais** (6 booleanos) + **5 campos escopados por componente** (4
> booleanos). Linhas por inspeção: `submission_values = G + S×C`; `submission_conformities =
> Gb + Sb×C`.

### Crescimento por inspeção

| Cenário | Componentes (C) | `submission_values` | `submission_conformities` | Folhas no `answers_json` | Disco/inspeção (heap+índices+snapshot) |
|---|---|---|---|---|---|
| Caminhão | 6 | 40 | 30 | 40 | ~23 KB |
| Ônibus | 12 | 70 | 54 | 70 | ~41 KB |
| Industrial | 300 | 1.510 | 1.206 | 1.510 | ~0,9 MB |

(Os componentes são linhas em `assets`, criadas **uma vez** no cadastro: ~7 / ~13 / ~301.)
Em volume (100 inspeções/mês de cada): caminhão ~48 mil linhas SV/ano; ônibus ~84 mil; industrial
**~1,8 milhão/ano**. O total não é o problema (Postgres lida bem) — o custo é **por requisição**.

### Impacto nos índices

- A troca para **`UNIQUE(submission_id, form_field_id, asset_id)`** aumenta a chave em ~50% (3
  UUIDs) → entradas maiores e mais manutenção.
- **Escrita amplificada no `save_answers`**: a inspeção grava todas as linhas numa transação;
  industrial ≈ **~2.700 linhas + ~10 mil atualizações de índice** numa transação (trivial no
  veicular).
- `ix_*_submission_id` segue sendo o índice quente (carrega o detalhe); `ix_*_form_field_id` vira o
  gargalo de **relatórios cross-inspeção** por campo escopado.
- `asset_id NULL` com **`NULLS NOT DISTINCT`** → histórico permanece único por campo, **sem
  backfill** (o padrão `NULLS DISTINCT` perderia essa unicidade — ver Nota Postgres em §3).

### Consultas mais pesadas

1. **`get_submission` (detalhe/render — hot path):** `selectinload(values)` + `selectinload(conformities)`
   materializa **todas** as linhas da inspeção. Veicular = 70–124 objetos (irrelevante);
   **industrial ≈ 2.700 objetos ORM + montagem de mapas em Python a cada abertura** — o ponto mais
   quente.
2. **`answers_json`:** coluna única, mas industrial ≈ **80–120 KB TOAST** (lido/descomprimido por
   leitura), agravado por chaves UUID de 36 chars.
3. **`calculate_score` / finalização:** O(linhas) em Python (industrial = 1.206 conformidades +
   validação por instância).
4. **Relatórios agregados** por `form_field_id` escopado: varrem muitas linhas conforme a adoção.

### Veredito

- **Veicular (4–12 componentes) — confortável.** Dezenas de linhas, KBs de disco, render trivial.
  O design da ADR-0016 escala sem ressalvas no mercado inicial.
- **Alta cardinalidade (industrial, 300) — caso de estresse**, concentrado em três pressões:
  (a) ~2.700 objetos por render, (b) `answers_json` de ~100 KB, (c) transação de escrita pesada.

### Limites e estratégias futuras (alta cardinalidade)

Fora do escopo do mercado inicial; registrar como evolução quando surgir demanda industrial real:

- **Não carregar a inspeção inteira para render:** paginar/segmentar `values`/`conformities` por
  componente (lazy por grupo) em vez de `selectinload` total.
- **Snapshot enxuto:** para ativos com C alto, enxugar `components_snapshot` (ex.: dropar `path`,
  derivável) ou não snapshotar a identidade — é a parte isolável das respostas (Q1.1).
- **Score incremental** em vez de recomputar O(linhas) a cada chamada.
- **Teto/aviso de cardinalidade** (ex.: alertar acima de ~100 componentes escopados por inspeção).
- **Índice parcial/particionamento por tenant** se relatórios cross-inspeção virarem gargalo medido.

> Nenhuma dessas estratégias é necessária para o veicular; são gatilhadas por **medição**, não
> antecipadamente (evitar otimização prematura — coerente com o ADR-0015).

---

## 14. Próximo passo

Decisões fechadas (§2) e refletidas na **[ADR-0016](../adr/0016-inspecao-por-componente-revisao-modelo-hibrido.md)**.
Aprovada/mergeada a ADR-0016, **derivar o `PLANO-DR-0002-Fases2-4`** com as tarefas das Fases 2–4
(2a já não é necessária — a revisão do ADR-0006 está na ADR-0016) e implementar fase a fase, com
retrocompatibilidade verificada a cada passo.
