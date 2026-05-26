# Arquitetura do Sistema - Smart Audit

## 1. Visão Geral

- Nome do sistema: Smart Audit
- Objetivo principal: digitalizar checklists, auditorias e inspeções com histórico, evidências e base pronta para evolução como SaaS.
- Problema de negócio que resolve: substituir planilhas, papel, formulários soltos e processos manuais por execução estruturada, rastreável e padronizada.
- Usuários principais:
  - administradores da empresa
  - gestores/supervisores
  - inspetores
  - usuários de consulta
- Perfis de acesso:
  - `OWNER`
  - `ADMIN`
  - `MANAGER`
  - `INSPECTOR`
  - `VIEWER`
- Stack principal:
  - Backend: FastAPI (Python 3.12), SQLAlchemy 2.0, Alembic, PostgreSQL
  - Frontend: Vue 3, Pinia, Vue Router, TailwindCSS 4, Axios
  - Testes backend: pytest + savepoint isolation real (PostgreSQL)
  - Testes frontend: Vitest + jsdom
  - Uploads: armazenamento local em disco (compatível com S3 futuramente)

## 2. Leitura do Domínio

### Núcleo do negócio

O núcleo do Smart Audit é a relação entre:

- empresa
- formulário de inspeção
- versão do formulário
- execução da inspeção
- resposta por item
- evidência anexada

O valor do produto não está apenas em cadastrar itens, mas em garantir:

- padronização da execução
- histórico confiável
- consistência entre versões
- rastreabilidade por empresa e usuário
- base para indicadores e relatórios

### Bounded contexts implementados

#### Identidade e acesso
- Objetivo: autenticar usuário, definir empresa ativa e aplicar papel de acesso.
- Entidades principais:
  - `users`
  - `companies`
  - `memberships`

#### Formulários
- Objetivo: permitir criação e evolução de templates de checklist sem quebrar execuções passadas.
- Entidades principais:
  - `forms`
  - `form_versions`
  - `form_fields`

#### Inspeções
- Objetivo: executar um formulário versionado, registrar respostas, status e progresso.
- Entidades principais:
  - `submissions`
  - `submission_values`

#### Evidências
- Objetivo: anexar fotos e arquivos em respostas específicas da inspeção.
- Entidades principais:
  - `attachments`

#### Equipes
- Objetivo: organizar usuários em equipes dentro de uma empresa.
- Entidades principais:
  - `teams`
  - `team_members`

#### Uploads
- Objetivo: receber e armazenar arquivos de evidência (imagens) com metadados.
- Implementação: endpoint `POST /api/v1/uploads`, escrita em disco, URL pública configurável via `UPLOAD_BASE_URL`.
- Sem módulo de domínio próprio — lógica de validação e persistência encapsuladas no router de uploads.

#### Visão analítica
- Objetivo: fornecer indicadores básicos de acompanhamento.
- Derivada de `submissions` e `submission_values` no endpoint `/me/stats`.

### O que é suporte e não núcleo do MVP

Ficam fora do MVP, mas com espaço arquitetural preparado:

- offline-first completo
- sync engine
- permissões granulares por equipe
- relatórios PDF sofisticados
- plano de ação corretiva
- automações e notificações

## 3. Arquitetura Recomendada

### Backend

Padrão principal:

`api -> service -> repository -> db`

Responsabilidades:

- `api/`
  - routers/endpoints
  - validação web
  - serialização HTTP
  - injeção de dependências
- `modules/<dominio>/service.py`
  - regras de negócio
  - orquestração de casos de uso
  - validações de domínio
  - `db.commit()` acontece aqui
- `modules/<dominio>/repository.py`
  - persistência
  - queries
  - acesso ao ORM
  - `db.flush()` via `_save()` — nunca `db.commit()`
  - métodos de criação nomeados (ex.: `create_team`, não `_save` direto)
- `modules/<dominio>/schemas.py`
  - contratos request/response (Pydantic)
  - todos os campos de request com `Field(min_length=..., max_length=...)`
- `db/models/`
  - entidades ORM
  - mapeamento relacional
- `core/`
  - configuração
  - auth JWT
  - sessão de banco
  - tratamento de erro RFC 7807
  - envelopes padrão `success_response` / `paginated_response`
  - `SQLAlchemyRepository` base com `_save`, `_save_many`
  - paginação com `PageMeta`

### Frontend

Organização principal:

- `router/`
- `stores/`
- `services/`
- `views/`
- `components/`
- `types/`

Responsabilidades:

- `router/`
  - rotas
  - guard de autenticação: bootstrap de contexto + sync de `authStore.user` após refresh
  - metadados por rota (`requiresAuth`, `guestOnly`)
- `stores/`
  - estado por domínio
  - loading/error
  - chamadas assíncronas orquestradas
- `services/`
  - cliente HTTP centralizado (`http.ts`) — nunca chamar axios diretamente
  - auto-attach de `Authorization: Bearer` e `X-Company-Id` em toda requisição
  - limpeza de token em 401
- `views/`
  - telas finas
  - composição de componentes
- `components/`
  - layout e UI reutilizável
- `types/`
  - contratos alinhados com a API

## 4. Estrutura de Pastas

### Backend

```text
backend/
  app/
    api/
      v1/
        router.py         # agrega todos os routers
        routers/
          auth.py
          me.py
          users.py
          forms.py
          submissions.py
          attachments.py
          uploads.py
          teams.py
          health.py
    core/
      config.py           # Settings via pydantic-settings, lê .env da raiz do repo
      responses.py        # success_response, paginated_response
      errors.py           # handlers RFC 7807
      repositories.py     # SQLAlchemyRepository base
      pagination.py       # PageMeta, paginate_query
      security.py         # PBKDF2-SHA256 custom
    db/
      models/             # ORM: users, companies, memberships, forms,
                          #       form_versions, form_fields, submissions,
                          #       submission_values, attachments, teams
      session.py
    modules/
      auth/
      companies/
      memberships/        # dependencies.py, permissions.py
      users/
      forms/
      submissions/
      attachments/
      teams/
  alembic/
    versions/
  tests/
    integration/          # 85 testes com savepoint isolation em Postgres real
```

### Frontend

```text
frontend/
  src/
    router/
      index.ts            # guard: bootstrap + sync authStore.user
    stores/
      auth/
      context/
      users/
      forms/
      submissions/
    services/
      api/
        http.ts           # cliente Axios centralizado
        storage.ts        # token + company-id em localStorage
        problem.ts        # extrai mensagem de erro de RFC 7807
      auth.service.ts
      context.service.ts
      users.service.ts
      forms.service.ts
      submissions.service.ts
      uploads.service.ts
      attachments.service.ts
    views/
      auth/
      dashboard/
      users/
      forms/
      submissions/
    components/
      layout/
        AppShell.vue      # sidebar + nav + seleção de empresa
      ui/
        BaseButton.vue
    types/
    __tests__/            # 25 testes Vitest (problem, storage, auth.store, context.store)
```

## 5. Padrões de Projeto Adotados

### Backend

- Layered Architecture (`api -> service -> repository -> db`)
- Repository Pattern com métodos nomeados de criação
- Service Layer como responsável pelo `commit`
- Migrations versionadas Alembic (escritas manualmente, sem autogenerate)
- Envelopes padronizados de resposta `{ "data": ..., "meta": {...} }`
- Erros em RFC 7807 `application/problem+json`
- Paginação padronizada com `PageMeta`
- Multi-tenancy obrigatório: toda query de domínio filtra por `company_id`
- JWT Bearer + `X-Company-Id` header para resolução de tenant
- PBKDF2-SHA256 customizado para hashes de senha

### Frontend

- SPA com Vue Router e guards de autenticação
- Pinia por domínio (composition API style)
- Cliente HTTP centralizado — `axios` nunca chamado diretamente em views/stores
- Token + company-id persistidos em `localStorage`
- Views finas — lógica nos stores, não nas views
- Componentes orientados a caso de uso

## 6. Contratos da API

### Sucesso

```json
{
  "data": {},
  "meta": {}
}
```

### Paginação

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

### Erro (RFC 7807)

```json
{
  "type": "about:blank",
  "title": "Not Found",
  "status": 404,
  "detail": "Recurso não encontrado.",
  "instance": "/api/v1/forms/123"
}
```

### Convenções principais

- Autenticação: `Authorization: Bearer <jwt>`
- Tenant: `X-Company-Id: <uuid>` (opcional se usuário tem apenas 1 empresa)
- Prefixo de versão: `/api/v1`
- Filtros via query params
- IDs como UUID string nos envelopes (`model_dump(mode="json")`)

## 7. Módulos Implementados

### Auth (`/api/v1/auth`)

- `POST /login` — retorna JWT + dados do usuário

### Me (`/api/v1/me`)

- `GET /me` — usuário autenticado
- `GET /me/companies` — empresas do usuário com papel
- `GET /me/context` — contexto ativo (empresa, membership, flags)
- `GET /me/stats` — métricas de inspeções da empresa ativa

### Usuários (`/api/v1/users`)

- CRUD completo de usuários da empresa ativa
- Acesso restrito a `OWNER`/`ADMIN`

### Formulários (`/api/v1/forms`)

- CRUD de formulários com versionamento automático
- `POST /forms/{id}/versions` — publica nova versão com novo conjunto de campos
- `GET /forms/{id}/versions/{vid}` — leitura de versão específica

### Inspeções (`/api/v1/submissions`)

- Criar, listar, detalhar inspeções
- `PUT /submissions/{id}/answers` — salva/atualiza respostas (idempotente)
- `POST /submissions/{id}/finish` — finaliza e calcula score

### Evidências (`/api/v1/attachments`)

- `POST /attachments` — cria registro de evidência para um campo de inspeção
- `GET /submissions/{id}/attachments` — lista evidências de uma inspeção

### Uploads (`/api/v1/uploads`)

- `POST /uploads` — recebe arquivo (JPEG/PNG/WebP, máx 10 MB), salva em disco, retorna URL
- Organizado por `company_id`: `<upload_dir>/<company_id>/<uuid>.<ext>`

### Equipes (`/api/v1/teams`)

- CRUD de equipes por empresa
- `POST /teams/{id}/members/{user_id}` — adiciona membro (valida que pertence à empresa)
- `DELETE /teams/{id}/members/{user_id}` — remove membro
- Leitura livre para qualquer membro; escrita exige `MANAGER` ou superior

## 8. Fluxos Críticos

### Fluxo 1 — Criar formulário

- Entrada: nome, descrição, lista de campos
- Validações: nome obrigatório, pelo menos um campo, chaves de campo únicas por versão
- Regras: cria `form` + `form_version` inicial + `form_fields` em transação única
- Resposta: formulário com versão ativa

### Fluxo 2 — Publicar nova versão

- Entrada: definição atualizada de campos
- Validações: formulário pertence à empresa ativa; nova versão não modifica histórico
- Regras: cria nova `form_version` + novos `form_fields`; versões anteriores intocadas
- Resposta: detalhe da nova versão publicada

### Fluxo 3 — Iniciar inspeção

- Entrada: `form_id` (seleciona versão publicada mais recente automaticamente)
- Validações: versão publicada disponível; usuário com acesso na empresa
- Regras: cria `submission` com status `in_progress`
- Resposta: inspeção aberta com estrutura do formulário

### Fluxo 4 — Responder inspeção

- Entrada: respostas por campo (`field_key` + `value`)
- Validações: tipo compatível com o campo; campo pertence à versão correta
- Regras: upsert em `submission_values`; atualiza `answers_json` (snapshot); recalcula score parcial
- Persistência: operações idempotentes por campo
- Resposta: estado atualizado da inspeção

### Fluxo 5 — Finalizar inspeção

- Entrada: confirmação de conclusão (chamada a `/finish`)
- Regras: salva respostas finais; muda status para `completed`; calcula score final (% de booleanos `true` entre obrigatórios respondidos)
- Resposta: resumo da inspeção concluída com score

### Fluxo 6 — Upload de evidência

- Entrada: arquivo de imagem (multipart/form-data)
- Validações: MIME `image/jpeg | image/png | image/webp`; tamanho ≤ 10 MB
- Regras: grava em disco em `<upload_dir>/<company_id>/<uuid>.<ext>`; retorna URL
- Sequência completa: `POST /uploads` → recebe URL → `POST /attachments` → vincula URL ao campo da inspeção

## 9. Estratégia de Testes

### Backend — 85 testes de integração (pytest)

Configuração: `python -m pytest` na raiz do repositório. Cada teste roda em transação PostgreSQL com rollback via savepoint (`join_transaction_mode="create_savepoint"`). Nenhum mock de banco.

Cobertura por módulo:

| Arquivo de teste | Testes |
|---|---|
| `test_auth.py` | login, me, token inválido |
| `test_users.py` | CRUD, permissões por papel |
| `test_forms.py` | criação, versionamento, paginação |
| `test_submissions.py` | criação, respostas, finalização, score, paginação |
| `test_attachments.py` | criação, listagem, isolamento por empresa |
| `test_uploads.py` | JPEG/PNG/WebP, MIME inválido, tamanho excedido, auth |
| `test_teams.py` | CRUD, membros, duplicata rejeitada, isolamento, permissões |

### Frontend — 25 testes (Vitest + jsdom)

Configuração: `npm test` em `frontend/`. Ambiente jsdom, globals habilitados.

Cobertura:

| Arquivo de teste | Testes |
|---|---|
| `problem.test.ts` | todos os ramos de `extractProblemMessage` |
| `storage.test.ts` | read/write/clear de token e company-id |
| `auth.store.test.ts` | login, logout, setUser, isAuthenticated, persistência |
| `context.store.test.ts` | bootstrap, selectCompany, reset, erro |

## 10. Decisões Arquiteturais

### Decisão 1 — Multi-tenancy desde o início

- Contexto: equilibrar MVP rápido e base pronta para SaaS.
- Opções: sistema simples vs. multiempresa desde o início.
- Escolha: multiempresa desde o início, com autorização simples.
- Motivo: evita retrabalho estrutural cedo demais.
- Consequências: um pouco mais de complexidade inicial em auth e escopo de dados.

### Decisão 2 — Versionamento de formulários

- Contexto: checklists mudam com o tempo.
- Opções: editar checklist em linha vs. versionar formulários.
- Escolha: versionamento de formulário (`forms` → `form_versions` → `form_fields`).
- Motivo: protege histórico de inspeções executadas.
- Consequências: mais tabelas, mas sem risco de quebrar dados antigos.

### Decisão 3 — Modelo híbrido de respostas

- Contexto: precisamos de flexibilidade sem cair em EAV puro e lento.
- Opções: somente JSON / somente relacional / híbrido.
- Escolha: `submission_values` (relacional tipado) + `answers_json` (snapshot desnormalizado).
- Motivo: leitura operacional rápida e consultas futuras viáveis.
- Consequências: exige sincronização entre as duas representações em `save_answers`.

### Decisão 4 — Offline adiado

- Contexto: offline e sincronização são valiosos, mas caros de fazer bem.
- Escolha: adiar para fase futura.
- Motivo: reduz risco e acelera entrega do core.
- Consequências: v1 depende de conectividade.

### Decisão 5 — Equipes promovidas ao MVP

- Contexto: teams/team_members estavam planejados para Fase 4, mas o modelo já era necessário para futuras permissões granulares.
- Escolha: implementar na Fase 3 com escopo mínimo (CRUD + membros).
- Motivo: base relacional é barata de adicionar agora; API já é usada por clients externos.
- Consequências: nova migration; permissões baseadas em equipe ficam para Fase 4.

### Decisão 6 — Uploads em disco local

- Contexto: evidências fotográficas precisam de storage, mas integração S3 traz custo de setup.
- Escolha: armazenamento local em disco com URL pública via `UPLOAD_BASE_URL`.
- Motivo: funciona end-to-end sem dependência de serviço externo no desenvolvimento.
- Consequências: migração para S3/R2 requer apenas trocar o bloco de escrita no router de uploads.

## 11. Riscos e Trade-offs

- O que foi simplificado intencionalmente:
  - offline não implementado no MVP
  - sem policy engine de permissões granulares
  - uploads em disco (não S3)
  - score calculado apenas sobre campos booleanos
- O que precisa nascer desacoplado (e está):
  - autenticação e empresa ativa
  - formulários versionados
  - inspeção separada do template
  - anexos desacoplados do banco binário
- Riscos arquiteturais monitorados:
  - acoplamento do frontend direto em formato interno do banco
  - crescer com campos dinâmicos sem contrato claro (`config_json`)
  - ignorar company isolation nas queries (mitigado: `membership.company_id` obrigatório em todas as queries de domínio)
  - snapshot `answers_json` dessincronizado de `submission_values` (risco se commits parciais ocorrerem)

## 12. Status do Roadmap

### Fase 1 — Fundação ✅

- estrutura do monorepo
- configuração de backend e frontend
- banco e migrations
- auth básica (JWT + PBKDF2)
- contexto de empresa (X-Company-Id)
- envelope de resposta
- tratamento de erros padronizado (RFC 7807)

### Fase 2 — Domínio Core ✅

- módulo de formulários com versionamento
- módulo de inspeções com respostas tipadas
- upload de arquivos de evidência
- listagem paginada e detalhamento

### Fase 3 — Robustez ✅

- 85 testes de integração (backend)
- 25 testes de unidade (frontend)
- dashboard com métricas de inspeções
- módulo de equipes (CRUD + membros)
- paginação refinada em todos os módulos
- correção de reidratação de usuário após refresh
- encoding correto em toda a UI

### Fase 4 — Evolução (pendente)

- permissões baseadas em equipe
- exportação PDF/CSV
- analytics avançado por empresa
- offline-first
- sync engine
- plano de ação corretiva
- notificações
