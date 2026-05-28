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

- Backend: FastAPI, SQLAlchemy async, Alembic, PostgreSQL, slowapi, fpdf2
- Frontend: Vue 3, Pinia, Vue Router, Tailwind CSS v4, Axios, Vitest
- Uploads: armazenamento local em disco

Baseline validado em `2026-05-27`:

- backend: `127 passed, 3 skipped`
- frontend: `116 passed`
- frontend build: `npm run build` OK

## 2. Estado real do produto

O Smart Audit ja nao esta mais em fase apenas de fundacao. O estado atual do codigo mostra:

- autenticacao JWT funcional
- recuperacao de senha completa (forgot-password + reset via token com TTL de 1h)
- contexto de empresa ativa e selecao de empresa
- dashboard com metricas por periodo
- CRUD de usuarios
- CRUD de equipes e membros
- formularios versionados
- detalhe de formulario e historico de versoes
- inspecoes com respostas tipadas e score
- finalizacao de inspecao com calculo de score
- evidencias anexadas por upload local
- relatorio e exportacao PDF de inspecao
- exportacao CSV de inspecoes com filtro de status
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
- `GET /api/v1/me/stats`
- `GET /api/v1/me/notifications` — derivadas de submissions, sem persistencia propria
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
- criacao
- publicacao de nova versao
- leitura de versao especifica
- historico de versoes

### Inspecoes

Responsavel pela execucao do formulario, persistencia de respostas e score.

Entidades principais:

- `submissions`
- `submission_values`

Capacidades ativas:

- criacao de inspecao
- listagem com filtros (status, form_id, created_by)
- detalhe
- salvamento de respostas tipadas
- finalizacao e calculo de score
- exportacao PDF por inspecao
- exportacao CSV da lista (com filtro de status)

### Evidencias

Responsavel por vincular metadados de arquivos a respostas de inspecao.

Entidade principal:

- `attachments`

### Uploads

Responsavel por receber arquivos de imagem e gravar em disco.

Observacao:

- nao existe modulo de dominio separado para uploads
- a logica fica encapsulada no router
- isso e aceitavel no estado atual porque o caso de uso e pequeno e bem isolado

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
- notificacoes em `/api/v1/me/notifications`: derivadas em tempo real das submissions
  - inspeções `in_progress` ha mais de 24h geram alerta `pending`
  - `completed` com score < 80% geram alerta `low_score`
  - `completed` com score >= 90% geram alerta `excellent`
  - mark-as-read e dismiss existem so no estado local do frontend

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

## 6. Design system e front-end visual

O frontend atual ja incorporou boa parte do redesign em curso.

Base visual ativa:

- Tailwind CSS v4
- tokens CSS proprios em `style.css`
- fontes `Plus Jakarta Sans` e `DM Mono`
- shell dark sidebar + bottom nav mobile
- icones SVG centralizados

Referencias:

- estilos base: [frontend/src/style.css](/c:/Projetos/smart-audit/frontend/src/style.css)
- icones: [frontend/src/components/ui/AppIcons.ts](/c:/Projetos/smart-audit/frontend/src/components/ui/AppIcons.ts)
- renderer de icone: [frontend/src/components/ui/SvgIcon.vue](/c:/Projetos/smart-audit/frontend/src/components/ui/SvgIcon.vue)

### Relacao com `redesign-handoff/`

A pasta `redesign-handoff/` nao e mais uma proposta isolada.

Hoje ela funciona como:

- referencia historica do redesign
- material de handoff para ajustes incrementais
- comparativo entre prototipo visual e app real

Ela nao deve mais ser aplicada por substituicao integral sem comparar com o estado atual do frontend.

## 7. Modulos e rotas implementados

### Backend

Rotas agregadas hoje:

- `health`
- `auth` (login, me, forgot-password, reset-password)
- `companies`
- `me` (context, companies, stats, notifications)
- `users`
- `forms`
- `submissions` (CRUD, answers, finish, export CSV, export PDF)
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
- `/`
- `/users`
- `/forms`
- `/forms/:formId`
- `/forms/:formId/versions`
- `/submissions`
- `/submissions/:id`
- `/submissions/:id/report`
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

## 9. Testes

### Backend

Estado validado em `2026-05-27`:

- `127 passed, 3 skipped`

Cobertura atual:

| Arquivo | Tipo |
|---|---|
| `test_auth.py` | integracao |
| `test_password_reset.py` | integracao |
| `test_forms.py` | integracao |
| `test_submissions.py` | integracao |
| `test_submissions_export.py` | integracao |
| `test_search.py` | integracao |
| `test_users.py` | integracao |
| `test_teams.py` | integracao |
| `test_companies.py` | integracao |
| `test_me.py` | integracao |
| `test_uploads.py` | integracao |
| `test_form_service.py` | unidade |
| `test_submission_service.py` | unidade |

Lacuna: `test_attachments.py` (integracao) ainda nao existe.

### Frontend

Estado validado em `2026-05-27`:

- `116 passed`

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

### Modelo hibrido de respostas

Mantido:

- `submission_values` como representacao estruturada
- `answers_json` como snapshot otimizado

### Upload local antes de storage externo

Mantido e coerente com o momento do projeto.

### Backend async

Ja e realidade no codigo. Qualquer documentacao antiga que ainda fale em sessao sincrona deve ser considerada obsoleta.

### Notificacoes sem tabela propria

Decisao deliberada: notificacoes sao derivadas do estado das submissions em tempo real. Nao existe tabela `notifications` no banco. Isso e adequado enquanto os alertas forem simples e de leitura. Se houver necessidade de persistir estado de leitura por usuario ou criar notificacoes de outras origens, sera necessario criar a tabela.

### Recuperacao de senha

Implementada com token de uso unico (TTL 1h) em `password_reset_tokens`. Entrega via SMTP quando configurado, ou via log em desenvolvimento. Anti-enumeracao: o endpoint sempre retorna 200 independente de o email existir.

## 11. O que esta consolidado vs. parcial

### Consolidado

- backend principal e contratos HTTP
- autenticacao, contexto e sessao
- recuperacao de senha (forgot + reset)
- shell autenticado consistente em todas as telas
- usuarios
- formularios e versionamento
- inspecoes, respostas, score
- finalizacao e relatorio
- evidencias e uploads
- equipes
- exportacao PDF e CSV
- busca em tempo real
- configuracoes da empresa (GET + PATCH com guard de role)
- perfil (nome, senha, empresas vinculadas)
- notificacoes derivadas (sem persistencia)
- testes automatizados de backend (integracao + unidade) e frontend (stores + services)

### Parcial ou com limitacao conhecida

- notificacoes: mark-as-read e dismiss existem so no estado local do frontend; recarregar a pagina perde o estado
- CompanySettings / aba Utilizacao: limites de uso (50 usuarios, 500 inspecoes, 100 formularios) sao hardcoded, nao vem de API
- CompanySettings / aba Plano: botao "Falar com o comercial" nao tem acao real
- Excluir empresa: endpoint e fluxo nao implementados; botao desabilitado na interface

## 12. Proxima linha segura de evolucao

1. testes de integracao para o modulo `attachments` (unico endpoint sem cobertura)
2. persistir estado de leitura de notificacoes (tabela `notification_reads` ou coluna em `submissions`)
3. limites de uso reais via API (`/me/usage` ou similar)
4. preparar PWA apos consolidar os itens acima
