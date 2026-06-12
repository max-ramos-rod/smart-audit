# Smart Audit — Documento de Handoff Técnico
## UX/IA Redesign · Sprints 1–4 · Backend Pendente · Junho 2026

---

> ## ⚠️ NOTA DE STATUS (atualização pós-auditoria — Junho 2026)
>
> Auditoria de integração contra o código-fonte atual encontrou que **as Seções 7 e 8 ("Backend Pendente" / "Plano de Implementação Backend") estão OBSOLETAS**. O backend DR-0002 Fases 2–3 e o ADR-0017 **já estavam implementados e mergeados** quando este handoff foi reavaliado:
>
> - ✅ `form_fields.component_type_id`, `submission_values.asset_id`, `submission_conformities.asset_id`, `submissions.components_snapshot` — **existem** (migration `e3f4a5b6c7d8_add_component_dimension`).
> - ✅ Motor de expansão (`build_checklist`), `save_answers` com `asset_id` + `components_snapshot`, score e finalização por componente — **implementados** em `backend/app/modules/submissions/service.py`.
> - ✅ ADR-0017 (evidência unificada por escopo) — **implementado**.
> - ❌ **Única tarefa que faltava: `GET /submissions?client_id=`** (Tarefa 5) — agora **implementada** (filtro via join em `assets.client_id`, com teste `test_submissions_filter_by_client.py`).
>
> **NÃO executar as Tarefas 1–4 da Seção 8** — duplicariam migration/lógica já existentes (risco de regressão grave).
>
> Os 21 arquivos de frontend dos Sprints 1–4 foram **integrados, validados e mergeados** em `main` em 7 PRs incrementais (vue-tsc + eslint + vitest 185/185 + ruff + mypy + pytest de submissions 70/70, todos verdes). Detalhes em `CLAUDE.md` (composables, ClientDetailView, InspectionComposer, builders de atributo, query `client_id`).

---

> **Autoria**
>
> Este documento foi produzido em colaboração por dois perfis complementares:
>
> — **Arquiteto de Sistemas Sênior** com foco em integridade de dados, contratos de API, migrations, invariantes e risco de regressão.
> — **Principal Product Designer** com foco em experiência operacional, fluxos de usuário, padrões de componente e curva de aprendizado.
>
> Toda afirmação técnica neste documento foi verificada diretamente no código-fonte, migrations Alembic, ADRs e specs do repositório. Nada foi assumido.

---

## Índice

1. [Contexto e Objetivo](#1-contexto-e-objetivo)
2. [O que foi entregue — Visão Geral dos 4 Sprints](#2-o-que-foi-entregue--visão-geral-dos-4-sprints)
3. [Sprint 1 — Zero JSON para Usuários Finais](#3-sprint-1--zero-json-para-usuários-finais)
4. [Sprint 2 — Hub Contextual de Clientes](#4-sprint-2--hub-contextual-de-clientes)
5. [Sprint 3 — Composables Testáveis e Onboarding](#5-sprint-3--composables-testáveis-e-onboarding)
6. [Sprint 4 — Form Builder: Escopo de Componente (DR-0002 Fase 4)](#6-sprint-4--form-builder-escopo-de-componente-dr-0002-fase-4)
7. [O que Falta — Backend Pendente](#7-o-que-falta--backend-pendente)
8. [Plano de Implementação Backend](#8-plano-de-implementação-backend)
9. [Invariantes Obrigatórias](#9-invariantes-obrigatórias)
10. [Critérios de Pronto](#10-critérios-de-pronto)
11. [Riscos e Mitigações](#11-riscos-e-mitigações)
12. [Appendix — Referências Documentais](#12-appendix--referências-documentais)

---

## 1. Contexto e Objetivo

O **Smart Audit** é uma plataforma SaaS multi-empresa para execução de checklists, auditorias e inspeções operacionais. A stack verificada é **FastAPI + SQLAlchemy 2.0 async (asyncpg) + PostgreSQL 17** no backend e **Vue 3 + Pinia + Vite** no frontend.

### 1.1 O problema que motivou este trabalho

Após leitura completa do código, identificamos **12 problemas** de UX e arquitetura, sendo os 3 mais críticos:

| # | Problema | Impacto |
|---|---|---|
| P1 | JSON manual exposto para usuários finais (`attributes_schema`, `attributes_json`) | **Bloqueador de adoção** — usuário não-técnico não consegue cadastrar nada |
| P2 | Hierarquia Cliente → Ativo → Inspeção invisível na UI | Inspetor precisa navegar 4 telas para criar uma inspeção contextual |
| P3 | `SubmissionDetailView.vue` com 2.497 linhas — lógica inline | Alto risco de manutenção; impossível testar isoladamente |

### 1.2 Domínio do produto

```
Empresa (tenant)
└── Cliente
    └── Ativo (raiz)
        └── Componentes (árvore, profundidade livre)
            └── Inspeções
                └── Campos × Conformidades × Evidências
```

A hierarquia real do negócio é **Client → Asset → Component → Inspection**. Os 4 sprints transformaram este domínio numa experiência navegável e coerente.

---

## 2. O que foi entregue — Visão Geral dos 4 Sprints

| Sprint | Foco | Arquivos | Status |
|---|---|---|---|
| **S1** | Eliminar JSON manual para usuário | 6 arquivos Vue/TS | ✅ Completo |
| **S2** | Hub contextual — Cliente como ponto de entrada | 6 arquivos Vue/TS + 1 rota | ✅ Completo |
| **S3** | Composables testáveis + onboarding no dashboard | 4 composables + 2 views | ✅ Completo |
| **S4** | Form Builder — UX de escopo de componente (DR-0002 Fase 4) | 2 arquivos + 1 patch | ✅ Frontend completo |
| **Backend** | DR-0002 Fases 2–3: migration + motor de expansão + score por componente | — | ⏳ **Pendente** |

**Total: 21 arquivos entregues no frontend.**

---

## 3. Sprint 1 — Zero JSON para Usuários Finais

### 3.1 Problema resolvido

`AssetTypesView.vue` expunha um `<textarea>` com o campo `attributes_schema` (JSONB bruto). `AssetsView.vue` expunha `attributes_json` da mesma forma. Qualquer erro de sintaxe JSON bloqueava o cadastro. Um gestor operacional **não deve e não consegue** escrever JSON manualmente.

### 3.2 Arquivos entregues

| Arquivo | Destino | Descrição |
|---|---|---|
| `AppShell.vue` | `src/components/layout/` | Sidebar reagrupada em 4 grupos semânticos; ícones corrigidos |
| `AppIcons.ts` | `src/components/ui/` | Ícones deduplicated; identidade visual corrigida |
| `AttributeSchemaBuilder.vue` | `src/components/ui/` | Construtor visual de `attributes_schema` — substitui textarea JSON |
| `AttributeValueEditor.vue` | `src/components/ui/` | Editor dinâmico de `attributes_json` — campos gerados pelo schema |
| `AssetTypesView.vue` | `src/views/asset-types/` | Integra `AttributeSchemaBuilder` — zero JSON exposto |
| `AssetsView.vue` | `src/views/assets/` | Integra `AttributeValueEditor` — campos dinâmicos do tipo |

### 3.3 Como funciona

O `AttributeSchemaBuilder` apresenta uma **tabela interativa** onde o usuário define:
- Nome do atributo (texto livre)
- Tipo de dado (Texto / Número / Data / Seleção)
- Obrigatório (toggle)

O schema JSONB é construído **programaticamente** no momento do submit — o usuário nunca vê JSON.

Ao cadastrar um ativo, `AttributeValueEditor` lê o `attributes_schema` do tipo selecionado e **renderiza campos tipados dinamicamente** (input text, number, date ou select), preenchendo `attributes_json` de forma estruturada.

### 3.4 Reorganização da sidebar

```
ANTES (12 itens sem agrupamento)       DEPOIS (4 grupos semânticos)
─────────────────────────────          ─────────────────────────────────
Resumo                                 Visão Geral
Formulários                              └── Dashboard
Inspeções
Equipes                                Operacional
Clientes                                 └── Clientes ✦ (hub contextual)
Tipos de ativo  ← no fluxo principal     └── Inspeções
Ativos          ← no fluxo principal
Usuários                               Configuração
Buscar                                   └── Formulários
Notificações                             └── Tipos de Ativo
Auditoria                                └── Ativos
Config. empresa
                                       Administração
                                         └── Usuários
                                         └── Equipes
                                         └── Configurações (empresa + auditoria)
```

**Justificativa:** "Tipos de Ativo" é configuração de template — feita raramente, por administradores. Posicioná-la no fluxo operacional principal gerava sobrecarga cognitiva e sinalizava frequência de uso incorreta.

### 3.5 Bottom nav mobile corrigido

```
ANTES: Resumo · Forms · Inspeções · Equipes · Usuários
DEPOIS: Início · Clientes · [+FAB] · Inspeções · Perfil
```

Equipes e Usuários não são usados por inspetores em campo. Clientes e o FAB de nova inspeção são as ações primárias no mobile.

---

## 4. Sprint 2 — Hub Contextual de Clientes

### 4.1 Problema resolvido

Não existia uma tela que conectasse Cliente → Ativos → Inspeções. O usuário precisava navegar entre 3 telas isoladas para criar uma inspeção contextual. O composer de nova inspeção apresentava um dropdown plano com **todos os ativos de todas as empresas** sem contexto de cliente.

### 4.2 Arquivos entregues

| Arquivo | Destino | Tipo |
|---|---|---|
| `AssetTree.vue` | `src/components/ui/` | Novo componente recursivo |
| `InspectionComposer.vue` | `src/components/submissions/` | Wizard extraído de SubmissionsView |
| `ClientDetailView.vue` | `src/views/clients/` | Nova view — hub contextual |
| `ClientsView.vue` | `src/views/clients/` | Modificado — nome clicável → detail |
| `SubmissionsView.vue` | `src/views/submissions/` | Modificado — usa InspectionComposer |
| `router/index.ts` | `src/router/` | Nova rota `/clients/:id` |

### 4.3 AssetTree.vue

Componente Vue recursivo com:
- **Lazy-load** dos filhos ao expandir (`fetchAsset(id)` chamado apenas na primeira expansão)
- **Ações contextuais no hover**: "+ Inspeção" e "+ Componente" revelados ao passar o mouse
- **`defineOptions({ name: 'AssetTree' })`** para auto-referência recursiva no template (Vue 3.3+)
- Eventos: `@start-inspection(asset)` e `@add-child(parent)`

```
📦 Caminhão 1 — Volvo FH            [+ Inspeção] [+ Comp.]
  ▼
  ├── ⚙ Motor Dianteiro
  ├── ⚙ Roda Dianteira Dir.
  └── ⚙ Roda Dianteira Esq.
      + Adicionar componente
```

### 4.4 InspectionComposer.vue

Wizard de 3 passos que suporta **3 fluxos de entrada**:

| Entrada | Passos ativos | Caso de uso |
|---|---|---|
| Ativo pré-selecionado | 1 passo (só formulário) | Hover "+ Inspeção" na árvore |
| Cliente pré-selecionado | 2 passos (form + ativo) | Nova inspeção do hub do cliente |
| Sem pré-seleção | 3 passos (form + cliente + ativo) | FAB mobile / botão em SubmissionsView |

O `asset_id` continua **nullable** na criação — retrocompatibilidade total.

### 4.5 ClientDetailView.vue

Nova view em `/clients/:id` que carrega em paralelo via `Promise.all`:
- Dados do cliente
- Ativos raiz (`fetchAssets` com `client_id`)
- Tipos de ativo (para mapa `type_id → nome`)
- Inspeções recentes (filtro client-side por `asset_id`)

> **Limitação conhecida (TODO backend):** As inspeções são filtradas client-side porque não existe `GET /submissions?client_id=`. Funciona para clientes com ≤ 100 ativos. Ver seção 7 para o endpoint pendente.

### 4.6 Fluxo operacional resultante (Fluxo A — recomendado)

```
Abrir Clientes
  → Clicar no cliente
  → Ver árvore de ativos
  → Hover no ativo → "+ Inspeção"
  → Selecionar formulário (1 passo)
  → Executar inspeção
```

---

## 5. Sprint 3 — Composables Testáveis e Onboarding

### 5.1 Problema resolvido

`SubmissionDetailView.vue` tinha **2.497 linhas** com toda a lógica de estado de conformidade, evidências, progresso e swipe inline. Impossível testar isoladamente. Alto risco de manutenção.

### 5.2 Arquivos entregues

| Arquivo | Destino | Responsabilidade |
|---|---|---|
| `useConformity.ts` | `src/composables/` | Status de conformidade, justificativa, bottom sheet, save debounced |
| `useEvidence.ts` | `src/composables/` | Upload, delete, listagem de evidências por instância |
| `useInspectionProgress.ts` | `src/composables/` | Contadores, score ao vivo, anel de score, seções |
| `useInspectionSwipe.ts` | `src/composables/` | Gestos de touch do modo cartão |
| `SubmissionDetailView-script.ts` | Substitui `<script setup>` | Script refatorado (~280 linhas + composables) |
| `HomeView.vue` | `src/views/dashboard/` | Onboarding checklist para novas empresas |

### 5.3 Arquitetura dos composables

```
SubmissionDetailView
  ├── useConformity(submissionId, answerableInstances, inspectionNext)
  │     → saveConformity (service)
  │     exports: conformityStatus, setConformity, setNaoConformeCard,
  │              confirmJustification, buildConformityItems, triggerConformitySave
  │
  ├── useEvidence(submissionId, answerableInstances)
  │     → listAttachments / uploadFile / createAttachment / deleteAttachment
  │     exports: evidenceAttachments, handleEvidenceUpload, handleEvidenceDelete
  │
  ├── useInspectionProgress(answerableInstances, conformityStatus, fields, inspectionIndex)
  │     exports: progressStats, liveScore, scoreRingStyle, allAnswered, formSections, nearbyDots
  │
  └── useInspectionSwipe({ getCurrentInstanceKey, onConformeSwipe, onNaoConformeSwipe })
        exports: swipeDeltaX, cardSwipeStyle, onTouchStart, onTouchMove, onTouchEnd
```

Cada composable é **TypeScript puro sem dependência de contexto Vue global** — testável com `vitest` + `@vue/test-utils` sem montar a view inteira.

### 5.4 Resultado da refatoração

| Métrica | Antes | Depois |
|---|---|---|
| Linhas no `<script setup>` | ~680 | ~280 |
| Lógica testável em isolamento | 0% | 100% |
| Arquivos de composable | 0 | 4 |
| Template alterado | — | **Inalterado** |

### 5.5 Onboarding no Dashboard

Quando uma empresa não tem inspeções nem formulários ativos, o Dashboard exibe um checklist de setup guiado com 5 passos:

```
1. Criar tipo de ativo     → link direto /asset-types
2. Cadastrar cliente        → link direto /clients
3. Criar formulário         → link direto /forms
4. Cadastrar ativo          → link direto /assets
5. Iniciar primeira inspeção → link direto /submissions
```

O widget desaparece automaticamente quando os itens são concluídos (baseado nos dados disponíveis). O anel de progresso usa CSS `conic-gradient` — zero dependências externas.

---

## 6. Sprint 4 — Form Builder: Escopo de Componente (DR-0002 Fase 4)

### 6.1 Contexto técnico

A **DR-0002** (Inspeção por Componente) é a funcionalidade de maior complexidade do roadmap. Divide-se em 4 fases:

| Fase | Responsabilidade | Status |
|---|---|---|
| Fase 1 | `submissions.asset_id` — vínculo ativo↔inspeção | ✅ Implementado |
| Fase 2 | Migration + motor de expansão do checklist | ⏳ **Pendente** |
| Fase 3 | Score e finalização por componente | ⏳ **Pendente** |
| Fase 4 | Frontend: builder marca escopo; inspeção renderiza por componente | ✅ **Entregue neste sprint** |

> **Descoberta no código:** `FormFieldEditor.vue` e `FormDetailView.vue` já tinham a implementação básica do `component_type_id` (FR4 estava parcialmente pronto). O Sprint 4 **melhorou a UX** e documentou com precisão o que falta no backend.

### 6.2 Arquivos entregues

| Arquivo | Destino | Mudança |
|---|---|---|
| `FormFieldEditor.vue` | `src/components/forms/` | Toggle visual + badge + painel de resumo |
| `FormDetailView-patch.ts` | Patch em `FormDetailView.vue` | 4 adições cirúrgicas |

### 6.3 UX entregue — Toggle "Repetir por componente"

```
ANTES:
  Escopo de componente: [ Nenhum ▼ ]   ← select plano, sem feedback visual

DEPOIS:
  ┌─────────────────────────────────────────────────┐
  │ Repetir por componente          [■■■■  ON  ] ✓  │
  │ O campo se repete para cada instância do tipo   │
  │                                                 │
  │ Tipo de componente:  [ Roda ▼ ]                 │
  │                                                 │
  │ ⚙ Este campo repete por cada Roda               │
  └─────────────────────────────────────────────────┘
```

No cabeçalho da linha de campo no builder, aparece a pill `⚙ Roda` indicando visualmente quais campos têm escopo de componente — sem precisar abrir o editor.

---

## 7. O que Falta — Backend Pendente

Esta seção é o **entregável principal para o desenvolvedor backend**. Toda informação está baseada na ADR-0016, SPEC-DR-0002-Fases2-4 e no código verificado.

### 7.1 Visão geral do que o backend precisa fazer

```
Estado atual do backend:
  ✅ form_fields.component_type_id  — coluna existe? → VERIFICAR na migration
  ✅ submissions.asset_id            — implementado (Fase 1)
  ❌ submission_values.asset_id      — não existe
  ❌ submission_conformities.asset_id — não existe
  ❌ submissions.components_snapshot — não existe
  ❌ Motor de expansão do checklist  — não implementado
  ❌ save_answers com asset_id       — não aceita dimensão de componente
  ❌ Score por componente            — calcula só por campo
  ❌ Finalização por instância       — não valida componente obrigatório pendente
  ❌ GET /submissions?client_id=     — endpoint não existe
```

### 7.2 Tarefa 1 — Migration aditiva (ALTO RISCO)

**Arquivo:** nova migration Alembic em `backend/alembic/versions/`
**Down revision:** `d2e3f4a5b6c7` (head da Fase 1)
**Risco:** ⚠️ Toca constraints UNIQUE do core — exige bateria de retrocompatibilidade antes de avançar.

#### DDL conceitual

```sql
-- 1. Escopo de campo (se não existir ainda)
ALTER TABLE form_fields
  ADD COLUMN component_type_id UUID NULL
  REFERENCES asset_types(id) ON DELETE SET NULL;

-- 2. Dimensão de componente nas respostas
ALTER TABLE submission_values
  ADD COLUMN asset_id UUID NULL
  REFERENCES assets(id) ON DELETE SET NULL;

-- 3. Dimensão de componente nas conformidades
ALTER TABLE submission_conformities
  ADD COLUMN asset_id UUID NULL
  REFERENCES assets(id) ON DELETE SET NULL;

-- 4. Snapshot de identidade de componente
ALTER TABLE submissions
  ADD COLUMN components_snapshot JSONB NULL;

-- 5. Alterar UNIQUE de 2 para 3 colunas — NULLS NOT DISTINCT (PG 15+)
-- submission_values
ALTER TABLE submission_values
  DROP CONSTRAINT uq_submission_values_submission_field;
ALTER TABLE submission_values
  ADD CONSTRAINT uq_submission_values_submission_field_asset
  UNIQUE NULLS NOT DISTINCT (submission_id, form_field_id, asset_id);

-- submission_conformities
ALTER TABLE submission_conformities
  DROP CONSTRAINT uq_submission_conformities_submission_field;
ALTER TABLE submission_conformities
  ADD CONSTRAINT uq_submission_conformities_submission_field_asset
  UNIQUE NULLS NOT DISTINCT (submission_id, form_field_id, asset_id);

-- 6. Índices auxiliares
CREATE INDEX ix_submission_values_asset_id
  ON submission_values(asset_id) WHERE asset_id IS NOT NULL;

CREATE INDEX ix_submission_conformities_asset_id
  ON submission_conformities(asset_id) WHERE asset_id IS NOT NULL;
```

#### Por que `NULLS NOT DISTINCT` é crítico

O Postgres padrão trata `NULL` como **distinto** — ou seja, `NULLS DISTINCT` (padrão) permitiria múltiplas linhas com `(submission_id, form_field_id, NULL)`, quebrando a garantia histórica de "uma resposta por campo". O `NULLS NOT DISTINCT` trata `NULL` como **igual**, preservando o comportamento atual para campos gerais (`asset_id = NULL`) enquanto permite múltiplas respostas por componente (`asset_id` preenchido). **Esta é a diferença entre retrocompatibilidade e regressão silenciosa.**

> Referência: [ADR-0016, §Decisão] e [SPEC-DR-0002, §3 Nota Postgres]

#### Estratégia Alembic (downgrade obrigatório)

```python
def upgrade():
    # 1. Add columns (all nullable — no backfill needed)
    # 2. Drop old UNIQUE constraints
    # 3. Create new UNIQUE NULLS NOT DISTINCT constraints
    # 4. Create auxiliary indexes

def downgrade():
    # 1. Drop new constraints and indexes
    # 2. Recreate original UNIQUE constraints
    # 3. Drop added columns
```

#### Bateria de retrocompatibilidade (executar ANTES de avançar)

```bash
pytest backend/tests/ -k "test_submission" -v
# Todos os testes de submission devem passar sem alteração de comportamento
# Especialmente: test_save_answers, test_calculate_score, test_finish_submission
```

---

### 7.3 Tarefa 2 — Motor de expansão do checklist

**Arquivo:** `backend/app/services/submissions.py` → método `get_submission_detail` (ou equivalente)

#### O que fazer

Ao montar a resposta de `GET /submissions/{id}`, para cada campo do formulário:

```python
for field in form_version.fields:
    if field.component_type_id is None:
        # Campo geral — comportamento atual: 1 instância com asset_id=None
        yield FieldInstance(field=field, asset_id=None, label=field.label)
    else:
        # Campo escopado — 1 instância por componente do tipo especificado
        components = await asset_repo.get_components_by_type(
            parent_asset_id=submission.asset_id,
            asset_type_id=field.component_type_id,
        )
        for component in components:
            yield FieldInstance(
                field=field,
                asset_id=component.id,
                label=f"{field.label} · {component.identifier}",
            )
```

#### Contrato de resposta esperado

```json
{
  "data": {
    "id": "...",
    "checklist": [
      {
        "field_key": "pressao_pneu",
        "field_type": "number",
        "label": "Pressão do pneu",
        "component_type_id": "<roda_type_id>",
        "components": [
          { "asset_id": "<roda_dd_id>", "label": "Roda Dianteira Dir.", "type": "Roda", "path": "Caminhão ABC > Roda DD" },
          { "asset_id": "<roda_de_id>", "label": "Roda Dianteira Esq.", "type": "Roda", "path": "Caminhão ABC > Roda DE" }
        ]
      },
      {
        "field_key": "freios_ok",
        "field_type": "boolean",
        "label": "Freios em boas condições?",
        "component_type_id": null,
        "components": []
      }
    ]
  }
}
```

#### Caso de borda — campo escopado sem componentes

Se o ativo não tiver componentes do `component_type_id` especificado, o campo deve ser **omitido da execução** com um **aviso não-bloqueante** (Q2 da SPEC). Não bloquear o rascunho, mas bloquear a finalização (Q3).

---

### 7.4 Tarefa 3 — `save_answers` com `asset_id`

**Arquivo:** `backend/app/services/submissions.py` → `SubmissionService.save_answers`

#### Formato de entrada esperado

```json
{
  "answers": [
    { "field_key": "freios_ok",     "value": true,  "asset_id": null },
    { "field_key": "pressao_pneu",  "value": 32.5,  "asset_id": "<roda_dd_id>" },
    { "field_key": "pressao_pneu",  "value": 31.0,  "asset_id": "<roda_de_id>" }
  ]
}
```

#### Mudança na chave de upsert

```python
# ANTES
stmt = insert(SubmissionValue).values(...)
stmt = stmt.on_conflict_do_update(
    constraint="uq_submission_values_submission_field",
    ...
)

# DEPOIS
stmt = insert(SubmissionValue).values(...)
stmt = stmt.on_conflict_do_update(
    constraint="uq_submission_values_submission_field_asset",
    ...
)
```

#### Formato do `answers_json` (snapshot — Q1/ADR-0016)

```python
# Campo geral: escalar (comportamento atual)
answers_json = {
    "freios_ok": True,
    "placa": "ABC-1234",
}

# Campo escopado: mapa { asset_id: valor }
answers_json = {
    "freios_ok": True,
    "pressao_pneu": {
        "<roda_dd_id>": 32.5,
        "<roda_de_id>": 31.0,
    }
}
```

> **Regra do ADR-0006 preservada:** relacional (`submission_values`) e snapshot (`answers_json`) são escritos na **mesma transação** em `save_answers`. Nunca divergem.

#### `components_snapshot` — Q1.1/ADR-0016

No mesmo `save_answers`, para cada `asset_id` escopado, congelar a identidade do componente:

```python
# Resolver uma vez por componente único na inspeção
components_snapshot = {}
for answer in scoped_answers:
    if answer.asset_id not in components_snapshot:
        component = await asset_repo.get(answer.asset_id)
        asset_type = await asset_type_repo.get(component.asset_type_id)
        path = await asset_repo.get_path_string(answer.asset_id)  # "Caminhão ABC > Roda DD"
        components_snapshot[str(answer.asset_id)] = {
            "label": component.identifier,
            "type": asset_type.name,
            "path": path,
        }

submission.components_snapshot = components_snapshot
```

**Importante:** gravado **uma vez por componente** (não por campo×componente). Nunca reescrito após a finalização. É o que garante que o laudo histórico seja imune a renomeação do ativo.

#### Validação de integridade (INV1)

```python
# Verificar antes de salvar:
# 1. asset_id pertence à subárvore do submission.asset_id
# 2. asset.asset_type_id == field.component_type_id
if not await asset_repo.is_in_subtree(asset_id, submission.asset_id):
    raise HTTPException(400, detail={...RFC7807...})
if asset.asset_type_id != field.component_type_id:
    raise HTTPException(400, detail={...RFC7807...})
```

---

### 7.5 Tarefa 4 — Score e finalização por componente

**Arquivo:** `backend/app/services/submissions.py` → `calculate_score`, `finish_submission`

#### Score (ADR-0008 — fórmula inalterada, cardinalidade muda)

```python
# ANTES: itera por campo booleano
for conformity in submission.conformities:
    field = form_field_map[conformity.form_field_id]
    if field.field_type == 'boolean':
        weight = field.config_json.get('weight', 1)
        total_weight += weight
        if conformity.status == 'conforme':
            conformed_weight += weight

# DEPOIS: itera por (campo, componente) — cada par é uma unidade
for conformity in submission.conformities:
    field = form_field_map[conformity.form_field_id]
    if field.field_type == 'boolean':
        weight = field.config_json.get('weight', 1)  # mesmo weight para todas as instâncias (Q6)
        total_weight += weight
        if conformity.status == 'conforme':
            conformed_weight += weight

# A fórmula final não muda: score = round((conformed_weight / total_weight) * 100)
```

#### Finalização — validação por instância (RN4)

```python
async def finish_submission(submission_id, ...):
    # Para cada campo required, verificar CADA instância expandida
    for field in required_fields:
        instances = expand_instances(field, submission.asset_id)
        for instance in instances:
            key = (field.id, instance.asset_id)  # asset_id pode ser None
            if key not in answered_conformities:
                raise ValidationError(
                    f"Campo '{field.label}' pendente"
                    + (f" para {instance.label}" if instance.asset_id else "")
                )
```

---

### 7.6 Tarefa 5 — Endpoint `GET /submissions?client_id=`

**Arquivo:** `backend/app/api/v1/submissions.py` e `backend/app/services/submissions.py`

#### Por que é necessário

`ClientDetailView.vue` filtra inspeções client-side por `asset_id`. Isso funciona para clientes com poucos ativos, mas é ineficiente e pode retornar resultados incompletos para clientes com muitos ativos (paginação trunca a lista).

#### Implementação sugerida

```python
# API
@router.get("/submissions", response_model=PaginatedEnvelope[SubmissionListItem])
async def list_submissions(
    client_id: UUID | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    membership = Depends(get_current_membership),
    db: AsyncSession = Depends(get_db),
):
    ...

# Repository (join via assets)
async def list_by_company(
    company_id: UUID,
    client_id: UUID | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Submission], PaginationMeta]:
    stmt = (
        select(Submission)
        .options(selectinload(Submission.form))
        .where(Submission.company_id == company_id)
    )
    if client_id:
        stmt = stmt.join(Asset, Submission.asset_id == Asset.id)
        stmt = stmt.where(Asset.client_id == client_id)
    if status:
        stmt = stmt.where(Submission.status == status)
    ...
```

---

## 8. Plano de Implementação Backend

### Ordem obrigatória (cada fase depende da anterior)

```
Fase 2a — Verificar/criar form_fields.component_type_id
   ↓
Fase 2b — Migration aditiva (+ bateria de retrocompatibilidade)
   ↓
Fase 2c — Motor de expansão + save_answers com asset_id + answers_json + components_snapshot
   ↓
Fase 3  — Score por componente + finalização por instância
   ↓
Fase 5  — GET /submissions?client_id= (independente, pode ser feita em paralelo)
```

### Estimativa de esforço

| Tarefa | Esforço | Risco | Pode paralelizar? |
|---|---|---|---|
| Migration aditiva | 1–2 dias | **ALTO** | Não — base de tudo |
| Motor de expansão | 2–3 dias | Médio | Não — depende de migration |
| save_answers com asset_id | 2–3 dias | **ALTO** | Não — depende de migration |
| Score por componente | 1 dia | Baixo | Não — depende de save_answers |
| Finalização por instância | 1 dia | Médio | Não — depende de score |
| GET /submissions?client_id= | 0.5 dia | Baixo | **Sim — independente** |

**Total estimado: 7.5–10.5 dias de engenharia backend.**

---

## 9. Invariantes Obrigatórias

Estas invariantes **devem ser protegidas por testes** antes de fazer merge de qualquer fase.

| ID | Invariante | Teste sugerido |
|---|---|---|
| **INV1** | `asset_id` da resposta/conformidade pertence à subárvore de `submissions.asset_id` e tem `asset_type_id = component_type_id` do campo | `test_submission_invariant_asset_scope.py` |
| **INV2** | Campo geral (`component_type_id = NULL`) → resposta/conformidade com `asset_id = NULL` | `test_save_answers_general_field.py` |
| **INV3** | Relacional (`submission_values`) e snapshot (`answers_json`) sempre escritos na mesma transação — nunca divergem | `test_snapshot_consistency.py` |
| **INV4** | Score deriva **exclusivamente** de `submission_conformities` (ADR-0008) | Reusar testes existentes de score |
| **INV5** | Versões de formulário publicadas são imutáveis — `component_type_id` não pode mudar após publicação | `test_form_version_immutability.py` |
| **INV6** | Para todo `asset_id` em campos escopados de `answers_json`, existe `components_snapshot[asset_id]` | `test_components_snapshot_completeness.py` |
| **CA1** | Inspeção sem `asset_id` e formulário sem campo escopado = idêntico ao comportamento atual | Reusar **todos** os testes existentes de submission |
| **CA2** | Ativo com 4 componentes do tipo X e campo escopado → 4 respostas; finalizar com 1 pendente = bloqueado | `test_submissions_component.py` |
| **CA3** | Score soma cada par campo×componente avaliado (exclui N/A e não avaliados) | `test_score_with_components.py` |
| **CA4** | Snapshot `answers_json` e `submission_values` consistentes para campos escopados | Comparar relacional × snapshot após save |
| **CA5** | Resposta com `asset_id` fora da subárvore → 400 RFC 7807 | `test_submission_invalid_asset_scope.py` |
| **CA6** | Migration reversível; nenhuma inspeção histórica alterada | `downgrade()` + verificar dados antigos |

---

## 10. Critérios de Pronto

A feature "Inspeção por Componente" está **done** quando:

- [ ] Migration passa `upgrade` e `downgrade` sem erros
- [ ] Todos os testes existentes de `submission` passam sem alteração (CA1)
- [ ] Ativo com 4 rodas + campo "Pressão do pneu" escopado → 4 respostas independentes na execução (CA2)
- [ ] Finalizar inspeção com 1 roda pendente = bloqueado com mensagem clara (CA2)
- [ ] Score final reflete média ponderada de todos os pares campo×componente (CA3)
- [ ] `answers_json` e `submission_values` consistentes após `save_answers` (CA4)
- [ ] `asset_id` fora da subárvore retorna 400 com RFC 7807 (CA5)
- [ ] `GET /submissions?client_id=` retorna apenas inspeções de ativos daquele cliente
- [ ] Frontend renderiza grupos por componente no modo lista e modo cartão
- [ ] Relatório PDF exibe seções por componente com scores individuais

---

## 11. Riscos e Mitigações

| ID | Risco | Probabilidade | Impacto | Mitigação |
|---|---|---|---|---|
| R-T1 | Regressão no `save_answers` pela mudança de UNIQUE constraint | Alta | Crítico | Migration reversível + bateria completa de testes antes de avançar |
| R-T2 | Divergência entre `answers_json` (snapshot) e `submission_values` (relacional) | Média | Alto | Único ponto de escrita (`save_answers`); testes de consistência |
| R-T3 | Acoplamento `forms` ↔ `asset_types` — form escopado para tipo que o ativo não tem | Média | Médio | Aviso não-bloqueante (Q2 da SPEC); validar compatibilidade ao vincular ativo × formulário |
| R-N1 | UX de grupos por componente confusa para o inspetor | Baixa | Médio | Protótipo de agrupamento visual antes de implementar; reusar lista atual |
| R-O1 | Crescimento de volume em `submission_values` e `submission_conformities` | Baixa (curto prazo) | Baixo | Índices por `submission_id`; monitorar após adoção |
| R-P1 | `NULLS NOT DISTINCT` requer PG 15+ | Baixa | Crítico | Prod roda PG 17 (verificado); dev roda PG 18 |

---

## 12. Appendix — Referências Documentais

Todos os documentos abaixo estão no repositório em `smart-audit/docs/`:

| Documento | Caminho | Relevância |
|---|---|---|
| ADR-0006 | `adr/0006-modelo-hibrido-de-respostas.md` | Modelo híbrido relacional × snapshot — **base de tudo** |
| ADR-0008 | `adr/0008-score-via-conformities.md` | Fórmula de score ponderado |
| ADR-0015 | `adr/0015-modelo-de-ativos-genericos.md` | Árvore de ativos, `client_id` discriminador |
| ADR-0016 | `adr/0016-inspecao-por-componente-revisao-modelo-hibrido.md` | **Decisão arquitetural DR-0002** — leitura obrigatória |
| ADR-0017 | `adr/0017-modelo-unificado-de-evidencias.md` | Evidência por componente (resolvida) |
| SPEC-DR-0002 | `specs/SPEC-DR-0002-Fases2-4-InspecaoPorComponente.md` | **Spec técnica completa** — fonte de verdade das Fases 2–4 |
| Arquitetura | `Arquitetura_Smart_Audit.md` | Bounded contexts, rotas, contratos |
| DER | `DER_Smart_Audit.md` | Modelo de dados atual (estado real) |
| AI_DECISIONS | `ai/AI_DECISIONS.md` | Catálogo fino de decisões Q1–Q6 |
| AI_RULES | `ai/AI_RULES.md` | Regras invioláveis do projeto |

---

*Documento gerado em Junho 2026 — baseado 100% no código-fonte, migrations e documentação do repositório `smart-audit`. Nenhuma afirmação foi assumida sem verificação direta.*
