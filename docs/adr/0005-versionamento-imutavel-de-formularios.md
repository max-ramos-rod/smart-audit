# ADR-0005 — Versionamento imutável de formulários

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

Formulários (checklists) evoluem com o tempo, mas inspeções já realizadas precisam permanecer
legíveis exatamente como foram preenchidas. Editar um template em uso não pode corromper o
histórico.

## Decisão

Separar **`forms`** (template lógico) de **`form_versions`** (o que as inspeções referenciam).
Verificado em `FormService.publish_new_version`:

- Publicar uma nova versão **cria** `FormVersion` + `FormField` novos; **nunca** muta campos de
  uma versão existente.
- Cada `submission` referencia um `form_version_id` para sempre.
- `form_versions` tem `UNIQUE(form_id, version)` e `CHECK status IN (draft, published, archived)`.

## Consequências

- Inspeções históricas continuam consistentes com a versão usada.
- Comparação entre versões e auditoria de mudança ficam naturais.
- Custo de armazenamento: cada versão duplica o conjunto de campos.
- O fluxo atual sempre cria versões já `published` (não há editor de rascunho de versão —
  ver AI_DECISIONS).
- Mudança estrutural exige publicar versão; não há "patch" in-place.

## Alternativas descartadas

- **Editar `form_fields` in-place:** quebra inspeções passadas (respostas apontariam para
  campos alterados/removidos).
- **Snapshot apenas em `answers_json`, sem versão relacional:** perde a estrutura tipada
  (labels, tipos, ordem) necessária para relatórios e re-render fiel.
- **Soft delete de campos com flag de vigência:** complica todas as queries de campo com
  filtros temporais frágeis.
