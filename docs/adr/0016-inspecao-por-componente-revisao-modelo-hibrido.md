# ADR-0016 — Inspeção por componente: dimensão `asset_id` no modelo híbrido (revisa ADR-0006)

**Status:** Proposta · **Data:** 2026-06-10
**Supersedes:** — · **Superseded-by:** —
**Revisa/estende:** [ADR-0006](0006-modelo-hibrido-de-respostas.md)

<!--
Status Proposta: decisão acordada, ainda não implementada no código. Origem em
docs/design-records/DR-0002-inspecao-por-componente.md e
docs/specs/SPEC-DR-0002-Fases2-4-InspecaoPorComponente.md (Q1 ratificada aqui).
NÃO supersede o ADR-0006 — o modelo híbrido permanece; ganha a dimensão de componente.
Ao implementar, mudar Status para "Aceita" e citar os símbolos do código que a sustentam.
-->

## Contexto

O DR-0002 (inspeção por componente) precisa que um campo do formulário seja **respondido por
componente** do ativo: inspecionar um Veículo com 4 Rodas gera 4 respostas de "Pressão do pneu",
cada uma com resposta, conformidade e evidência próprias.

O modelo híbrido vigente (ADR-0006) não comporta isso, por duas restrições verificadas no código:

- **Unicidade por campo.** `submission_values` tem `UniqueConstraint(submission_id, form_field_id)`
  (`uq_submission_values_submission_field`) e `submission_conformities` o equivalente
  (`uq_submission_conformities_submission_field`) — **uma** resposta/conformidade por campo.
- **Snapshot por chave de campo.** `submissions.answers_json` é `{ field_key: valor }` (escrito em
  `SubmissionService.save_answers`) — também **sem** dimensão de componente.

A Fase 1 do DR-0002 já entregou o vínculo `submissions.asset_id` (ativo inspecionado), mas **não**
repete campo por componente. Para isso é preciso **estender** o modelo híbrido. Restrições que
moldam a decisão: preservar inspeções históricas (ADR-0009), manter o score derivado de
conformities (ADR-0008), versões publicadas imutáveis (ADR-0005), e a sincronização relacional ×
snapshot do próprio ADR-0006.

## Decisão

Estender o modelo híbrido com uma **dimensão de componente** (`asset_id`), mantendo o
comportamento atual quando `asset_id` é nulo. (Decisão de design; ainda não implementada — ver
Status. Detalhe técnico em
[`SPEC-DR-0002-Fases2-4`](../specs/SPEC-DR-0002-Fases2-4-InspecaoPorComponente.md).)

- **Escopo no campo:** `form_fields.component_type_id` (FK nullable → `asset_types`). Nulo = campo
  geral (comportamento atual); preenchido = o campo repete por componente daquele tipo. É parte da
  versão publicada imutável (ADR-0005).
- **Dimensão na resposta:** adicionar `asset_id` (FK nullable → `assets`) a `submission_values` e a
  `submission_conformities`. A unicidade passa de `(submission_id, form_field_id)` para
  **`(submission_id, form_field_id, asset_id)`**. Como o Postgres trata `NULL` como distinto, as
  linhas históricas (`asset_id NULL`) permanecem únicas por campo — **retrocompatível**.
- **Formato do snapshot (ratifica Q1 do DR-0002):** `answers_json` fica **aninhado** — campo geral
  continua **escalar**; campo escopado vira **mapa por componente** `{ <asset_id>: valor }`.
  Ex.: `{ "placa": "ABC", "pressao_pneu": { "<roda1>": 32, "<roda2>": 30 } }`. Relacional e
  snapshot continuam escritos na **mesma operação** em `save_answers` (invariante do ADR-0006).
- **Score (ADR-0008 inalterado em fórmula):** cada par **(campo booleano × componente)** avaliado é
  uma unidade; a fórmula ponderada não muda, só a cardinalidade.
- **Integridade:** `asset_id` de uma resposta/conformidade deve pertencer à subárvore do
  `submissions.asset_id` e ter `asset_type_id = component_type_id` do campo.

O modelo híbrido do ADR-0006 **permanece**: duas representações sincronizadas. Esta ADR apenas
acrescenta a dimensão de componente a ambas.

## Consequências

- Um campo pode ser avaliado por componente sem criar campos manuais; o inspetor é obrigado a
  percorrer cada componente (validação de finalização por instância).
- **Retrocompatibilidade por `NULL`:** inspeções e formulários existentes (sem escopo, sem
  `asset_id`) continuam idênticos; a migração é aditiva e reversível.
- **Custo (sensível):** muda um `UNIQUE` do core — migração de maior risco do roadmap; exige
  bateria de retrocompatibilidade antes de seguir.
- **Leitores do snapshot precisam saber** se o valor de um `field_key` é escalar (geral) ou mapa
  (escopado) — pequena complexidade adicional de parsing.
- **Acoplamento `forms` ↔ `asset_types`:** um formulário escopado só faz sentido para ativos com
  aqueles tipos de componente — validar compatibilidade ao vincular ativo × formulário.
- Volume de `submission_values`/`submission_conformities` cresce por componente — monitorar.

## Alternativas descartadas

- **Chave composta plana no snapshot** (`"pressao_pneu::<roda1>"`): mantém o mapa plano, mas troca
  o formato de chave para todos e depende de convenção de string frágil.
- **Tabela nova `submission_component_values`** separada de `submission_values`: duplica o conceito
  de "valor de resposta", cria dois caminhos de escrita/leitura e força o score a unir duas fontes
  — fragmenta o modelo híbrido (ADR-0006).
- **Snapshot só para campos gerais** (componentes só no relacional): quebra a simetria do ADR-0006
  (leitura rápida) justamente para os campos escopados.
- **Escopo em `config_json`** em vez de coluna (`component_type_id`): sem FK enforced; referência
  cross-context "solta" e consultas mais frágeis — integridade importa demais aqui (cf. ADR-0007,
  que segue válido para configuração de campo, não para esse vínculo estrutural).
- **Manter o ADR-0006 sem alteração:** impossível — a unicidade por campo impede mais de uma
  resposta por campo.
