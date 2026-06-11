# ADR-NNNN — <título curto da decisão>

**Status:** Proposta · **Data:** YYYY-MM-DD
**Supersedes:** — · **Superseded-by:** — · **Revisa/estende:** —

<!--
Template oficial e CANÔNICO de ADR do Smart Audit (Q7.4, ADR-0017).
Status permitidos: Proposta | Aceita | Supersedida | Descartada
- Proposta: decisão acordada, ainda NÃO implementada no código.
- Aceita: implementada e vigente — cite os símbolos do código que a sustentam.
- Supersedida: preencha "Superseded-by: ADR-XXXX" e "Supersedes: ADR-NNNN" no ADR novo.
- Descartada: avaliada e não adotada.
Ao adicionar/alterar status, atualize a tabela em docs/adr/README.md.
Registre apenas decisões verificáveis no código (ver docs/ai/START_HERE.md).

Seções: NÚCLEO é obrigatório; as marcadas "(se aplicável)" entram só quando houver impacto;
a "Governança — Checklist de Sincronização Documental" é OBRIGATÓRIA em toda ADR (com N/A
explícito quando a ADR não altera domínio/dados/API/módulos).
-->

## Contexto

<Qual problema/força motivou a decisão? Restrições reais e verificadas do projeto. Sem inventar.>

## Decisão

<O que foi decidido, no presente. Cite o ponto do código que sustenta/sustentará a decisão
(arquivo/símbolo), no padrão dos ADRs existentes. Numere sub-decisões (Qx, Qx.1…) quando houver.>

## Consequências

- <Efeito positivo>
- <Custo / trade-off / efeito não óbvio>
- <Acoplamento de evolução, se houver (ex.: revisa ADR-XXXX)>

## Alternativas descartadas

- **<Alternativa>:** <por que não foi adotada>.

## Impacto no schema *(se aplicável)*

<Tabelas/colunas/constraints/índices afetados. DDL conceitual. Reversibilidade.>

## Impacto na API *(se aplicável)*

<Endpoints, schemas/DTO, envelope `{data,meta}`/RFC 7807, compatibilidade de contrato.>

## Impacto na migração / Rollout *(se aplicável)*

<Migration Alembic (`down_revision`), backfill, compatibilidade com dados existentes,
ordem de deploy, feature flag, plano de reversão.>

## Impacto operacional *(se aplicável)*

<Performance, armazenamento, segurança/RBAC, tenancy, custo, observabilidade.>

## Critérios de aceite / Requisitos obrigatórios *(se aplicável)*

- <Condição objetiva de pronto / invariante que a implementação deve garantir.>

---

## Governança — Checklist de Sincronização Documental *(OBRIGATÓRIA)*

> Regra permanente do projeto (ADR-0017, Q7.4): toda ADR que altere **domínio de negócio**,
> **modelo de dados**, **contratos de API** ou **arquitetura de módulos** DEVE preencher e resolver
> esta checklist. Cada item marcado **nomeia o arquivo + a mudança** — caixa marcada sem diff
> correspondente reprova o PR. **Definition of Done:** nenhuma implementação derivada da ADR é
> concluída com a checklist pendente.
>
> ADRs que **não** alteram esses eixos marcam: `N/A — não altera domínio/dados/API/módulos`.

| Documento | Impactado? | Arquivo + mudança | Status |
|---|---|---|---|
| ADRs impactadas | ☐ | | ⬜ |
| DRs impactados | ☐ | | ⬜ |
| SPECs impactadas | ☐ | | ⬜ |
| DER (`docs/DER_Smart_Audit.md`) | ☐ | | ⬜ |
| Diagramas arquiteturais | ☐ | | ⬜ |
| Arquitetura (`docs/Arquitetura_Smart_Audit.md`) | ☐ | | ⬜ |
| `CLAUDE.md` | ☐ | | ⬜ |
| `docs/ai/*` (AI_MODELS / AI_RULES / AI_DECISIONS / START_HERE / AI_WORKFLOWS) | ☐ | | ⬜ |
| Relatórios de auditoria arquitetural (`docs/AUDIT_REPORT.md`) | ☐ | | ⬜ |
| Planos de implementação (`docs/specs/PLANO-*`) | ☐ | | ⬜ |
| `docs/adr/README.md` (índice/status) | ☐ | | ⬜ |
| Outros documentos impactados | ☐ | | ⬜ |

<!-- Marque ☑ os impactados, descreva a mudança e leve cada um a ⬜→✅ antes de marcar a ADR como Aceita. -->
