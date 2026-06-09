# Design Records — Smart Audit

Registros de design **durável** por funcionalidade. Cada DR captura decisões, contexto e
intenção de uma iniciativa de evolução, em formato suficiente para depois gerar **ADRs, specs,
user stories, tasks, test plans** — sem rediscutir a arquitetura.

**Diferença para ADR:** um ADR registra **uma decisão pontual já tomada/vigente** (`docs/adr/`).
Um Design Record descreve **uma funcionalidade proposta** em profundidade (problema, modelo,
fluxos, riscos, fases), e *origina* um ou mais ADRs quando a decisão é tomada.

> Visão consolidada/estratégica e roadmap geral: [`../Design_Record_Evolutivo.md`](../Design_Record_Evolutivo.md).
> Este diretório quebra aquela visão em iniciativas focadas e independentes.

## Ciclo de vida (Status)

- **Proposta** — em discussão, ainda não implementada.
- **Em implementação** — fase iniciada no código.
- **Implementada** — concluída; decisões consolidadas viram/atualizam ADRs.
- **Descartada** — avaliada e não adotada.

## Estrutura de cada DR

Todos seguem a mesma estrutura de 15 seções: Resumo Executivo · Contexto Atual · Objetivos ·
Não-Objetivos · Alternativas · Solução Recomendada · Impacto Arquitetural · Impacto em ADRs ·
Modelo de Domínio · Fluxos · Riscos · Estratégia de Implementação · Critérios de Aceitação ·
Questões em Aberto · Evoluções Futuras.

## Índice

| DR | Iniciativa | Status | Depende de | Toca o core? | ADRs relacionadas |
|---|---|---|---|---|---|
| [DR-0001](DR-0001-ativos-genericos.md) | Ativos genéricos (árvore de componentes, owner próprio×cliente) | Proposta | — | Não (aditivo) | 0003, 0007 |
| [DR-0002](DR-0002-inspecao-por-componente.md) | Inspeção por componente (dimensão de componente nas respostas) | Proposta | DR-0001 | **Sim** | **0006**, 0008 |
| [DR-0003](DR-0003-geracao-checklist-ia.md) | Geração de checklist por IA (pipeline assíncrono) | Proposta | — | Não | 0005, 0007 |
| [DR-0004](DR-0004-score-regulado.md) | Score regulado (item crítico/knockout + threshold) | Proposta | — | Estende score | **0008** |
| [DR-0005](DR-0005-acoes-corretivas-laudo.md) | Ações corretivas + re-inspeção + laudo | Proposta | DR-0004 (laudo) | Não (aditivo) | 0008, 0011 |
| [DR-0006](DR-0006-abstracao-relatorio.md) | Abstração de relatório (`ReportRenderer`) | Proposta | — | Não (aditivo) | 0011, 0013 |

## Sequência recomendada (orientada a receita e a contrato)

```
Fundação (fora deste diretório): storage externo (R2), onboarding sem SSH, e-mail transacional
   │
   ├─ DR-0003 (IA)            ← diferencial que acelera vendas; independente; baixo risco
   ├─ DR-0001 (Ativos)        ← vincular objeto; aditivo; atende os dois mercados
   ├─ DR-0004 (Score regulado) + DR-0006 (Relatório)  ← destrava regulado
   ├─ DR-0005 (Ações corretivas + laudo)              ← fecha o ciclo de conformidade
   └─ DR-0002 (Inspeção por componente)               ← MAIOR risco (toca ADR 0006); por último
```

**Princípio:** cada DR é destravado por demanda real (contrato/cliente), não por especulação.
DR-0002 é o único que toca o core (modelo híbrido, ADR 0006) e deve vir por último, com
migração testada e retrocompatibilidade (`asset_id` nulo = comportamento atual).

## Como usar para gerar artefatos depois

- **ADR** → a partir das seções 6 (Solução) + 8 (Impacto em ADRs) + 9 (Modelo) de cada DR.
- **User stories** → a partir dos Objetivos (OF/ONF) e Critérios de Aceitação (CA).
- **Test plan** → a partir dos Critérios de Aceitação + Fluxos (cenários de erro).
- **Tasks/épicos** → a partir da Estratégia de Implementação (fases).
