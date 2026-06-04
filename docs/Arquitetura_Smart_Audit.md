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
- CI: GitHub Actions com jobs separados para backend, frontend (Vitest) e E2E (Playwright)

Baseline validado em `2026-06-04`:

- backend: `212 passed, 3 skipped`
- frontend Vitest: `119 passed`
- frontend build: `npm run build` OK
- E2E Playwright: `53 testes` (todos mockados, sem backend necessario)

## 2. Estado real do produto

O Smart Audit ja nao esta mais em fase apenas de fundacao. O estado atual do codigo mostra:

- autenticacao JWT funcional
- recuperacao de senha completa (forgot-password + reset via token com TTL de 1h)
- contexto de empresa ativa e selecao de empresa
- dashboard com metricas por periodo, grafico de score por formulario e sparkline de tendencia 30 dias
- CRUD de usuarios com desativacao de usuario (`is_active`) e revogacao de acesso (`DELETE /users/{id}`)
- CRUD de equipes e membros com desativacao soft (equipes deactivadas nao aparecem na lista)
- memberships com soft delete via `revoked_at` — usuarios revogados nao acessam mais a empresa
- formularios versionados com suporte a secoes, evidencias e configuracao avancada por campo
- campos de formulario configurados via `config_json`: peso, allow_na, opcoes de select
- tipos de campo: `boolean`, `text`, `number`, `select`, `date`, `section`
- detalhe de formulario e historico de versoes
- importacao de formulario via CSV ou Excel
- inspecoes com respostas tipadas e score ponderado por peso de campo
- suporte a resposta N/A em campos booleanos com `allow_na: true`
- modo de inspecao (card a card) e modo lista com carga progressiva (`load more`)
- barra de progresso e atalhos rapidos por secao na execucao da inspecao
- finalizacao de inspecao com calculo de score ponderado
- score_breakdown com contagem de conformes, nao conformes, sem resposta e N/A
- relatorio detalhado por inspecao com exportacao PDF profissional com suporte a Unicode (fonte DejaVu Sans TTF)
- exportacao CSV de inspecoes com filtro de status
- evidencias anexadas por upload local (imagem, video, audio, PDF)
- busca em tempo real por formularios e inspecoes (`GET /search?q=`)
- perfil do usuario (nome, senha, empresas vinculadas)
- configuracoes da empresa (dados cadastrais, fuso horario, guard de role)
- notificacoes derivadas das inspecoes com persistencia de leitura e dismiss no banco

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
- `GET /api/v1/me/usage` — contagens reais de uso vs limites do plano (`users`, `forms`, `submissions_this_month`)
- `GET /api/v1/me/notifications` — derivadas de submissions; retorna `read: bool` e `dismissed: bool` persistidos
- `POST /api/v1/me/notifications/read` — marca uma notificacao como lida
- `POST /api/v1/me/notifications/read-all` — marca todas as notificacoes fornecidas como lidas
- `POST /api/v1/me/notifications/dismiss` — descarta uma notificacao (persistido em `notification_reads.dismissed`)
- `POST /api/v1/me/notifications/dismiss-all` — descarta multiplas notificacoes
- `GET /api/v1/companies/me`
- `PATCH /api/v1/companies/me` (requer OWNER ou ADMIN)

Limites de uso por plano (definidos em `CompanyService._PLAN_LIMITS`):

| Plano | Usuarios | Formularios | Inspecoes/mes |
|---|---|---|---|
| `starter` | 10 | 20 | 100 |
| `pro` | 50 | 100 | 500 |
| `enterprise` | 999 | 999 | 9999 |

### Usuarios

Responsavel por gerenciar membros da empresa.

Capacidades ativas:

- `GET /api/v1/users` — lista memberships ativos (`revoked_at IS NULL`)
- `GET /api/v1/users/{id}`
- `POST /api/v1/users` — cria usuario e vincula via membership
- `PATCH /api/v1/users/{id}` — atualiza nome, senha, role, `is_active` do usuario
- `DELETE /api/v1/users/{id}` — revoga o acesso do usuario (seta `revoked_at`); nao exclui dados

Regras de revogacao:

- apenas ADMIN ou superior podem revogar
- o proprio usuario nao pode revogar o proprio acesso
- usuario revogado desaparece da listagem e perde acesso imediato (token existente rejeitado no proximo contexto)
- o historico de inspecoes e registros permanece intacto

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
- exportacao PDF individual com score profissional e suporte a Unicode
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
- tipos permitidos: `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `video/quicktime`, `video/x-msvideo`, `audio/mpeg`, `audio/wav`, `audio/ogg`, `audio/mp4`, `application/pdf`
- limites por tipo: imagem 10 MB, PDF 20 MB, audio 50 MB, video 200 MB

### Equipes

Responsavel por organizar usuarios em equipes dentro da empresa ativa.

Entidades principais:

- `teams`
- `team_members`

Capacidades ativas:

- listagem de equipes ativas (`is_active = TRUE`)
- criacao de equipe
- edicao de equipe
- desativacao de equipe (`DELETE /teams/{id}` — soft delete via `is_active = FALSE`)
- adicionar membro (valida se equipe esta ativa e se usuario tem membership ativo)
- remover membro

Regras de desativacao:

- equipes desativadas nao aparecem na listagem nem no detalhe (retornam 404)
- operacoes de membro em equipes inativas tambem retornam 404
- o historico de membros permanece intacto no banco

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
- estado de leitura persistido em `notification_reads.read = TRUE`
- estado de dismiss persistido em `notification_reads.dismissed = TRUE`; notificacoes dispensadas nao aparecem na listagem

### Relatorio e exportacao PDF

Responsavel por gerar o relatorio visual de uma inspecao em PDF.

Capacidades ativas:

- `GET /api/v1/submissions/{id}/export` — download do PDF
- `GET /api/v1/submissions/{id}/export?inline=true` — abertura inline no browser
- conteudo do PDF: bloco de score colorido (verde/amarelo/vermelho), chips de breakdown, tabela de respostas com resultado de conformidade, divisores de secao, rodape com contagem de campos
- fonte DejaVu Sans TTF embutida — suporte completo a Unicode incluindo acentos portugueses, caracteres especiais e simbolos

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
- Soft delete via `revoked_at` (memberships) e `is_active` (teams, forms)

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
- `liveScore`: score calculado em tempo real durante a inspecao (baseado em `conformityStatus`, que espelha `submission_conformities`; mesma formula ponderada do backend)

## 6. Design system e front-end visual

O frontend atual ja incorporou boa parte do redesign em curso.

Base visual ativa:

- Tailwind CSS v4
- tokens CSS proprios em `style.css`
- fontes `Plus Jakarta Sans` e `DM Mono`
- shell dark sidebar + bottom nav mobile
- icones SVG centralizados

Classes CSS de inspecao:

- `.insp-card`, `.insp-meta`, `.insp-section`, `.insp-counter`, `.insp-nav` — modo inspecao card
- `.insp-progress-bar` — barra de progresso (preenchimento via `:style` inline)
- `.insp-sec-chips`, `.insp-sec-chip`, `.insp-sec-chip--done`, `.insp-sec-chip--active` — chips de secao no modo inspecao (card e lista inspecao)
- `.score-ring`, `.score-ring-inner` — anel de score conic-gradient no header de inspecao
- `.section-jump-bar`, `.section-jump-chip` — atalhos de secao no modo lista normal (leitura)
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
- `me` (context, companies, stats com score_by_form/score_trend, usage, notifications com read/dismiss)
- `users` (CRUD + revogacao de acesso via `DELETE /users/{id}`)
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
- `/users` — lista, cria, edita, revoga acesso
- `/forms`
- `/forms/:formId` — editor com secoes, peso, allow_na, instrucao por campo
- `/forms/:formId/versions`
- `/submissions`
- `/submissions/:id` — execucao com modo inspecao e modo lista, progresso, atalhos de secao
- `/submissions/:id/report` — relatorio com botoes "Visualizar PDF" e "Baixar PDF"
- `/profile`
- `/company-settings` — aba Geral, aba Plano, aba Utilizacao (contagens reais via API)
- `/notifications` — com dismiss persistido
- `/search`
- `/teams` — lista, cria, edita, desativa equipes; gerencia membros

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

### Resposta de uso (`GET /me/usage`)

```json
{
  "data": {
    "users": { "used": 3, "limit": 10 },
    "forms": { "used": 7, "limit": 20 },
    "submissions_this_month": { "used": 14, "limit": 100 }
  }
}
```

## 9. Testes

### Backend

Estado validado em `2026-06-04`:

- `212 passed, 3 skipped`

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
| `test_teams.py` | integracao | CRUD equipes e membros (soft delete) |
| `test_companies.py` | integracao | configuracoes de empresa |
| `test_me.py` | integracao | context, stats, notificacoes, usage |
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

### E2E — Playwright

Job `e2e` no CI (`.github/workflows/ci.yml`). Todos os 53 testes usam `page.route()` para mockar chamadas de API — nao requerem backend em execucao.

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

### Soft delete por tipo de entidade

O sistema distingue dois mecanismos de soft delete conforme a semântica da entidade:

- **`memberships.revoked_at TIMESTAMPTZ NULL`** — timestamp de quando o acesso foi revogado. Todas as queries que dependem de membership ativo filtram `WHERE revoked_at IS NULL`: listagem de usuarios da empresa, resolucao de contexto, autenticacao (dependencias `get_current_membership`), e contagem de membros ativos em `/me/usage`.

- **`teams.is_active BOOLEAN`** — flag booleana para equipes. Listagem e detalhe de equipes filtram `WHERE is_active = TRUE`. Operacoes de membro em equipes inativas retornam 404. O `DELETE /teams/{id}` HTTP realiza desativacao em vez de exclusao fisica.

Dados historicos (inspecoes, respostas, evidencias, membros de equipe) sao preservados em ambos os casos.

### Notificacoes sem tabela propria

As notificacoes sao derivadas do estado das submissions em tempo real. Nao existe tabela `notifications` no banco.

O estado de leitura e dismiss e persistido em `notification_reads` (campos `read: bool` e `dismissed: bool`, chave composta `user_id + notification_key`). A chave e deterministica — ex.: `excellent-{submission_id}` — o que permite upsert sem conflito. Notificacoes dispensadas sao filtradas antes de retornar ao cliente.

### PDF com fonte DejaVu Sans TTF

O PDF e gerado com fpdf2 usando a fonte DejaVu Sans TTF embutida em `backend/app/modules/submissions/fonts/`. Essa fonte cobre Unicode completo, incluindo todos os acentos do portugues, simbolos especiais e caracteres internacionais. O arquivo TTF (~757 KB) esta versionado no repositorio.

### Recuperacao de senha

Implementada com token de uso unico (TTL 1h) em `password_reset_tokens`. Entrega via SMTP quando configurado, ou via log em desenvolvimento. Anti-enumeracao: o endpoint sempre retorna 200 independente de o email existir.

### Upload local antes de storage externo

Mantido e coerente com o momento do projeto.

### Backend async

Ja e realidade no codigo. Qualquer documentacao antiga que ainda fale em sessao sincrona deve ser considerada obsoleta.

## 11. O que esta consolidado vs. parcial

### Consolidado

- backend principal e contratos HTTP
- autenticacao, contexto e sessao
- recuperacao de senha (forgot + reset)
- shell autenticado consistente em todas as telas
- usuarios com desativacao (`is_active`), revogacao (`DELETE /users/{id}`) e reativacao (`POST /users/{id}/reactivate`)
- formularios com versionamento, secoes, tipos completos e config_json
- campo `instruction` por campo de formulario (builder UI + importacao)
- importacao de formulario via CSV ou Excel (`POST /api/v1/forms/import`)
- inspecoes com score ponderado, N/A, modo inspecao, carga progressiva
- avaliacao de conformidade por campo (`submission_conformities`) — base do score e da barra de progresso
- comportamento de avanco automatico apenas no botao "Conforme" (card view)
- finalizacao com validacao de campos visiveis
- relatorio e exportacao PDF profissional (score colorido, breakdown, secoes, Unicode via DejaVu Sans)
- evidencias e uploads (imagem, video, audio, PDF)
- equipes com soft delete (`is_active`)
- memberships com soft delete (`revoked_at`) e reativacao
- desativacao de empresa (`DELETE /companies/me`) com cascade de memberships e equipes; modal de confirmacao com digitacao do nome + logout automatico
- audit_logs: tabela imutavel, bounded context completo, eventos company.deactivated / membership.revoked / membership.reactivated / user.created / team.deactivated; view com filtro e paginacao
- exportacao CSV
- busca em tempo real
- dashboard com score_by_form e score_trend
- configuracoes da empresa (GET + PATCH com guard de role)
- perfil (nome, senha, empresas vinculadas)
- notificacoes com persistencia de leitura e dismiss
- endpoint `/me/usage` com contagens reais e limites por plano
- CI com jobs separados: backend (ruff + pytest), frontend (vue-tsc + Vitest), E2E (Playwright)
- testes automatizados: backend 218 passed, frontend 119 passed (Vitest), 53 E2E (Playwright)

### Parcial ou com limitacao conhecida

- CompanySettings / aba Plano: botao "Falar com o comercial" nao tem acao real
- Storage externo: uploads ficam em disco local; sem S3/GCS

## 12. Proxima linha segura de evolucao

1. ~~`DELETE /companies/me`~~ — concluido
2. ~~Reativar membership revogado~~ — concluido
3. ~~`audit_logs`~~ — concluido
4. Storage externo (S3/GCS) em substituicao ao disco local
5. `corrective_actions` — acoes corretivas vinculadas a itens reprovados em inspecoes
6. Preparar PWA apos consolidar os itens acima
