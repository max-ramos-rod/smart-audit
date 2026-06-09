# DR-0002 — Inspeção por Componente

**Status:** Proposta · **Data:** 2026-06-08 · **Depende de:** DR-0001 · **Toca o core:** **Sim**
**ADRs relacionadas:** **0006 (modelo híbrido — impacto direto)**, 0008 (score), 0005, 0007

> ⚠️ **Este é o único DR que altera o core.** Muda a unicidade de `submission_values`/
> `submission_conformities` e o formato do snapshot `answers_json` (ADR 0006). Deve ser a
> **última** iniciativa da sequência, com migração testada e retrocompatibilidade total.

---

## 1. Resumo Executivo

**O que é.** Permitir que um campo (ou seção) do formulário seja **repetido por componente** do
ativo inspecionado. Ao inspecionar um Veículo com 4 Rodas, o campo "Pressão do pneu" se expande
em 4 instâncias (uma por roda), cada uma com **resposta, conformidade e evidência próprias**.

**Problema que resolve.** Hoje (e mesmo com o DR-0001) a inspeção é por campo, não por
componente. Para granularidade por roda é preciso criar 4 campos manuais; e o inspetor pode
esquecer um componente, pois nada o obriga a percorrer cada um.

**Quem se beneficia.** Inspeções de objetos com partes repetidas/críticas: veículos (rodas,
portas), prédios (cômodos), máquinas (componentes), estruturas (vãos, cabos).

---

## 2. Contexto Atual

> Fatos verificados (ADR 0006, 0008; `docs/DER_Smart_Audit.md`).

- **Modelo híbrido (ADR 0006):** resposta gravada **duas vezes** em `SubmissionService.save_answers`:
  (1) relacional em `submission_values` com `UNIQUE(submission_id, form_field_id)`; (2) snapshot
  `submissions.answers_json = { field_key: valor }`. Ambos sincronizados na mesma operação; a
  criação de anexo também escreve no snapshot.
- **Conformidade (ADR 0008):** `submission_conformities` com `UNIQUE(submission_id,
  form_field_id)` e `CHECK status IN (conforme, nao_conforme)`. O **score** deriva daqui:
  `Σ weight(conforme) / Σ weight(avaliados) * 100`.
- **Campos (ADR 0007):** `form_fields.config_json` guarda config do campo; `weight` é lido de
  qualquer campo não-`section`.
- **DR-0001** entrega `assets` (árvore) e `submissions.asset_id` (vínculo da inspeção ao ativo),
  mas **não** repete campo por componente.

**Limitação central:** a unicidade `(submission_id, form_field_id)` permite **uma** resposta/
conformidade por campo. Não há dimensão de componente. O snapshot `answers_json` é uma chave por
`field_key` — também sem componente.

---

## 3. Objetivos

### Funcionais

- **OF1.** Declarar, num campo (ou seção) do formulário, um **escopo de componente** (tipo de
  ativo): "este item repete por Roda".
- **OF2.** Na execução, **expandir** o campo escopado em uma instância por componente daquele
  tipo sob o ativo alvo, cada uma respondível e avaliável independentemente.
- **OF3.** Vincular **resposta, conformidade e evidência** a um **componente específico**
  (`asset_id`).
- **OF4.** Validar a finalização exigindo que **cada** instância obrigatória (por componente)
  seja respondida — o inspetor não pode esquecer um componente.
- **OF5.** Calcular o **score** com a dimensão de componente (cada par campo×componente é uma
  unidade avaliada), preservando a fórmula ponderada (ADR 0008).

### Não Funcionais

- **ONF1. Retrocompatibilidade total:** `asset_id` nulo = comportamento atual. Formulários e
  inspeções existentes funcionam inalterados.
- **ONF2.** Snapshot `answers_json` permanece consistente com o relacional (invariante do ADR
  0006), mesmo com múltiplos valores por `field_key`.
- **ONF3.** Migração reversível e testada; nenhuma inspeção histórica corrompida.

---

## 4. Não Objetivos

- **NÃO** cadastrar ativos/árvore (isso é o **DR-0001**, pré-requisito).
- **NÃO** mudar a fórmula do score (apenas a *cardinalidade* das unidades) — alterações de
  critério de aprovação são o **DR-0004**.
- **NÃO** suportar campos escopados a componentes de **tipos diferentes** num mesmo grupo (1
  campo → 1 tipo de componente).
- **NÃO** permitir edição in-place de versões publicadas (ADR 0005 mantido).

---

## 5. Alternativas Consideradas

### 5.1 Como declarar o escopo de componente no campo

**A) Coluna explícita `form_fields.component_type_id` (FK nullable → `asset_types`).** ✅
- *Vantagens:* integridade referencial; consultável; explícito no schema da versão (ADR 0005).
- *Desvantagens:* migração em `form_fields`; acopla `forms` a `asset_types`.
- *Escolha:* recomendada — o escopo é estrutural e merece integridade.

**B) Dentro de `config_json` (`config_json.repeat_per_component_type`).**
- *Vantagens:* sem migração (alinhado ao ADR 0007).
- *Desvantagens:* FK não enforced; referência cross-context "solta"; consultas mais frágeis.
- *Rejeição (como principal):* integridade importa demais aqui; fica como fallback se a
  migração em `form_fields` for indesejada.

### 5.2 Onde guardar a dimensão de componente na resposta

**A) `submission_values.asset_id` + `submission_conformities.asset_id`; unicidade vira
`(submission_id, form_field_id, asset_id)`.** ✅
- *Vantagens:* mínimo e direto; `asset_id` nulo preserva o passado; consultas por componente
  naturais.
- *Desvantagens:* muda um `UNIQUE` do core (migração sensível).
- *Escolha:* recomendada.

**B) Tabela nova `submission_component_values` separada.**
- *Vantagens:* não toca a tabela existente.
- *Desvantagens:* duplica o conceito de "valor de resposta"; dois caminhos de escrita/leitura;
  score teria de unir duas fontes.
- *Rejeição:* fragmenta o modelo híbrido (ADR 0006) em dois lugares.

### 5.3 Formato do snapshot `answers_json` com componentes (o ponto mais sensível)

O snapshot hoje é `{ field_key: valor }`. Com componentes, há **vários** valores por `field_key`.

**A) Aninhado:** campo geral → escalar; campo escopado → `{ component_id: valor }`.
`answers_json = { "placa": "ABC", "pressao_pneu": { "<roda1>": 32, "<roda2>": 30, ... } }`
- *Vantagens:* estrutura clara; geral continua escalar (retrocompat de leitura).
- *Desvantagens:* leitores do snapshot precisam saber se o valor é escalar ou objeto.
- *Recomendada* (com `component_id` = `asset_id` do componente).

**B) Chave composta plana:** `"pressao_pneu::<roda1>": 32`.
- *Vantagens:* mantém o mapa plano.
- *Desvantagens:* muda o formato de chave para todos; parsing por convenção de string.
- *Rejeição:* convenção de string frágil.

**C) Snapshot só para campos gerais; componentes só no relacional.**
- *Vantagens:* `answers_json` não muda.
- *Desvantagens:* quebra a simetria do ADR 0006 (leitura rápida) para campos escopados.
- *Rejeição:* enfraquece a razão de existir do snapshot.

> **Decisão de design pendente formal (Q1):** alternativa **A** é a recomendada, mas a escolha
> final do formato do snapshot é a principal decisão a ratificar numa ADR que **revisa o ADR 0006**.

---

## 6. Solução Recomendada

### Comportamento

1. Um `form_field` pode ter `component_type_id` (tipo de componente). Campo sem isso = geral
   (comportamento atual).
2. Ao executar a inspeção de um `asset` alvo, o motor monta o checklist:
   - campos gerais (sem `component_type_id`): uma instância, `asset_id = NULL`;
   - campos escopados: o motor busca os **componentes** do ativo alvo cujo `asset_type_id =
     component_type_id` e gera **uma instância por componente** (`asset_id = <componente>`).
3. Resposta/conformidade/evidência são gravadas com `asset_id` (nulo para geral).
4. A finalização valida obrigatoriedade **por instância expandida**.
5. O score soma cada par campo×componente avaliado (fórmula do ADR 0008 inalterada).

### Regras de negócio

- **RN1.** `asset_id = NULL` ⇒ campo geral (idêntico ao comportamento atual).
- **RN2.** Campo escopado expande por **todos** os componentes do tipo sob o ativo alvo.
- **RN3.** `asset_id` de uma resposta/conformidade deve ser componente **da árvore do ativo
  alvo** da inspeção (integridade — ver INV).
- **RN4.** Campo escopado **obrigatório** ⇒ cada instância expandida é obrigatória.
- **RN5.** Snapshot `answers_json` representa campos escopados como mapa por componente
  (formato a ratificar — Q1), mantido em sincronia na mesma operação (ADR 0006).
- **RN6.** Score: cada par (campo booleano × componente) com conformidade entra na fórmula
  ponderada; `weight` vem do `config_json` do campo (igual para todas as instâncias).

---

## 7. Impacto Arquitetural

- **Banco (sensível).**
  - `submission_values`: + `asset_id` (FK nullable → `assets`); `UNIQUE(submission_id,
    form_field_id)` → `UNIQUE(submission_id, form_field_id, asset_id)`.
  - `submission_conformities`: + `asset_id` (FK nullable); mesma mudança de unicidade.
  - `form_fields`: + `component_type_id` (FK nullable → `asset_types`).
  - **Migração:** preencher `asset_id = NULL` no histórico; o novo `UNIQUE` é compatível com
    `NULL` (uma linha por campo, como hoje). Reversível.
- **Backend.** `SubmissionService.save_answers` passa a aceitar `asset_id` por resposta e a
  manter o snapshot no novo formato; o motor de montagem do checklist expande campos escopados;
  `calculate_score`/`calculate_score_breakdown` iteram por (campo, componente); validação de
  finalização considera instâncias expandidas.
- **Frontend.** A tela de inspeção renderiza campos escopados como grupo por componente (Roda
  DD/DE/TD/TE), cada um com resposta + conformidade + evidência; o builder permite marcar o
  escopo de componente de um campo/seção.
- **APIs.** Os endpoints de answers/conformity passam a aceitar `asset_id` por item; envelope e
  RFC 7807 mantidos (ADR 0011).
- **Auditoria/Observabilidade.** Volume de `submission_values`/`conformities` cresce por
  componente — monitorar. Score breakdown ganha contagem por componente.

---

## 8. Impacto em ADRs

- **ADR 0006 (modelo híbrido) — REVISÃO NECESSÁRIA.** A unicidade muda e o snapshot
  `answers_json` ganha dimensão de componente. Requer **nova ADR que revisa/estende o 0006**
  (documentando o novo `UNIQUE` e o formato do snapshot).
- **ADR 0008 (score) — extensão leve.** A fórmula não muda; a cardinalidade das unidades sim.
  Atualizar o texto do 0008 (ou nota) para refletir score por componente. (Critério de
  aprovação por item crítico é o DR-0004, separado.)
- **ADR 0005 (versionamento) — mantido.** `component_type_id` faz parte da versão publicada
  imutável.
- **ADR 0007 (config_json) — mantido/alternativo.** O escopo poderia viver em `config_json`
  (alternativa 5.1-B), mas recomenda-se coluna explícita.
- **Nova ADR:** *"Inspeção por componente"* — registra `asset_id` em values/conformities, o
  novo `UNIQUE`, e o formato do snapshot.

---

## 9. Modelo de Domínio

### Mudanças (conceituais; sem DDL)

```
form_fields              + component_type_id?  (FK -> asset_types)
submission_values        + asset_id?           (FK -> assets)
                         UNIQUE(submission_id, form_field_id, asset_id)
submission_conformities  + asset_id?           (FK -> assets)
                         UNIQUE(submission_id, form_field_id, asset_id)
submissions.answers_json  campo escopado → { component_id: valor }   (Q1)
```

### Invariantes

- **INV1.** `asset_id` de uma resposta/conformidade ∈ subárvore do `submissions.asset_id` alvo,
  e do tipo igual ao `component_type_id` do campo.
- **INV2.** Campo geral (`component_type_id` nulo) ⇒ resposta/conformidade com `asset_id` nulo.
- **INV3.** Snapshot e relacional sempre sincronizados na mesma operação (preserva ADR 0006).
- **INV4.** Score deriva só de `submission_conformities` (preserva ADR 0008), agora por
  (campo, componente).
- **INV5.** Versões publicadas permanecem imutáveis (ADR 0005); `component_type_id` é parte da
  versão.

---

## 10. Fluxos

### Principal — inspeção com componentes

1. Inspeção do "Veículo ABC" (DR-0001) com formulário cujo campo "Pressão do pneu" tem
   `component_type_id = Roda`.
2. Motor encontra 4 componentes Roda sob ABC → expande o campo em 4 instâncias.
3. Inspetor responde/avalia cada roda; anexa evidência por roda.
4. Finalização exige as 4; score soma os 4 pares campo×componente avaliados.

### Cenários de erro

- **Campo escopado sem componentes** do tipo no ativo alvo → expande para zero; a spec decide
  entre "campo omitido" e "aviso de inconsistência" (Q2).
- **Resposta com `asset_id` fora da árvore/tipo** → rejeitada (INV1).
- **Finalizar com um componente pendente** → bloqueado (RN4).
- **Inspeção sem `asset_id`** com campo escopado → o campo escopado não pode expandir; a spec
  decide tratar como erro de configuração ou ignorar (Q3).

---

## 11. Riscos

### Técnicos
- **R-T1. Mudança de `UNIQUE` no core.** Risco de regressão em `save_answers` e no score.
  *Mitigação:* migração reversível; `asset_id` nulo preserva o passado; bateria de testes de
  retrocompatibilidade antes de tudo.
- **R-T2. Sincronização do snapshot** (ADR 0006) com formato aninhado. *Mitigação:* único ponto
  de escrita (`save_answers`); testes que comparam relacional × snapshot.
- **R-T3. Acoplamento `forms` ↔ `asset_types`.** Um formulário escopado só faz sentido para
  ativos com aqueles tipos de componente. *Mitigação:* validar compatibilidade ao vincular
  ativo×formulário; mensagem clara.

### Negócio
- **R-N1. Complexidade de UX.** Renderizar grupos por componente pode confundir. *Mitigação:*
  agrupamento visual claro (Roda DD/DE/…); reusar o padrão de lista de inspeção existente.

### Operacionais
- **R-O1. Crescimento de volume** de respostas/conformidades. *Mitigação:* índices; monitorar
  tamanho de `answers_json`.

---

## 12. Estratégia de Implementação

- **Fase 1.** Migração aditiva: `asset_id` em values/conformities + novo `UNIQUE`;
  `component_type_id` em form_fields. Tudo nulo no histórico (sem mudança de comportamento).
- **Fase 2.** Motor de expansão (montagem do checklist por componente) + `save_answers` com
  `asset_id` + novo formato de snapshot.
- **Fase 3.** Score/breakdown por componente + validação de finalização por instância.
- **Fase 4.** Builder (marcar escopo) + render de inspeção por componente no frontend.

> Fase 1 é puramente aditiva e segura; o risco concentra-se nas Fases 2–3 (lógica de escrita e
> score). Manter retrocompatibilidade verificada a cada fase.

---

## 13. Critérios de Aceitação

- **CA1.** Inspeção **sem** `asset_id` e formulário **sem** campo escopado funcionam idênticos
  ao comportamento atual (retrocompatibilidade).
- **CA2.** Para um ativo com 4 componentes do tipo X e um campo escopado a X, a inspeção exige 4
  respostas/conformidades distintas; finalizar com uma pendente é bloqueado.
- **CA3.** Score de uma inspeção com componentes soma cada par campo×componente avaliado,
  excluindo N/A e não avaliados (consistente com ADR 0008).
- **CA4.** Snapshot `answers_json` e `submission_values` permanecem consistentes para campos
  escopados (mesma fonte de verdade).
- **CA5.** Resposta com `asset_id` fora da árvore/tipo do ativo alvo é rejeitada (RFC 7807).
- **CA6.** Migração é reversível e nenhuma inspeção histórica é alterada.

---

## 14. Questões em Aberto

- **Q1.** Formato definitivo do snapshot `answers_json` para campos escopados (aninhado ×
  composto) — decisão que **revisa o ADR 0006**.
- **Q2.** Campo escopado sem componentes correspondentes no ativo: omitir ou sinalizar?
- **Q3.** Campo escopado em inspeção **sem** `asset_id`: erro de configuração ou ignorar?
- **Q4.** Escopo por **campo** apenas, ou também por **seção** (grupo repetível inteiro)?
- **Q5.** Declaração do escopo: coluna `component_type_id` (recomendado) vs `config_json`.
- **Q6.** Peso por componente: sempre o `weight` do campo, ou permitir peso por componente
  (ex.: roda dianteira pesa mais)? (Default: peso do campo.)

---

## 15. Evoluções Futuras

> Fora do escopo deste DR.

- **Peso por componente** (criticidade diferente por posição).
- **Condicional por componente** (mostrar item só para certos componentes).
- **Herança de resultado** (reprovar o ativo se qualquer componente crítico reprovar — conecta
  ao DR-0004).
- **Comparação histórica por componente** (evolução do amortecedor dianteiro ao longo do tempo).
