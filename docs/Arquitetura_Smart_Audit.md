# Arquitetura do Sistema - Smart Audit

## 1. Visao geral

- Nome do sistema: Smart Audit
- Dominio: auditorias, checklists, inspecoes e evidencias operacionais
- Objetivo: substituir processos manuais por execucao rastreavel, versionada e multiempresa
- Modelo atual: SaaS multiempresa com empresa ativa definida por contexto

Perfis de acesso atualmente modelados:

- `OWNER`
- `ADMIN`
- `MANAGER`
- `INSPECTOR`
- `VIEWER`

Stack atual:

- Backend: FastAPI, SQLAlchemy async, Alembic, PostgreSQL, slowapi, fpdf2 — porta `8003`
- Frontend: Vue 3, Pinia, Vue Router, Tailwind CSS v4, Axios, Vitest, Playwright — porta `5174`
- Uploads: armazenamento local em disco

Baseline validado em `2026-05-31`:

- backend: `191 passed, 3 skipped`
- frontend Vitest (19 arquivos): `119 passed`
- frontend build: `npm run build` OK

## 2. Estado real do produto

O Smart Audit ja nao esta mais em fase apenas de fundacao. O estado atual do codigo mostra:

- autenticacao JWT funcional
- recuperacao de senha completa (forgot-password + reset via token com TTL de 1h)
- contexto de empresa ativa e selecao de empresa
- dashboard com metricas por periodo, grafico de score por formulario e sparkline de tendencia 30 dias
- CRUD de usuarios
- CRUD de equipes e membros
- formularios versionados com suporte a secoes, evidencias e configuracao avancada por campo
- campos de formulario configurados via `config_json`: peso, allow_na, opcoes de select
- tipos de campo: `boolean`, `text`, `number`, `select`, `date`, `section`
- detalhe de formulario e historico de versoes
- inspecoes com respostas tipadas e score ponderado por peso de campo
- suporte a resposta N/A em campos booleanos com `allow_na: true`
- modo de inspecao (card a card) e modo lista com carga progressiva (`load more`)
- barra de progresso e atalhos rapidos por secao na execucao da inspecao
- finalizacao de inspecao com calculo de score ponderado
- score_breakdown com contagem de conformes, nao conformes, sem resposta e N/A
- relatorio detalhado por inspecao com exportacao PDF profissional
- PDF inclui: bloco de score colorido, chips de breakdown, divisores de secao, linhas coloridas por resultado
- exportacao CSV de inspecoes com filtro de status
- evidencias anexadas por upload local (imagem, video, audio, PDF)
- busca em tempo real por formularios e inspecoes (`GET /search?q=`)
- perfil do usuario (nome, senha, empresas vinculadas)
- configuracoes da empresa (dados cadastrais, fuso horario, guard de role)
- notificacoes derivadas das inspecoes (sem tabela propria no banco)

## 3. Bounded contexts implementados

### Identidade e acesso

Responsavel por autenticacao, perfil, empresa ativa, memberships e recuperacao de senha.

Entidades principais:

- `users`
- `companies`
- `memberships`
- `password_reset_tokens`

Capacidades ativas:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/forgot-password` — gera token com TTL 1h, entrega via SMTP ou log
- `POST /api/v1/auth/reset-password` — valida token, troca senha, marca token como usado
- `GET /api/v1/me/companies`
- `GET /api/v1/me/context`
- `PATCH /api/v1/me`
- `GET /api/v1/me/stats` — retorna metricas por periodo com `score_by_form` e `score_trend`
- `GET /api/v1/me/notifications` — derivadas de submissions; retorna `read: bool` persistido
- `POST /api/v1/me/notifications/read` — marca uma notificacao como lida
- `POST /api/v1/me/notifications/read-all` — marca todas as notificacoes fornecidas como lidas
- `GET /api/v1/companies/me`
- `PATCH /api/v1/companies/me` (requer OWNER ou ADMIN)

### Formularios

Responsavel por templates versionados de checklist.

Entidades principais:

- `forms`
- `form_versions`
- `form_fields`

Capacidades ativas:

- listagem paginada
- criacao com campos tipados e configurados via `config_json`
- publicacao de nova versao (imutavel pos-publicacao)
- leitura de versao especifica
- historico de versoes
- importacao via CSV ou Excel (`POST /api/v1/forms/import`) — cria formulario com todos os campos a partir de arquivo

Configuracao de campo via `config_json`:

| Propriedade | Tipo | Campo aplicavel | Descricao |
|---|---|---|---|
| `weight` | `float` | `boolean` | Peso no calculo do score ponderado (default 1.0) |
| `allow_na` | `bool` | `boolean` | Habilita resposta N/A |
| `options` | `string[]` | `select` | Opcoes do dropdown |
Campo `instruction` em `form_fields`:

- coluna `instruction TEXT NULL` — texto livre explicando como executar a tarefa do campo
- editavel no formulario builder e preenchivel via importacao (coluna `instrucao` no arquivo)
- exibido na tela de inspecao abaixo do label do campo (card view e list view)

Tipos de campo suportados:

| Tipo | Armazenamento | Observacao |
|---|---|---|
| `boolean` | `value_boolean` | Aceita `true`, `false` ou `"na"` (com `allow_na: true`) |
| `text` | `value_text` | String livre |
| `number` | `value_number` | Float |
| `date` | `value_date` | ISO 8601 |
| `select` | `value_json` | `{ "option": "valor" }` |
| `section` | — | Divisor visual; nao gera `submission_value` |

**Tipos removidos**: `photo` (migration `a1b2c3d4e5f7`) e `evidence` (migration `b3c4d5e6f7a8`). Evidencia e agora uma capacidade de qualquer campo via modulo `attachments`.

### Inspecoes

Responsavel pela execucao do formulario, persistencia de respostas e score.

Entidades principais:

- `submissions`
- `submission_values`
- `submission_conformities`

Capacidades ativas:

- criacao de inspecao
- listagem com filtros (status, form_id, created_by)
- detalhe
- salvamento de respostas tipadas (todos os tipos de campo)
- resposta N/A em booleanos com `allow_na: true` (armazenada como `value_text = "na"`)
- avaliacao de conformidade por campo: `PUT /submissions/{id}/conformity` registra `conforme` ou `nao_conforme` em `submission_conformities`
- finalizacao com validacao de campos obrigatorios respondidos
- calculo de score ponderado baseado em `submission_conformities` (campos N/A e sem conformidade sao excluidos)
- score_breakdown: `conformes`, `nao_conformes`, `sem_resposta`, `na_count`, `total_boolean`
- exportacao PDF individual com score profissional
- exportacao CSV da lista (com filtro de status)

Calculo de score:

```
score = sum(weight_i para conformes) / sum(weight_i para avaliados e nao N/A) * 100
```

A fonte do score e `submission_conformities`, nao `submission_values`. Campos sem avaliacao de conformidade e N/A nao entram no denominador.

### Evidencias

Responsavel por vincular metadados de arquivos a respostas de inspecao.

Entidade principal:

- `attachments`

Relacionamento: `attachments` vincula ao `submission_value` correspondente ao campo de evidencia.

### Uploads

Responsavel por receber arquivos e gravar em disco.

- nao existe modulo de dominio separado para uploads
- a logica fica encapsulada no router
- tipos permitidos: `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `video/mov`, `video/avi`, `audio/mpeg`, `audio/wav`, `audio/ogg`, `audio/m4a`, `application/pdf`
- limite: 10 MB

### Equipes

Responsavel por organizar usuarios em equipes dentro da empresa ativa.

Entidades principais:

- `teams`
- `team_members`

Capacidades ativas:

- CRUD de equipes
- adicionar membro
- remover membro

### Busca

Responsavel por consulta full-text simples sobre formularios e inspecoes da empresa.

Capacidades ativas:

- `GET /api/v1/search?q=` (minimo 2 caracteres, maximo 100)
- retorna `{ forms: [...], submissions: [...] }` filtrados por `company_id`
- busca por nome de formulario (ILIKE)

### Visao analitica e notificacoes

A visao analitica e derivada de `submissions`. Nao existe tabela propria de notificacoes.

Capacidades ativas:

- metricas em `/api/v1/me/stats` com filtro por periodo `7d | 30d | 90d | all`
- `score_by_form`: media de score por formulario (ultimos 10, ordem crescente — piores primeiro)
- `score_trend`: media diaria de score dos ultimos 30 dias
- notificacoes em `/api/v1/me/notifications`: derivadas em tempo real das submissions
  - inspecoes `in_progress` ha mais de 24h geram alerta `pending`
  - `completed` com score < 80% geram alerta `low_score`
  - `completed` com score >= 90% geram alerta `excellent`

### Relatorio e exportacao PDF

Responsavel por gerar o relatorio visual de uma inspecao em PDF.

Capacidades ativas:

- `GET /api/v1/submissions/{id}/export` — download do PDF
- `GET /api/v1/submissions/{id}/export?inline=true` — abertura inline no browser
- conteudo do PDF: bloco de score colorido (verde/amarelo/vermelho), chips de breakdown, tabela de respostas com resultado de conformidade, divisores de secao, rodape com contagem de campos

Restricoes:

- PDF gerado com fpdf2 usando fonte Helvetica (Latin-1); caracteres fora de Latin-1 nao sao suportados

## 4. Arquitetura backend

Padrao principal:

`api -> service -> repository -> db`

### Camadas

`api/`

- routers FastAPI
- injecao de dependencias
- serializacao HTTP
- sem regra de negocio relevante

`modules/*/service.py`

- regras de negocio
- validacoes de dominio
- orquestracao transacional
- `db.commit()` acontece aqui

`modules/*/repository.py`

- queries
- persistencia
- `db.flush()` e helpers de repositorio base
- nenhuma responsabilidade de commit

`db/models/`

- entidades ORM
- relacionamentos
- constraints e indexes refletem o dominio

`core/`

- configuracao
- seguranca
- rate limiting
- paginacao
- envelopes padrao
- tratamento de erro

### Padroes realmente aplicados

- Layered Architecture
- Repository Pattern
- Service Layer
- Multi-tenancy por contexto de membership
- RFC 7807 para respostas de erro
- Envelopes `{ data, meta }`
- Paginacao padronizada com `PageMeta`
- AsyncSession em todo o backend

### Pontos concretos do codigo

- sessao async: [backend/app/db/session.py](/c:/Projetos/smart-audit/backend/app/db/session.py)
- repositorio base: [backend/app/core/repositories.py](/c:/Projetos/smart-audit/backend/app/core/repositories.py)
- handlers de erro: [backend/app/core/errors.py](/c:/Projetos/smart-audit/backend/app/core/errors.py)
- envelopes: [backend/app/core/responses.py](/c:/Projetos/smart-audit/backend/app/core/responses.py)
- router principal: [backend/app/api/v1/router.py](/c:/Projetos/smart-audit/backend/app/api/v1/router.py)
- gerador PDF: [backend/app/modules/submissions/pdf.py](/c:/Projetos/smart-audit/backend/app/modules/submissions/pdf.py)

## 5. Arquitetura frontend

Organizacao principal:

- `router/`
- `stores/`
- `services/`
- `views/`
- `components/`
- `types/`

### Padroes realmente aplicados

- SPA com Vue Router
- stores Pinia por dominio
- axios centralizado em `services/api/http.ts`
- token e `company-id` em `localStorage`
- bootstrap de contexto no route guard
- sync do usuario autenticado apos refresh
- views majoritariamente finas

### Fluxo de bootstrap de sessao

1. o usuario faz login
2. o token e persistido
3. o `contextStore.bootstrap()` carrega empresas e contexto
4. o route guard sincroniza `context.user` em `authStore.user` quando necessario
5. o shell usa esse estado para renderizar sessao, empresa ativa e navegacao

Referencias:

- router: [frontend/src/router/index.ts](/c:/Projetos/smart-audit/frontend/src/router/index.ts)
- auth store: [frontend/src/stores/auth/auth.store.ts](/c:/Projetos/smart-audit/frontend/src/stores/auth/auth.store.ts)
- context store: [frontend/src/stores/context/context.store.ts](/c:/Projetos/smart-audit/frontend/src/stores/context/context.store.ts)
- app shell: [frontend/src/components/layout/AppShell.vue](/c:/Projetos/smart-audit/frontend/src/components/layout/AppShell.vue)

### Modo de inspecao

A view `SubmissionDetailView.vue` opera em tres modos mutuamente exclusivos:

- **Modo lista normal** (padrao, tambem para inspecoes concluidas): todos os campos em scroll; concluidas sao somente leitura
- **Modo inspecao — card** (`inspectionMode = true`, `viewMode = 'card'`): um campo por vez com gestos de swipe (esquerda = Nao conforme, direita = Conforme); disponivel apenas para inspecoes em andamento
- **Modo inspecao — lista** (`inspectionMode = true`, `viewMode = 'list'`): lista compacta dentro do fluxo de inspecao

Os dois modos lista usam o componente `InspectionFieldRow.vue` (prop `compact` distingue inspecao de leitura normal). O modo card permanece inline na view.

Computeds relevantes:

- `answerableFields`: campos respondiveis (exclui secoes)
- `progressPct`: percentual respondido dos campos respondiveis
- `formSections`: lista de secoes para atalhos rapidos de navegacao
- `liveScore`: score calculado em tempo real durante a inspecao (baseado em respostas boolean confirmadas)

## 6. Design system e front-end visual

O frontend atual ja incorporou boa parte do redesign em curso.

Base visual ativa:

- Tailwind CSS v4
- tokens CSS proprios em `style.css`
- fontes `Plus Jakarta Sans` e `DM Mono`
- shell dark sidebar + bottom nav mobile
- icones SVG centralizados

Classes CSS de inspecao:

- `.insp-card`, `.insp-meta`, `.insp-section`, `.insp-counter`, `.insp-nav` — modo inspecao
- `.insp-progress-bar`, `.insp-progress-fill` — barra de progresso
- `.section-jump-bar`, `.section-jump-chip` — atalhos de secao
- `.section-divider` — divisor visual de secao no modo lista

Classes CSS de dashboard:

- `.dash-chart-card`, `.dash-bar-row`, `.dash-bar-fill`, `.dash-bar-pct` — grafico de barras por formulario
- `.dash-sparkline`, `.dash-spark-labels` — sparkline de tendencia

Referencias:

- estilos base: [frontend/src/style.css](/c:/Projetos/smart-audit/frontend/src/style.css)
- icones: [frontend/src/components/ui/AppIcons.ts](/c:/Projetos/smart-audit/frontend/src/components/ui/AppIcons.ts)
- renderer de icone: [frontend/src/components/ui/SvgIcon.vue](/c:/Projetos/smart-audit/frontend/src/components/ui/SvgIcon.vue)

## 7. Modulos e rotas implementados

### Backend

Rotas agregadas hoje:

- `health`
- `auth` (login, me, forgot-password, reset-password)
- `companies`
- `me` (context, companies, stats com score_by_form/score_trend, notifications)
- `users`
- `forms` (CRUD, versoes, importacao via CSV/Excel)
- `submissions` (CRUD, answers, conformity, finish, export CSV, export PDF com `?inline`)
- `search`
- `teams`
- `attachments`
- `uploads`

### Frontend

Rotas de interface existentes hoje:

- `/login`
- `/forgot-password`
- `/reset-password` (recebe `?token=` na query string)
- `/select-company`
- `/` — dashboard com metricas, barras de score por formulario, sparkline de tendencia
- `/users`
- `/forms`
- `/forms/:formId` — editor com secoes, peso, allow_na, instrucao por campo
- `/forms/:formId/versions`
- `/submissions`
- `/submissions/:id` — execucao com modo inspecao e modo lista, progresso, atalhos de secao
- `/submissions/:id/report` — relatorio com botoes "Visualizar PDF" e "Baixar PDF"
- `/profile`
- `/company-settings`
- `/notifications`
- `/search`
- `/teams`

## 8. Contratos HTTP

### Sucesso

```json
{
  "data": {},
  "meta": {}
}
```

### Paginacao

```json
{
  "data": [],
  "meta": {
    "total": 0,
    "page": 1,
    "page_size": 20,
    "has_next": false,
    "total_pages": 0
  }
}
```

### Erro

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Recurso nao encontrado.",
  "instance": "/api/v1/forms/123"
}
```

Observacao: mensagens de erro do backend nao usam acentos para evitar problemas de encoding em logs.

### Resposta de stats (`GET /me/stats`)

```json
{
  "data": {
    "total_submissions": 42,
    "completed": 35,
    "in_progress": 7,
    "avg_score": 87.5,
    "recent": [...],
    "score_by_form": [
      { "form_id": "...", "form_name": "Checklist A", "avg_score": 72.3, "count": 5 }
    ],
    "score_trend": [
      { "date": "2026-05-01", "avg_score": 81.0 }
    ]
  }
}
```

## 9. Testes

### Backend

Estado validado em `2026-06-03`:

- `214 passed, 3 skipped` (backend)
- `27 passed` (unit — test_form_importer.py adicionado)

Cobertura atual:

| Arquivo | Tipo | Escopo |
|---|---|---|
| `test_auth.py` | integracao | login, JWT, me |
| `test_password_reset.py` | integracao | forgot/reset password |
| `test_forms.py` | integracao | CRUD formularios e versoes |
| `test_submissions.py` | integracao | fluxo principal, filtros, RBAC |
| `test_submissions_export.py` | integracao | CSV export, filtros, isolamento |
| `test_submissions_advanced.py` | integracao | PDF, N/A, pesos, stats, isolamento |
| `test_search.py` | integracao | busca full-text |
| `test_users.py` | integracao | CRUD usuarios |
| `test_teams.py` | integracao | CRUD equipes e membros |
| `test_companies.py` | integracao | configuracoes de empresa |
| `test_me.py` | integracao | context, stats, notificacoes |
| `test_uploads.py` | integracao | upload, validacao de tipo e tamanho |
| `test_attachments.py` | integracao | evidencias |
| `test_form_service.py` | unidade | validate_fields (todos os tipos) |
| `test_submission_service.py` | unidade | normalize_value, calculate_score (ponderado via conformities), score_breakdown (N/A), extract_value, parse_period_start, PDF |
| `test_form_importer.py` | unidade | parse_csv, parse_excel, parse_import_file (27 casos) |

Casos cobertos em `test_submissions_advanced.py`:

- exportacao PDF: content-type, `?inline`, secoes + N/A, 404, auth guard
- stats: `score_by_form` e `score_trend` presentes, filtro por periodo
- N/A boolean: aceitacao, score_breakdown.na_count, exclusao do denominador do score
- score ponderado via conformities: peso 3:1 gera score 75%, pesos iguais geram 50%
- isolamento multiempresa: inspector em empresa diferente ve stats zeradas

### Frontend — Vitest (unitario e de servico)

Estado validado em `2026-05-31`:

- `119 passed`

Cobertura atual:

| Arquivo | Tipo |
|---|---|
| `problem.test.ts`, `storage.test.ts` | utils |
| `auth.store.test.ts` | store |
| `context.store.test.ts` | store |
| `forms.store.test.ts` | store |
| `users.store.test.ts` | store |
| `teams.store.test.ts` | store |
| `submissions.store.test.ts` | store |
| `auth.service.test.ts` | service |
| `companies.service.test.ts` | service |
| `context.service.test.ts` | service |
| `forms.service.test.ts` | service |
| `notifications.service.test.ts` | service |
| `search.service.test.ts` | service |
| `submissions.service.test.ts` | service |
| `teams.service.test.ts` | service |
| `users.service.test.ts` | service |
| `uploads.service.test.ts` | service |
| `attachments.service.test.ts` | service |

## 10. Decisoes arquiteturais consolidadas

### Multiempresa desde o inicio

Mantida e correta. Estrutura do dominio e contratos ja assumem tenant ativo.

### Versionamento de formularios

Mantido e central para preservar historico.

Publicar uma nova versao cria `FormVersion` + `FormField` novos. A versao anterior fica imutavel e as inspecoes ja finalizadas continuam legando a ela.

### Modelo hibrido de respostas

Mantido:

- `submission_values` como representacao estruturada
- `answers_json` como snapshot otimizado

O snapshot `answers_json` e usado como fonte de leitura rapida durante a finalizacao — isso evita N+1 de queries por campo.

### config_json como extensao de campo

Campos de formulario tem toda a sua configuracao especifica em `config_json` (JSONB). Isso evita colunas esparsas e permite adicionar novas opcoes sem migracoes de schema. A estrutura e responsabilidade do servico interpretar e validar cada propriedade.

### Tipo `section` sem submission_value

Campos do tipo `section` sao divisores visuais. Eles nao geram `submission_value`, nao participam do score e sao automaticamente excluidos de todas as validacoes de finalizacao. A chave e gerada automaticamente pelo frontend no formato `__section_{posicao}__`.

### N/A em campos booleanos

O valor N/A e armazenado como `value_text = "na"` com `value_boolean = NULL`. Isso distingue N/A de "sem resposta" (linha inexistente em `submission_values`). N/A nao entra no denominador do score ponderado — so e contado em `na_count` no breakdown.

### Score ponderado via conformities

O score nao e uma media simples. Cada campo booleano tem `config_json.weight` (default 1.0). O score e calculado a partir de `submission_conformities`:

```
score = sum(weight_i para status='conforme') / sum(weight_i para avaliados) * 100
```

onde `avaliados` inclui apenas campos com registro em `submission_conformities` cujo status seja `conforme` ou `nao_conforme`. Campos sem avaliacao e N/A nao entram no denominador.

A separacao entre resposta (booleana, em `submission_values`) e avaliacao de conformidade (em `submission_conformities`) permite que o inspetor responda campos e decida a conformidade em etapas distintas durante a inspecao.

### PDF em Latin-1 (fpdf2 Helvetica)

A geracao de PDF usa fpdf2 com a fonte embutida Helvetica. Helvetica suporta apenas o charset Latin-1 (ISO 8859-1). Todos os textos escritos no PDF devem estar dentro deste conjunto. Em particular:

- Usar `"-"` em vez de `"—"` (em dash U+2014)
- Usar `"..."` em vez de `"…"` (elipsis U+2026)
- Acentos do portugues (`a`, `e`, `o`, `u`, `c`) estao dentro de Latin-1 e sao seguros

Para suportar Unicode completo, seria necessario registrar uma fonte TTF.

### Upload local antes de storage externo

Mantido e coerente com o momento do projeto.

### Backend async

Ja e realidade no codigo. Qualquer documentacao antiga que ainda fale em sessao sincrona deve ser considerada obsoleta.

### Notificacoes sem tabela propria

As notificacoes sao derivadas do estado das submissions em tempo real. Nao existe tabela `notifications` no banco.

O estado de leitura e persistido separadamente em `notification_reads` (chave composta `user_id + notification_key`). A chave e deterministica — ex.: `excellent-{submission_id}` — o que permite upsert sem conflito.

Dismiss ainda e so no estado local do frontend.

### Recuperacao de senha

Implementada com token de uso unico (TTL 1h) em `password_reset_tokens`. Entrega via SMTP quando configurado, ou via log em desenvolvimento. Anti-enumeracao: o endpoint sempre retorna 200 independente de o email existir.

## 11. O que esta consolidado vs. parcial

### Consolidado

- backend principal e contratos HTTP
- autenticacao, contexto e sessao
- recuperacao de senha (forgot + reset)
- shell autenticado consistente em todas as telas
- usuarios
- formularios com versionamento, secoes, tipos completos e config_json
- campo `instruction` por campo de formulario (builder UI + importacao)
- importacao de formulario via CSV ou Excel (`POST /api/v1/forms/import`)
- inspecoes com score ponderado, N/A, modo inspecao, carga progressiva
- avaliacao de conformidade por campo (`submission_conformities`) — base do score e da barra de progresso
- comportamento de avanco automatico apenas no botao "Conforme" (card view)
- finalizacao com validacao de campos visiveis
- relatorio e exportacao PDF profissional (score colorido, breakdown, secoes)
- evidencias e uploads (imagem, video, audio, PDF)
- equipes
- exportacao CSV
- busca em tempo real
- dashboard com score_by_form e score_trend
- configuracoes da empresa (GET + PATCH com guard de role)
- perfil (nome, senha, empresas vinculadas)
- notificacoes derivadas (sem persistencia)
- testes automatizados: backend 214 passed (integracao + unidade), frontend 119 passed (Vitest)

### Parcial ou com limitacao conhecida

- notificacoes: dismiss existe so no estado local do frontend; recarregar a pagina perde o estado de dismiss (mark-as-read e persistido via `notification_reads`)
- CompanySettings / aba Utilizacao: limites de uso (50 usuarios, 500 inspecoes, 100 formularios) sao hardcoded, nao vem de API
- CompanySettings / aba Plano: botao "Falar com o comercial" nao tem acao real
- Excluir empresa: endpoint e fluxo nao implementados; botao desabilitado na interface
- PDF com fonte Helvetica (Latin-1 only): caracteres fora do charset causam erro em geracao

## 12. Proxima linha segura de evolucao

1. limites de uso reais via API (`/me/usage` ou similar)
2. excluir empresa: endpoint `DELETE /companies/me` + fluxo no frontend
3. font TTF no PDF para suporte a Unicode completo (emojis, simbolos especiais)
4. storage externo (S3/GCS) em substituicao ao disco local
5. preparar PWA apos consolidar os itens acima
