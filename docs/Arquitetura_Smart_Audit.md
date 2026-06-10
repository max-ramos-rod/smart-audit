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
- Frontend: Vue 3, Pinia, Vue Router, Tailwind CSS v4, Axios, Vitest, Playwright — porta `5174` (dev); em producao o SPA e servido sob a base `/app/`
- Landing page institucional estatica (`landing/index.html`) servida na raiz `/` do dominio
- Uploads: armazenamento local em disco
- Deploy: Docker Compose (db + backend + frontend) atras de proxy reverso Nginx e Cloudflare Tunnel — ver `docs/Deploy_Smart_Audit.md`
- CI: GitHub Actions com jobs separados para backend, frontend (Vitest) e E2E (Playwright)

Baseline validado em `2026-06-09`:

- backend: `220 passed`
- frontend Vitest: `122 passed`
- frontend build: `npm run build` OK
- E2E Playwright: `54 testes` (todos mockados, sem backend necessario)

## 2. Estado real do produto

O Smart Audit ja nao esta mais em fase apenas de fundacao. O estado atual do codigo mostra:

- autenticacao JWT funcional
- recuperacao de senha completa (forgot-password + reset via token com TTL de 1h)
- infraestrutura de e-mail com provider abstraction (SMTP/console), templates HTML+texto e metodos semanticos
- convite de usuario por e-mail (onboarding intra-empresa): o convidado define a propria senha pelo link
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
- modo de inspecao com dois overlays fullscreen (card a card com swipe + lista compacta com filtros)
- barra de progresso segmentada, legenda de cores e atalhos rapidos por secao na execucao da inspecao
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

- `POST /api/v1/auth/login` — rate limit `10/minute` (slowapi)
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/forgot-password` — gera token com TTL 1h, entrega via SMTP ou log; rate limit `5/minute`
- `POST /api/v1/auth/reset-password` — valida token, troca senha, marca token como usado; rate limit `10/minute`
- `GET /api/v1/me/companies`
- `GET /api/v1/me/context`
- `PATCH /api/v1/me`
- `GET /api/v1/me/stats` — retorna metricas por periodo com `score_by_form` e `score_trend`
- `GET /api/v1/me/usage` — contagens reais de uso vs limites do plano (`users`, `forms`, `submissions_this_month`)
- `GET /api/v1/me/notifications` — derivadas de submissions; retorna `read: bool` (derivado da existencia de linha nao-dispensada em `notification_reads`); notificacoes dispensadas sao omitidas da resposta
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
- `GET /api/v1/users/revoked` — lista memberships revogados (`revoked_at IS NOT NULL`)
- `GET /api/v1/users/{id}`
- `POST /api/v1/users` — cria usuario com senha inicial e vincula via membership
- `POST /api/v1/users/invite` — convida usuario por e-mail (sem senha): cria usuario com senha aleatoria inutilizavel, vincula via membership, gera token e envia link
- `PATCH /api/v1/users/{id}` — atualiza nome, senha, role, `is_active` do usuario
- `DELETE /api/v1/users/{id}` — revoga o acesso do usuario (seta `revoked_at`); nao exclui dados
- `POST /api/v1/users/{id}/reactivate` — reativa membership revogado

Todas as rotas de usuarios exigem ADMIN ou superior (`get_admin_membership`).

Convite de usuario (onboarding intra-empresa):

- o convidado nao consegue logar ate definir a propria senha pelo link
- o link reaproveita a tabela `password_reset_tokens` e o endpoint `POST /auth/reset-password` (mesma tela do reset), com TTL configuravel (`invite_token_ttl_hours`, default 72h)
- audit log: `user.invited`
- so resolve o onboarding *dentro* de uma empresa existente; o primeiro usuario (OWNER) de uma empresa nova ainda e provisionado por script (ver `docs/Deploy_Smart_Audit.md`)

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
| `weight` | `float` | qualquer campo (exceto `section`) | Peso no calculo do score ponderado (default 1.0); o motor de score le `weight` de qualquer campo com conformidade, mas o builder UI so expoe o ajuste em `boolean` |
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
- score_breakdown: `conformes`, `nao_conformes`, `sem_resposta`, `total_boolean`, `na_count` (hoje retorna sempre 0 — o calculo de N/A foi para o dominio de conformities; o campo permanece no contrato por compatibilidade)
- exportacao PDF individual com score profissional e suporte a Unicode
- exportacao CSV da lista (com filtro de status; teto de 5000 linhas, prefixo BOM UTF-8 para compatibilidade com Excel PT-BR)

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

Efeito colateral na criacao: `AttachmentService.create_attachment` tambem grava `answers_json[field_key] = file_url` no snapshot da submission, de modo que o campo aparece como respondido no armazenamento denormalizado. O `submission_value` alvo e criado on-demand se ainda nao existir.

### Uploads

Responsavel por receber arquivos e gravar em disco.

- nao existe modulo de dominio separado para uploads
- a logica fica encapsulada no router
- tipos permitidos: `image/jpeg`, `image/png`, `image/webp`, `video/mp4`, `video/quicktime`, `video/x-msvideo`, `audio/mpeg`, `audio/wav`, `audio/ogg`, `audio/mp4`, `application/pdf`
- limites por tipo: imagem 10 MB, PDF 20 MB, audio 50 MB, video 200 MB

### Email

Infraestrutura compartilhada em `backend/app/core/email/` — nenhum modulo envia e-mail com `smtplib` direto. Tres camadas:

- **`sender.py`**: protocol `EmailSender` + `SmtpEmailSender` (producao, roda o `smtplib` bloqueante via `asyncio.to_thread` e engole excecoes — envio nunca quebra o fluxo) e `ConsoleEmailSender` (dev, loga a mensagem quando `SMTP_HOST` esta vazio). `get_email_sender()` e uma factory `lru_cache` que escolhe a implementacao pelas settings.
- **`templates.py`**: funcoes puras que retornam `EmailMessage` (assunto + corpo texto + corpo HTML). `password_reset` e `user_invite`. O par multipart/alternative melhora deliverability.
- **`service.py`**: `EmailService` com metodos semanticos (`send_password_reset`, `send_user_invite`). Modulos chamam intencao, nao SMTP — mesma regra dos repositories que escondem ORM. Servicos que enviam e-mail recebem um `EmailService` opcional no `__init__` (injetavel).

Links absolutos nos e-mails usam `FRONTEND_URL` (ja inclui o base `/app`) — sem `/app` hardcoded. Variaveis SMTP: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` (nomes exatos; `SMTP_FROM` deve ser o endereco autenticado). Ver `docs/Deploy_Smart_Audit.md`.

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

### Ativos (clientes, tipos e ativos)

Responsavel pelo cadastro do objeto inspecionado e suas partes (DR-0001 / ADR-0015). Tres
bounded contexts irmaos sob a mesma decisao de modelagem.

Entidades principais:

- `clients` — empresa atendida cujos ativos sao inspecionados (entidade minima)
- `asset_types` — categoria/molde de ativo, com `attributes_schema` opcional
- `assets` — objeto concreto em arvore (raiz/componentes), com `attributes_json` livre

Capacidades ativas (todas: leitura `get_current_membership`, escrita `get_manager_membership`):

- `GET/POST /api/v1/clients`, `GET/PATCH/DELETE /api/v1/clients/{id}` — CRUD + soft delete (`is_active`)
- `GET/POST /api/v1/asset-types`, `GET/PATCH/DELETE /api/v1/asset-types/{id}` — CRUD + soft delete (`is_active`); `attributes_schema` aceito livre (M1)
- `GET/POST /api/v1/assets`, `GET/PATCH/DELETE /api/v1/assets/{id}` — CRUD + arvore
  - `GET /assets` filtra por `asset_type_id`, `client_id`, `parent_asset_id`, `status`
  - `GET /assets/{id}` retorna `components` (filhos diretos)
  - `parent_asset_id` so no create (imutavel, M5); `client_id` so em raiz (M6/V3)
  - `DELETE` desativa toda a subarvore em cascata (CTE `deactivate_subtree`, V6); `PATCH status='active'` e top-down (so com pai ativo, V7)

Regras de desativacao:

- soft delete em cascata: nenhum ativo `active` pode existir sob ancestral `inactive`
- reativacao nao cascateia (preserva o estado previo de cada componente)
- auditoria `asset.created` e `asset.deactivated` (esta ultima com contagem de descendentes)

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
  - inspecoes `in_progress` ha mais de 24h geram alerta `pending` (sem piso de data)
  - `completed` finalizadas nos ultimos 30 dias com score < 80% geram alerta `low_score`
  - `completed` finalizadas nos ultimos 30 dias com score >= 90% geram alerta `excellent`
  - a query lê no maximo 50 submissions e a resposta e limitada as 20 notificacoes mais recentes
- estado de leitura derivado da existencia de linha em `notification_reads` com `dismissed = FALSE` (nao ha coluna `read`)
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

### Controle de acesso por papel (RBAC)

As rotas sao protegidas por quatro dependencias em [backend/app/modules/memberships/permissions.py](/c:/Projetos/smart-audit/backend/app/modules/memberships/permissions.py), cada uma exigindo um conjunto de papeis (alem de membership ativo na empresa, `revoked_at IS NULL`):

| Guard | Papeis permitidos |
|---|---|
| `get_current_membership` | qualquer membro ativo (OWNER, ADMIN, MANAGER, INSPECTOR, VIEWER) |
| `get_operator_membership` | OWNER, ADMIN, MANAGER, INSPECTOR |
| `get_manager_membership` | OWNER, ADMIN, MANAGER |
| `get_admin_membership` | OWNER, ADMIN |
| `get_owner_membership` | OWNER |

Aplicacao por recurso:

| Recurso | Leitura | Escrita | Guard de escrita |
|---|---|---|---|
| `companies` | qualquer membro | `PATCH` admin / `DELETE` owner | `get_admin_membership` / `get_owner_membership` |
| `users` (incl. `revoked`, `invite`, `reactivate`) | ADMIN+ | ADMIN+ | `get_admin_membership` |
| `audit-logs` | ADMIN+ | — | `get_admin_membership` |
| `forms` | qualquer membro | criar / importar / publicar versao | `get_manager_membership` |
| `teams` | qualquer membro | criar / editar / desativar / membros | `get_manager_membership` |
| `submissions` | qualquer membro | criar / answers / conformity / finish | `get_operator_membership` |
| `attachments` | qualquer membro | criar / deletar | `get_current_membership` |
| `uploads` | — | enviar arquivo | `get_current_membership` |
| `search` | qualquer membro | — | — |
| `me` (stats, usage, notifications) | qualquer membro / usuario autenticado | marcar lida / dispensar | usuario autenticado |

Notas:

- **VIEWER e somente leitura no fluxo de inspecao** (nao cria nem responde submissions — `get_operator_membership` o exclui), mas **pode enviar uploads e criar/remover anexos**, pois `uploads` e `attachments` exigem apenas membership ativo.
- `auth` (`login`, `forgot-password`, `reset-password`) e publico; `auth/me` exige apenas usuario autenticado.

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
- SPA servido sob a base `/app/` (a landing institucional ocupa a raiz `/`); base definida em `vite.config.ts` (`base: '/app/'`), `router/index.ts` (`createWebHistory('/app/')`) e `frontend/nginx.conf` (`location /app/` com rewrite) — os tres devem ficar em sincronia
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

- **Modo lista normal** (padrao, tambem para inspecoes concluidas): todos os campos em scroll; concluidas sao somente leitura; usa `InspectionFieldRow.vue`
- **Modo inspecao — card** (`viewMode = 'card'`): um campo por vez com gestos de swipe (esquerda = Nao conforme, direita = Conforme); disponivel apenas para inspecoes em andamento; renderizado via `Teleport to="body"` em overlay `.insp-fullscreen`
- **Modo inspecao — lista** (`viewMode = 'list'`): lista compacta com filtros e navegacao por secao; disponivel apenas para inspecoes em andamento; renderizado via `Teleport to="body"` em overlay `.insp-listshell`; usa `InspectionListRow.vue`

**Componentes de campo:**

- `InspectionFieldRow.vue` — modo lista normal (leitura de inspecoes concluidas e em andamento na view padrao). Props: `field`, `answer`, `conformityStatus`, `conformityJustification`, `isCompleted`, `isPendingRequired`, `evidenceAttachments`, `evidenceUploading`, `evidenceError`, `compact?`
- `InspectionListRow.vue` — modo inspecao lista (overlay `.insp-listshell`). Props: `field`, `position`, `answer`, `conformityStatus`, `conformityJustification`, `isCompleted`, `isPendingRequired`, `evidenceCount`, `isExpanded`. Linha compacta com expand inline para resposta + conformidade + evidencias

**Overlays fullscreen (Teleport):**

Ambos os overlays de inspecao (`insp-fullscreen` e `insp-listshell`) sao renderizados via `<Teleport to="body">` com `position: fixed`. No desktop (>768px) o offset `left: 248px` deixa a sidebar visivel. No mobile cobrem o viewport completo (`z-index: 200`).

**Header compartilhado (identico nos dois modos):**

- Linha 1 (`.insp-fhdr`): botao voltar + nome do formulario + toggle [Lista][Cartao] + anel de score
- Linha 2 (`.insp-fprog`): barra de progresso segmentada + counter (X/N) + legenda de cores (conformes/nao conformes/pendentes) + separador + chips (section chips no card, filter chips na lista)

**Navegacao entre modos:**

- Inspecoes em andamento entram diretamente no modo lista
- Toggle `[Lista][Cartao]` disponivel no header de ambos os modos
- Botao voltar no card mode retorna ao modo lista (nao sai da inspecao)

**Filter chips (modo lista):** `Todos`, `Pendentes`, `Conformes`, `Nao conf.`, `S/N`, `Selecao` — filtram `filteredListFields`

Computeds relevantes:

- `answerableFields`: campos respondiveis (exclui secoes)
- `progressStats`: `{ conformes, naoConformes, pending, evaluated, total }` — fonte da barra e da legenda
- `formSections`: lista de secoes com `{ key, label, pct }` para navigation chips no card
- `filteredListFields`: campos filtrados por `listFilter` no modo lista
- `visibleSectionKeys`: set de chaves de secoes com campos visiveis no filtro atual
- `liveScore`: score calculado em tempo real (baseado em `conformityStatus` espelhando `submission_conformities`; mesma formula ponderada do backend)

## 6. Design system e front-end visual

O frontend atual ja incorporou boa parte do redesign em curso.

Base visual ativa:

- Tailwind CSS v4
- tokens CSS proprios em `style.css`
- fontes `Plus Jakarta Sans` e `DM Mono`
- shell dark sidebar + bottom nav mobile
- icones SVG centralizados

Classes CSS de inspecao:

- `.insp-fullscreen`, `.insp-listshell` — overlays fullscreen Teleport para card e lista de inspecao
- `.insp-fhdr`, `.insp-fhdr-vt`, `.insp-fhdr-vt-btn` — header linha 1 (compartilhado card e lista)
- `.insp-fback` — botao voltar do header
- `.insp-fhdr-info`, `.insp-fhdr-name`, `.insp-fhdr-sub` — bloco de nome/subtitulo do formulario
- `.insp-fprog`, `.insp-fprog-row`, `.insp-fprog-bar`, `.insp-fprog-lbl` — area de progresso linha 2 (compartilhada)
- `.insp-sec-chips`, `.insp-sec-chip`, `.insp-sec-chip--done`, `.insp-sec-chip--active`, `.insp-sec-pct` — chips de secao no card mode (dentro de `.insp-fprog`)
- `.insp-filter-bar`, `.insp-fchip` — chips de filtro no lista mode (dentro de `.insp-fprog`)
- `.score-ring`, `.score-ring-inner` — anel de score conic-gradient no header
- `.insp-list-sec-hdr`, `.insp-list-sec-ring`, `.insp-list-sec-ring-inner`, `.insp-list-sec-name`, `.insp-list-sec-cnt` — cabecalho sticky de secao no modo lista
- `.insp-list-container` — area scrollavel do modo lista (fundo cinza)
- `.insp-lsfooter`, `.insp-lsfooter-finish`, `.insp-lsfooter-err` — footer fixo do modo lista
- `.section-jump-bar`, `.section-jump-chip` — atalhos de secao no modo lista normal (leitura)
- `.section-divider` — divisor visual de secao no modo lista normal

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
- `users` (CRUD + listagem de revogados via `GET /users/revoked` + convite via `POST /users/invite` + revogacao via `DELETE /users/{id}` + reativacao)
- `forms` (CRUD, versoes, importacao via CSV/Excel)
- `submissions` (CRUD, answers, conformity, finish, export CSV, export PDF com `?inline`)
- `search`
- `teams`
- `clients` (CRUD + soft delete via `is_active`)
- `asset-types` (CRUD + soft delete; `attributes_schema` opcional aceito livre)
- `assets` (CRUD + arvore; filtros; soft delete em cascata da subarvore; reativacao top-down)
- `attachments`
- `uploads`
- `audit-logs` (`GET /api/v1/audit-logs` — lista de eventos de auditoria com filtro por acao e paginacao; requer ADMIN)

### Frontend

Rotas de interface existentes hoje:

- `/login`
- `/forgot-password`
- `/reset-password` (recebe `?token=` na query string)
- `/select-company`
- `/` — dashboard com metricas, barras de score por formulario, sparkline de tendencia
- `/users` — lista, cria (senha inicial ou convite por e-mail), edita, revoga e reativa acesso
- `/forms`
- `/forms/:formId` — editor com secoes, peso, allow_na, instrucao por campo
- `/forms/:formId/versions`
- `/submissions`
- `/submissions/:id` — execucao com modo inspecao e modo lista, progresso, atalhos de secao
- `/submissions/:id/report` — relatorio com botoes "Visualizar PDF" e "Baixar PDF"
- `/profile`
- `/company-settings` — aba Geral, aba Plano, aba Utilizacao (contagens reais via API)
- `/audit` — log de auditoria com filtro por acao e paginacao (requer ADMIN no backend via `get_admin_membership`)
- `/notifications` — com dismiss persistido
- `/search`
- `/teams` — lista, cria, edita, desativa equipes; gerencia membros
- `/clients` — lista, cria, edita, desativa e reativa clientes
- `/asset-types` — CRUD de tipos; `attributes_schema` como JSON livre
- `/assets` — cadastro raiz/componente, filhos diretos, filtros por tipo/cliente/status

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

Estado validado em `2026-06-09`:

- `220 passed`

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
| `test_users.py` | integracao | CRUD usuarios + convite (invite -> login bloqueado -> define senha -> login) |
| `test_teams.py` | integracao | CRUD equipes e membros (soft delete) |
| `test_companies.py` | integracao | configuracoes de empresa |
| `test_me.py` | integracao | context, stats, notificacoes, usage |
| `test_uploads.py` | integracao | upload, validacao de tipo e tamanho |
| `test_attachments.py` | integracao | evidencias |
| `test_audit_logs.py` | integracao | auditoria: registro de evento, filtro por acao, guard ADMIN, isolamento |
| `test_form_service.py` | unidade | validate_fields (todos os tipos) |
| `test_submission_service.py` | unidade | normalize_value, calculate_score (ponderado via conformities), score_breakdown (N/A), extract_value, parse_period_start, PDF |
| `test_form_importer.py` | unidade | parse_csv, parse_excel, parse_import_file (27 casos) |

Cobertura de auditoria: `test_audit_logs.py` cobre a rota `GET /api/v1/audit-logs` (registro de evento, filtro por acao, guard ADMIN, isolamento por empresa). O servico de auditoria do frontend tem teste em `audit.service.test.ts`.

Casos cobertos em `test_submissions_advanced.py`:

- exportacao PDF: content-type, `?inline`, secoes + N/A, 404, auth guard
- stats: `score_by_form` e `score_trend` presentes, filtro por periodo
- N/A boolean: aceitacao da resposta `"na"` e exclusao do denominador do score (campo `score_breakdown.na_count` retorna 0 por design atual)
- score ponderado via conformities: peso 3:1 gera score 75%, pesos iguais geram 50%
- isolamento multiempresa: inspector em empresa diferente ve stats zeradas

### Frontend — Vitest (unitario e de servico)

Estado validado em `2026-06-09`:

- `122 passed`

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
| `audit.service.test.ts` | service |

### E2E — Playwright

Job `e2e` no CI (`.github/workflows/ci.yml`). Todos os 54 testes usam `page.route()` para mockar chamadas de API — nao requerem backend em execucao.

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

O score nao e uma media simples. Qualquer campo respondivel (todos os tipos exceto `section`) pode receber avaliacao de conformidade e `config_json.weight` (default 1.0). O score e calculado a partir de `submission_conformities`:

```
score = sum(weight_i para status='conforme') / sum(weight_i para avaliados) * 100
```

onde `avaliados` inclui todos os campos com registro em `submission_conformities` (o CHECK constraint garante `status IN ('conforme', 'nao_conforme')`). Campos sem registro de conformidade — incluindo respostas N/A em `submission_values`, que nao geram conformity — nao entram no denominador.

A separacao entre resposta (em `submission_values`) e avaliacao de conformidade (em `submission_conformities`) permite que o inspetor responda campos e decida a conformidade em etapas distintas durante a inspecao.

Observacao: o campo `score_breakdown.total_boolean` mantem o nome por compatibilidade, mas conta todos os campos nao-section (nao apenas booleanos).

### Soft delete por tipo de entidade

O sistema distingue dois mecanismos de soft delete conforme a semântica da entidade:

- **`memberships.revoked_at TIMESTAMPTZ NULL`** — timestamp de quando o acesso foi revogado. Todas as queries que dependem de membership ativo filtram `WHERE revoked_at IS NULL`: listagem de usuarios da empresa, resolucao de contexto, autenticacao (dependencias `get_current_membership`), e contagem de membros ativos em `/me/usage`.

- **`teams.is_active BOOLEAN`** — flag booleana para equipes. Listagem e detalhe de equipes filtram `WHERE is_active = TRUE`. Operacoes de membro em equipes inativas retornam 404. O `DELETE /teams/{id}` HTTP realiza desativacao em vez de exclusao fisica.

Dados historicos (inspecoes, respostas, evidencias, membros de equipe) sao preservados em ambos os casos.

### Notificacoes sem tabela propria

As notificacoes sao derivadas do estado das submissions em tempo real. Nao existe tabela `notifications` no banco.

O estado de leitura e dismiss e persistido em `notification_reads` (coluna `dismissed: bool`; nao ha coluna `read` — "lida" e derivada da existencia de uma linha com `dismissed = FALSE`; chave composta `user_id + notification_key`). A chave e deterministica — ex.: `excellent-{submission_id}` — o que permite upsert sem conflito. Notificacoes dispensadas sao filtradas antes de retornar ao cliente.

### PDF com fonte DejaVu Sans TTF

O PDF e gerado com fpdf2 usando a fonte DejaVu Sans TTF embutida em `backend/app/modules/submissions/fonts/`. Essa fonte cobre Unicode completo, incluindo todos os acentos do portugues, simbolos especiais e caracteres internacionais. O arquivo TTF (~757 KB) esta versionado no repositorio.

### Recuperacao de senha

Implementada com token de uso unico (TTL 1h) em `password_reset_tokens`. Entrega via `EmailService` (SMTP quando configurado, ou log em desenvolvimento). Anti-enumeracao: o endpoint sempre retorna 200 independente de o email existir.

### Email como infraestrutura compartilhada

O envio de e-mail vive em `backend/app/core/email/` (sender + templates + service), nao espalhado pelos modulos. Provider abstraction via protocol `EmailSender` permite trocar o transporte (SMTP -> Resend/SES) sem tocar nos chamadores. `SmtpEmailSender` roda o `smtplib` bloqueante via `asyncio.to_thread` e e fail-soft (excecoes logadas, nunca propagadas). Ver secao "Email" em Bounded contexts.

### Convite de usuario reaproveita o reset de senha

O convite (`POST /users/invite`) cria o usuario com senha aleatoria inutilizavel e gera um token na **mesma** tabela `password_reset_tokens`, com TTL maior (`invite_token_ttl_hours`, default 72h). O convidado define a senha pelo **mesmo** endpoint e tela do reset. Isso evita um fluxo de "ativacao" separado — uma unica maquina de tokens serve reset e convite. O onboarding cross-empresa (primeiro OWNER) permanece manual (script), pois nenhum membership pode autoriza-lo.

### Upload local antes de storage externo

Mantido e coerente com o momento do projeto.

### Backend async

Ja e realidade no codigo. Qualquer documentacao antiga que ainda fale em sessao sincrona deve ser considerada obsoleta.

### Modelo de ativos genericos (ADR-0015)

O objeto inspecionado e modelado sem tabela por dominio: `asset_types` (molde), `assets`
(instancia em arvore) e `clients` (dono externo). Um componente **e** um `asset` com
`parent_asset_id` preenchido — colapsa "ativo" e "componente" numa adjacency list de
profundidade livre; a cardinalidade real e decidida na instancia, nao no tipo. O dono e
discriminado por `assets.client_id` nullable (NULL = patrimonio proprio), sem `owner_kind`.
A Fase 1 (DR-0001) entregou o nucleo: CRUD dos tres contextos, soft delete em cascata da
subarvore (CTE recursiva) e reativacao top-down. Ficaram para fase posterior o blueprint de
composicao entre tipos (`asset_type_components`) e a validacao de `attributes_schema`
(atributos aceitos livres, M1). Ver ADR-0015 e `docs/specs/SPEC-DR-0001-Fase1-Ativos.md`.

## 11. O que esta consolidado vs. parcial

### Consolidado

- backend principal e contratos HTTP
- autenticacao, contexto e sessao
- recuperacao de senha (forgot + reset)
- infraestrutura de e-mail (`core/email/`: provider abstraction, templates HTML+texto, metodos semanticos)
- convite de usuario por e-mail (`POST /users/invite`) com botao na tela `/app/users`
- shell autenticado consistente em todas as telas
- usuarios com desativacao (`is_active`), revogacao (`DELETE /users/{id}`) e reativacao (`POST /users/{id}/reactivate`)
- formularios com versionamento, secoes, tipos completos e config_json
- campo `instruction` por campo de formulario (builder UI + importacao)
- importacao de formulario via CSV ou Excel (`POST /api/v1/forms/import`)
- inspecoes com score ponderado, N/A, modo inspecao card e lista
- avaliacao de conformidade por campo (`submission_conformities`) — base do score e da barra de progresso
- comportamento de avanco automatico apenas no botao "Conforme" (card view)
- redesign UX do modo de inspecao: overlays fullscreen Teleport, header unificado com legenda de cores, filter chips no modo lista, `InspectionListRow.vue` como componente compacto de linha
- finalizacao com validacao de campos visiveis
- relatorio e exportacao PDF profissional (score colorido, breakdown, secoes, Unicode via DejaVu Sans)
- evidencias e uploads (imagem, video, audio, PDF)
- equipes com soft delete (`is_active`)
- ativos genericos (DR-0001/ADR-0015): `clients`, `asset_types`, `assets` em arvore; soft delete em cascata da subarvore e reativacao top-down; telas `/clients`, `/asset-types`, `/assets`
- memberships com soft delete (`revoked_at`) e reativacao
- desativacao de empresa (`DELETE /companies/me`) com cascade de memberships e equipes; modal de confirmacao com digitacao do nome + logout automatico
- audit_logs: tabela imutavel, bounded context completo, eventos company.deactivated / membership.revoked / membership.reactivated / user.created / user.invited / team.deactivated; view com filtro e paginacao
- exportacao CSV
- busca em tempo real
- dashboard com score_by_form e score_trend
- configuracoes da empresa (GET + PATCH com guard de role)
- perfil (nome, senha, empresas vinculadas)
- notificacoes com persistencia de leitura e dismiss
- endpoint `/me/usage` com contagens reais e limites por plano
- CI com jobs separados: backend (ruff + pytest), frontend (vue-tsc + Vitest), E2E (Playwright)
- testes automatizados: backend 252 passed, frontend 165 passed (Vitest), 68 E2E (Playwright)

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
