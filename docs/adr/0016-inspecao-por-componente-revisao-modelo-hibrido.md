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
  **`(submission_id, form_field_id, asset_id)`** com **`NULLS NOT DISTINCT`** (PG 15+). Tratar
  `NULL` como **igual** mantém a garantia do constraint antigo: o histórico (`asset_id NULL`)
  continua com **uma** linha por `(submission_id, form_field_id)`, enquanto componentes distintos
  (`asset_id` não-nulo) coexistem no mesmo campo — **retrocompatível**. (O padrão `NULLS DISTINCT`
  permitiria múltiplos `NULL` no mesmo campo e perderia essa garantia — regressão; ver Alternativas
  descartadas.)
- **Formato do snapshot (ratifica Q1 do DR-0002):** `answers_json` fica **aninhado** e carrega
  **apenas respostas** — campo geral continua **escalar**; campo escopado vira **mapa de valores
  puros por componente** `{ <asset_id>: valor }`. Ex.:
  `{ "placa": "ABC", "pressao_pneu": { "<roda1>": 32, "<roda2>": 30 } }`. A chave é o `asset_id`
  (UUID) — `identifier` é mutável e não-único, logo inviável como chave. Relacional e snapshot
  continuam escritos na **mesma operação** em `save_answers` (invariante do ADR-0006).
- **Snapshot de identidade do componente (ratifica Q1.1):** a identidade exibível do componente
  (rótulo, tipo, caminho) é **mutável** no cadastro (`identifier` editável e não-único;
  `asset_types.name` e os rótulos dos ancestrais também mudam — embora `asset_id`,
  `parent_asset_id` e `asset_type_id` sejam imutáveis). Para preservar a fidelidade histórica do
  laudo, congela-se essa identidade **uma vez por componente**, **separada das respostas**, numa
  coluna dedicada **`submissions.components_snapshot` (JSONB, nullable)**:
  `{ <asset_id>: { "label": "Roda DD", "type": "Roda", "path": "Caminhão ABC > Eixo 1 > Roda DD" } }`,
  gravada no `save_answers` do momento da inspeção. O `asset_id` liga ao **presente** (rastreio); o
  `components_snapshot` preserva o **passado** (laudo imune a renomeação, desativação ou mudança de
  nome de tipo, sem join ao estado vivo).
- **Score (ADR-0008 inalterado em fórmula):** cada par **(campo booleano × componente)** avaliado é
  uma unidade; a fórmula ponderada não muda, só a cardinalidade. O `weight` vem do `config_json` do
  campo, igual para todas as instâncias (sem peso por componente — ratifica Q6).
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
- **Identidade sem duplicação e sem join:** `components_snapshot` guarda label/type/path **uma vez
  por componente** (não por campo×componente), e o laudo histórico não depende do estado vivo do
  ativo. Custo: uma coluna JSONB adicional, sincronizada no mesmo `save_answers`. Em alta
  cardinalidade, é o campo a enxugar primeiro (ex.: dropar `path`), por ser isolável das respostas.
- **Acoplamento `forms` ↔ `asset_types`:** um formulário escopado só faz sentido para ativos com
  aqueles tipos de componente — validar compatibilidade ao vincular ativo × formulário.
- Volume de `submission_values`/`submission_conformities` cresce por componente — monitorar.

## Alternativas descartadas

- **Chave composta plana no snapshot** (`"pressao_pneu::<roda1>"`): mantém o mapa plano, mas troca
  o formato de chave para todos e depende de convenção de string frágil.
- **Identidade (label/type/path) dentro de cada campo escopado** (`{ <asset_id>: { v, label } }`):
  duplica o rótulo a cada campo × componente para o mesmo componente, com risco de divergência
  interna e mistura de resposta com identidade — por isso a identidade vai para a coluna
  `components_snapshot`, separada e deduplicada (Q1.1).
- **`identifier` como chave do mapa escopado:** `identifier` é mutável e não-único — inviável como
  chave estável/única; o `asset_id` (UUID) é a chave, e o `identifier` é congelado como `label`.
- **Tabela nova `submission_component_values`** separada de `submission_values`: duplica o conceito
  de "valor de resposta", cria dois caminhos de escrita/leitura e força o score a unir duas fontes
  — fragmenta o modelo híbrido (ADR-0006).
- **Snapshot só para campos gerais** (componentes só no relacional): quebra a simetria do ADR-0006
  (leitura rápida) justamente para os campos escopados.
- **Escopo em `config_json`** em vez de coluna (`component_type_id`): sem FK enforced; referência
  cross-context "solta" e consultas mais frágeis — integridade importa demais aqui (cf. ADR-0007,
  que segue válido para configuração de campo, não para esse vínculo estrutural).
- **`UNIQUE` de 3 colunas com `NULLS DISTINCT` (padrão do Postgres):** parecia retrocompatível, mas
  trata cada `NULL` como distinto — permitiria **várias** linhas `(submission_id, form_field_id,
  NULL)` para o mesmo campo geral, perdendo a garantia "uma resposta por campo" do constraint
  antigo (regressão silenciosa, capturada por teste de retrocompat). Por isso `NULLS NOT DISTINCT`.
  *Alternativa equivalente para PG < 15:* índice único parcial `WHERE asset_id IS NULL` (não
  necessário — prod roda PG 17).
- **Manter o ADR-0006 sem alteração:** impossível — a unicidade por campo impede mais de uma
  resposta por campo.
