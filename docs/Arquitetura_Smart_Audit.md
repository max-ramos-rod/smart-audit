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

- backend: `90 passed, 3 skipped`
- frontend: `68 passed`
- frontend build: `npm run build` OK

## 2. Estado real do produto

O Smart Audit ja nao esta mais em fase apenas de fundacao. O estado atual do codigo mostra:

- autenticacao JWT funcional
- contexto de empresa ativa e selecao de empresa
- dashboard com metricas por periodo
- CRUD de usuarios
- CRUD de equipes e membros
- formularios versionados
- detalhe de formulario e historico de versoes
- inspecoes com respostas tipadas e score
- evidencias anexadas por upload local
- relatorio e exportacao PDF de inspecao
- tela placeholder de recuperacao de acesso
- telas auxiliares de perfil, busca, notificacoes e configuracoes da empresa, agora alinhadas ao shell principal e com UX mais consistente

Ha, portanto, uma diferenca importante entre:

- o nucleo de dominio, que esta consolidado
- e algumas telas auxiliares, que ainda funcionam como composicao de UX em cima do dominio existente

## 3. Bounded contexts implementados

### Identidade e acesso

Responsavel por autenticacao, perfil, empresa ativa e memberships.

Entidades principais:

- `users`
- `companies`
- `memberships`

Capacidades ativas:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/me/companies`
- `GET /api/v1/me/context`
- `PATCH /api/v1/me`

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
- historico de versoes no frontend

### Inspecoes

Responsavel pela execucao do formulario, persistencia de respostas e score.

Entidades principais:

- `submissions`
- `submission_values`

Capacidades ativas:

- criacao de inspecao
- listagem com filtros
- detalhe
- salvamento de respostas
- finalizacao
- score e score breakdown
- exportacao PDF

### Evidencias

Responsavel por vincular metadados de arquivos a respostas de inspecao.

Entidade principal:

- `attachments`

### Uploads

Responsavel por receber arquivos de imagem e gravar em disco.

Observacao:

- nao existe um modulo de dominio separado para uploads
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

### Visao analitica

Hoje a visao analitica e derivada principalmente de `submissions`.

Capacidades ativas:

- metricas em `/api/v1/me/stats`
- filtro por periodo `7d | 30d | 90d | all`

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

### Padrões realmente aplicados

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

### Padrões realmente aplicados

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
- `auth`
- `me`
- `users`
- `forms`
- `submissions`
- `teams`
- `attachments`
- `uploads`

### Frontend

Rotas de interface existentes hoje:

- `/login`
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
- `/forgot-password`

Observacao:

- `"/forgot-password"` existe hoje como rota placeholder segura, sem fluxo transacional completo de recuperacao

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

## 9. Testes

### Backend

Estado validado em `2026-05-27`:

- `90 passed, 3 skipped`

Cobertura atual observada no repositorio:

- integracao: auth, forms, me, submissions, teams, uploads, users
- unidade: form service, submission service

### Frontend

Estado validado em `2026-05-27`:

- `68 passed`

Cobertura atual observada:

- `problem`
- `storage`
- `auth.store`
- `context.store`
- `forms.store`
- `submissions.store`
- `teams.store`
- `users.store`

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

## 11. O que esta consolidado vs. parcial

### Consolidado

- backend principal
- contratos HTTP
- autenticacao e contexto
- shell autenticado consistente nas telas principais
- usuarios
- formularios
- inspecoes
- evidencias e uploads
- equipes
- exportacao PDF
- recuperacao de acesso com placeholder de UX
- testes automatizados de backend e frontend

### Parcial ou em composicao

- notificacoes: derivadas do estado das inspecoes, sem modulo dedicado
- busca: UX funcional e alinhada ao shell, mas sem backend de busca dedicado
- configuracoes da empresa: interface mais clara, mas sem backend administrativo completo
- perfil: fluxo funcional, mas ainda simples para um modulo completo de conta
- gerenciamento completo de plano e recuperacao real de senha ainda nao existem

## 12. Principais pendencias documentais e tecnicas

- corrigir mojibake/encoding em documentos e parte da UI
- manter a documentacao sincronizada com os numeros reais de teste
- explicitar melhor o que e tela operacional e o que e tela placeholder
- antes de PWA, consolidar fluxos auxiliares e substituir placeholders por fluxos reais onde fizer sentido

## 13. Proxima linha segura de evolucao

1. estabilizar documentacao e consistencia textual
2. transformar placeholders visiveis em fluxos reais ou estados de produto explicitamente limitados
3. consolidar telas auxiliares com backend dedicado onde fizer sentido
4. depois preparar PWA
