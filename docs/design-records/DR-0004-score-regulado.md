# DR-0004 — Score Regulado (item crítico e threshold de aprovação)

**Status:** Proposta · **Data:** 2026-06-08 · **Depende de:** — · **Toca o core:** Estende score
**ADRs relacionadas:** **0008 (score) — extensão**, 0007 (config_json), 0005 (versionamento)

---

## 1. Resumo Executivo

**O que é.** Estender o cálculo de resultado da inspeção com dois conceitos exigidos por normas
(ISO/OSHA/NBR/FDA/GMP):

1. **Item crítico / knockout** — qualquer não conformidade num item marcado como crítico
   **reprova** a inspeção, independentemente do score numérico.
2. **Threshold de aprovação configurável** — o limite de aprovação deixa de ser implícito e
   passa a ser definido por formulário/norma (não um 85 fixo).

Disso resulta um **veredito de aprovação** (aprovado/reprovado) além da nota numérica.

**Problema que resolve.** Hoje há score ponderado (ADR 0008), mas não há "reprova automática por
item crítico" nem limite de aprovação configurável. Em contexto regulado, um item crítico
reprovado deve reprovar tudo — o que o modelo atual não expressa.

**Quem se beneficia.** Mercado regulado e empresas de inspeção que emitem laudo (o veredito é a
base do laudo — ver DR-0005).

---

## 2. Contexto Atual

> Fatos verificados (ADR 0008, 0007; `docs/Arquitetura_Smart_Audit.md`; `frontend/src/utils/score.ts`).

- **Score (ADR 0008):** `round(Σ weight(conforme) / Σ weight(avaliados) * 100, 2)`, a partir de
  `submission_conformities`. N/A e não avaliados ficam fora do denominador. `weight` vem do
  `config_json` (ADR 0007).
- **Breakdown:** `score_breakdown` com `conformes`, `nao_conformes`, `sem_resposta`,
  `total_boolean` (nome legado), `na_count` (sempre 0; cálculo migrou para conformities).
- **Limiares de exibição (frontend):** `utils/score.ts` define `SCORE_THRESHOLD_OK=85`,
  `SCORE_THRESHOLD_WARN=65` — são **limiares de cor/rótulo** (Aprovado/Atenção/Reprovado para
  exibição), **não** um veredito formal de aprovação configurável por norma.
- **Não existe:** conceito de item crítico/knockout, nem threshold de aprovação por
  formulário, nem veredito formal de inspeção.

**Dor:** o resultado é só um número; não expressa "reprovado porque o freio falhou" nem permite
que cada norma defina seu próprio limite.

---

## 3. Objetivos

### Funcionais

- **OF1.** Marcar um campo como **crítico** (config do campo).
- **OF2.** Definir, por formulário/versão, o **threshold de aprovação** (limite numérico).
- **OF3.** Calcular um **veredito** (`aprovado`|`reprovado`) por inspeção, combinando: itens
  críticos não conformes ⇒ reprovado; senão, score ≥ threshold ⇒ aprovado.
- **OF4.** Expor no breakdown quantos itens críticos existem e quantos reprovaram.
- **OF5.** Preservar o score numérico ponderado (ADR 0008) inalterado como métrica.

### Não Funcionais

- **ONF1. Retrocompatibilidade:** sem campo crítico e sem threshold definido, o comportamento
  numérico atual permanece; veredito vira opcional/derivado de default.
- **ONF2.** Configuração de criticidade segue a filosofia `config_json` (ADR 0007) — sem coluna
  esparsa.
- **ONF3.** Veredito é determinístico e auditável (mesma entrada ⇒ mesmo resultado).

---

## 4. Não Objetivos

- **NÃO** alterar a **fórmula** do score ponderado (ADR 0008) — apenas adicionar veredito.
- **NÃO** emitir laudo/certificado (isso é o **DR-0005**); este DR só produz o **veredito** que
  o laudo consome.
- **NÃO** implementar score por componente (isso é o **DR-0002**); os dois são compatíveis mas
  independentes.
- **NÃO** mudar os limiares de **cor** do frontend (exibição) — embora possam passar a respeitar
  o threshold configurado.

---

## 5. Alternativas Consideradas

### 5.1 Onde marcar "item crítico"

**A) `config_json.critical: bool` no campo.** ✅
- *Vantagens:* alinhado ao ADR 0007 (config no JSONB); sem migração; parte da versão imutável
  (ADR 0005).
- *Desvantagens:* não enforced no banco (validação no service).
- *Escolha:* recomendada — coerente com `weight`/`allow_na`.

**B) Coluna `form_fields.is_critical`.**
- *Vantagens:* enforced, consultável.
- *Desvantagens:* migração; foge do padrão `config_json` para uma flag de campo.
- *Rejeição (como principal):* `config_json` já é o lar de config de campo.

### 5.2 Onde definir o threshold de aprovação

**A) Config no nível do **formulário/versão** (ex.: `form_versions.config_json.pass_threshold`).** ✅
- *Vantagens:* cada norma/checklist define seu limite; imutável por versão (ADR 0005).
- *Escolha:* recomendada.

**B) Global por empresa.**
- *Desvantagens:* uma empresa pode operar várias normas com limites diferentes.
- *Rejeição:* granularidade errada.

### 5.3 Onde calcular/armazenar o veredito

**A) Derivado no cálculo de finalização e **persistido** na submission (ex.:
`submissions.verdict`).** ✅
- *Vantagens:* veredito estável no laudo; auditável; não recalcula a cada leitura.
- *Escolha:* recomendada.

**B) Sempre derivado em runtime (não persiste).**
- *Desvantagens:* laudo poderia divergir se regras mudassem; menos auditável.
- *Rejeição:* laudo precisa de veredito congelado no momento da finalização.

---

## 6. Solução Recomendada

### Conceitos

- **Item crítico:** campo com `config_json.critical = true`. Se sua conformidade for
  `nao_conforme`, a inspeção é **reprovada** independentemente do score.
- **Threshold de aprovação:** limite numérico definido na versão do formulário
  (`config_json.pass_threshold`). Sem itens críticos reprovados, `score ≥ threshold` ⇒ aprovado.
- **Veredito:** `reprovado` se houver crítico não conforme **ou** `score < threshold`; senão
  `aprovado`. Persistido na finalização.

### Regras de negócio

- **RN1.** Qualquer item crítico com conformidade `nao_conforme` ⇒ veredito `reprovado`
  (knockout), ignorando o score.
- **RN2.** Sem críticos reprovados: `score ≥ pass_threshold` ⇒ `aprovado`; senão `reprovado`.
- **RN3.** `pass_threshold` ausente ⇒ usa um default (a definir; ex.: comportamento atual de
  exibição) — retrocompatível.
- **RN4.** O **score numérico** continua calculado exatamente como no ADR 0008.
- **RN5.** O breakdown ganha `critical_total` e `critical_failed`.
- **RN6.** O veredito é congelado na finalização (persistido), base do laudo (DR-0005).

---

## 7. Impacto Arquitetural

- **Banco.** `submissions` + `verdict` (ex.: `aprovado`|`reprovado`, nullable até finalizar).
  `form_versions.config_json.pass_threshold` e `form_fields.config_json.critical` (sem novas
  colunas — usa JSONB existente, ADR 0007).
- **Backend.** `SubmissionService.calculate_score`/`calculate_score_breakdown` ganham a lógica
  de veredito e a contagem de críticos; a finalização persiste `verdict`. Acoplamento de
  evolução já previsto no ADR 0008 (mudar score = tocar essas funções).
- **Frontend.** Builder: marcar campo como crítico; definir threshold no formulário. Inspeção/
  relatório: exibir veredito + itens críticos reprovados em destaque. `utils/score.ts` pode
  passar a respeitar o threshold configurado.
- **APIs.** Resposta de submission/breakdown ganha `verdict`, `critical_total`,
  `critical_failed`. Envelope + RFC 7807 (ADR 0011).
- **Auditoria.** `audit_logs`: registrar veredito na finalização (`submission.finished` com
  veredito).

---

## 8. Impacto em ADRs

- **ADR 0008 (score) — EXTENSÃO.** Adiciona veredito (item crítico + threshold) sem alterar a
  fórmula. Atualizar o 0008 (ou ADR nova que o estende) documentando veredito e os novos campos
  de breakdown.
- **ADR 0007 (config_json) — reuso.** `critical` (campo) e `pass_threshold` (versão) entram no
  JSONB existente.
- **ADR 0005 (versionamento) — mantido.** Criticidade e threshold fazem parte da versão imutável.
- **Nova ADR (opcional):** *"Veredito de aprovação por item crítico e threshold"*.

---

## 9. Modelo de Domínio

### Mudanças (conceituais)

```
form_fields.config_json     + critical: bool            (default false)
form_versions.config_json   + pass_threshold: number    (opcional)
submissions                 + verdict: 'aprovado'|'reprovado'  (nullable até finalizar)
score_breakdown             + critical_total, critical_failed
```

### Invariantes

- **INV1.** Veredito determinístico: mesma configuração + mesmas conformidades ⇒ mesmo veredito.
- **INV2.** Crítico não conforme ⇒ `reprovado` (precede o threshold).
- **INV3.** Score numérico permanece como no ADR 0008.
- **INV4.** Veredito é congelado na finalização (não muda em leituras posteriores).
- **INV5.** Criticidade/threshold pertencem à versão imutável do formulário (ADR 0005).

---

## 10. Fluxos

### Principal

1. No builder, marca-se "Freio funcionando" como **crítico**; define-se `pass_threshold = 90`.
2. Inspeção é executada; conformidades avaliadas.
3. Finalização: se "Freio" = `nao_conforme` ⇒ `reprovado` (mesmo com score 95). Senão, `score ≥
   90` ⇒ `aprovado`.
4. Veredito persistido; consumido pelo laudo (DR-0005).

### Cenários de erro/limite

- **Sem `pass_threshold` definido** ⇒ usa default (RN3).
- **Item crítico não avaliado** (sem conformidade) ⇒ tratar como pendência de finalização (não
  reprova por omissão; a finalização exige avaliação). Decisão fina em Q3.
- **Todos N/A** ⇒ sem denominador; veredito segue regra de score vazio (a definir — Q4).

---

## 11. Riscos

### Técnicos
- **R-T1. Acoplamento em `calculate_score`.** Mudança concentrada (já previsto no ADR 0008).
  *Mitigação:* testes do veredito (críticos, threshold, defaults).
- **R-T2. Retrocompatibilidade do breakdown** (nomes legados). *Mitigação:* só adicionar campos,
  não remover.

### Negócio
- **R-N1. Configuração incorreta de criticidade** pelo cliente (marca tudo crítico). *Mitigação:*
  UI explica o efeito knockout; sugestão da IA (DR-0003) com moderação.

### Operacionais
- **R-O1. Divergência de veredito** se regra mudar pós-finalização. *Mitigação:* veredito
  congelado/persistido (INV4).

---

## 12. Estratégia de Implementação

- **Fase 1.** `config_json.critical` + lógica de knockout no cálculo + `critical_*` no breakdown.
- **Fase 2.** `pass_threshold` na versão + cálculo do veredito + persistência em `submissions`.
- **Fase 3.** Frontend: marcar crítico, definir threshold, exibir veredito e críticos
  reprovados.

---

## 13. Critérios de Aceitação

- **CA1.** Inspeção com um item crítico `nao_conforme` resulta `reprovado` mesmo com score acima
  do threshold.
- **CA2.** Sem críticos reprovados, `score ≥ pass_threshold` ⇒ `aprovado`; `<` ⇒ `reprovado`.
- **CA3.** Formulário sem críticos e sem threshold mantém o comportamento numérico atual
  (retrocompatível).
- **CA4.** O score numérico (ADR 0008) é idêntico ao atual nos casos sem veredito.
- **CA5.** Breakdown expõe `critical_total` e `critical_failed`.
- **CA6.** Veredito persistido não muda em leituras posteriores.

---

## 14. Questões em Aberto

- **Q1.** Default de `pass_threshold` quando não definido (usar 85 da exibição? exigir sempre?).
- **Q2.** Há **níveis** de criticidade (crítico × maior × menor), comum em normas, ou só
  binário crítico/não?
- **Q3.** Item crítico **não avaliado**: bloqueia finalização (recomendado) ou conta como
  reprovado?
- **Q4.** Veredito quando não há itens avaliados (todos N/A): `aprovado`, `reprovado` ou
  `inconclusivo`?
- **Q5.** Score/threshold por **seção/categoria** (score composto), comum em algumas normas?

---

## 15. Evoluções Futuras

> Fora do escopo deste DR.

- **Níveis de não conformidade** (crítica/maior/menor) com pesos e regras distintas.
- **Score por categoria/seção** e aprovação composta (todas as seções ≥ X).
- **Regras de aprovação programáveis** por norma (motor de regras).
- **Validade do veredito** (laudo expira em N meses — conecta recorrência).
- **Reprovação parcial por componente** (conecta DR-0002: reprovar o ativo se um componente
  crítico reprovar).
