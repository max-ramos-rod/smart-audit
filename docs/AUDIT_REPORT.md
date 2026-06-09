# Relatório de Auditoria — Smart Audit

> Documento gerado por análise comparativa entre documentação e implementação real.
> **Data:** 2026-06-08 · **Escopo:** backend, frontend, migrations e testes × `README.md`,
> `CLAUDE.md`, `docs/Arquitetura_Smart_Audit.md`, `docs/DER_Smart_Audit.md`, `docs/Deploy_Smart_Audit.md`.
> **Regra (geração original):** somente leitura — nenhum arquivo foi alterado pela auditoria.
>
> **Atualização 2026-06-09:** os achados acionáveis foram resolvidos em commits posteriores.
> As seções originais abaixo são preservadas para rastreabilidade e cada uma recebeu um marcador
> de status. Resumo em "Status de resolução".

## Método e observações de escopo

- Fontes de documentação efetivamente encontradas: `README.md` (raiz), `CLAUDE.md` (raiz) e
  `docs/` (`Arquitetura_Smart_Audit.md`, `DER_Smart_Audit.md`, `Deploy_Smart_Audit.md`).
- **`PROMPT.md` não existe** no repositório (solicitado na auditoria, porém ausente).
- Baseline de testes declarado: backend `216 passed`, frontend Vitest `119 passed`, E2E Playwright `54`.
  O Vitest foi reexecutado nesta análise: **119 passed** (confirmado). Backend e E2E não foram
  reexecutados; os números são tratados como baseline declarado.
- Estrutura real de testes: 13 integração + 3 unidade (backend), 19 arquivos Vitest, 8 specs E2E.

---

## Status de resolução (2026-06-09)

Pós-auditoria, os itens acionáveis foram corrigidos:

| Item | Status | Onde foi resolvido |
|---|---|---|
| §2.1 escopo de `weight` (contradição interna) | ✅ Resolvido | tabelas de `config_json` na Arquitetura e DER alinhadas (commit `1b19c0c`) |
| §2.2 inventário não citava lacuna de teste | ✅ Resolvido | nota em Arquitetura §9 + `backend/tests/integration/test_audit_logs.py` criado (4 testes); resta o teste Vitest do `audit.service.ts` |
| §3 rate limits, teto CSV, teto de 50 na query, BOM, efeito do anexo | ✅ Resolvido | documentados em Arquitetura/DER (`1b19c0c`) |
| §3 RBAC (`GET /companies/me`, VIEWER) | ✅ Resolvido | matriz de RBAC na Arquitetura §4 (`2e8e33c`) |
| §4 link quebrado `redesign-handoff/README.md` | ✅ Resolvido | README aponta para a pasta (`1b19c0c`) |
| §4 `PROMPT.md` ausente | ◻️ N/A | nunca foi afirmado por documento; segue inexistente |
| §5 decisões implícitas | ✅ Resolvido | catalogadas em `docs/ai/AI_DECISIONS.md` e promovidas a ADRs em `docs/adr/` (`1ff79a5`) |

> Lacuna remanescente (não é de documentação): o backend já tem `test_audit_logs.py` (4 testes,
> backend total 220 passed); resta apenas o teste Vitest do `audit.service.ts` no frontend.

---

## 1. Documentação correta

Itens em que documentação e código estão alinhados e foram verificados nesta auditoria.

| Tema | Evidência no código | Documento |
|---|---|---|
| Arquitetura em camadas `api → service → repository → db` | estrutura `backend/app/modules/*/{service,repository,schemas}.py` | Arquitetura §4, README |
| Envelope `{ data, meta }` + RFC 7807 | `backend/app/core/responses.py`, `core/errors.py` | Arquitetura §8 |
| Multi-tenancy por `X-Company-Id`/membership | `modules/memberships/dependencies.py` | CLAUDE.md, Arquitetura |
| Soft delete `memberships.revoked_at` / `teams.is_active` | `companies/repository.py:deactivate_company`, `teams/service.py` | DER, Arquitetura |
| Versionamento de formulários imutável | `forms/service.py:publish_new_version` | Arquitetura §10, DER |
| Modelo híbrido de respostas (`submission_values` + `answers_json`) | `submissions/service.py:save_answers` | DER, Arquitetura |
| Tipos de campo `boolean/text/number/date/select/section` + N/A `value_text="na"` | `submissions/service.py:normalize_value/extract_value` | DER, Arquitetura |
| Score ponderado via `submission_conformities` | `submissions/service.py:calculate_score` | Arquitetura §10 |
| `score_breakdown` com `na_count` sempre 0 | `submissions/service.py:calculate_score_breakdown` | Arquitetura §3 |
| `audit_logs` imutável (sem `updated_at`), 6 ações, sem CASCADE | `db/models/audit_logs.py`, migration `b0c1d2e3f4a5` | DER |
| Notificações sem tabela própria; "lida" derivada de linha `dismissed=FALSE` | `notifications/repository.py:get_read_keys` | DER, Arquitetura *(corrigido nesta sessão)* |
| RBAC por 4 guards (owner/admin/manager/operator) | `memberships/permissions.py` | Arquitetura §4 *(adicionado nesta sessão)* |
| Janela de notificações: pending +24h, completed últimos 30 dias, cap 20 | `submissions/repository.py:list_for_notifications`, `service.py:get_notifications` | Arquitetura/DER *(adicionado nesta sessão)* |
| Migrations (16) listadas | `backend/alembic/versions/*` | DER §Migrações |
| Limites por plano (10/20/100, 50/100/500, 999/999/9999) | `companies/service.py:_PLAN_LIMITS` | Arquitetura §3 |
| Convite reaproveita `password_reset_tokens` (TTL 72h) | `users/service.py:invite_user`, `core/config.py:invite_token_ttl_hours` | Arquitetura §3, DER |
| Reset de senha TTL 1h + anti-enumeração | `auth/service.py:request_password_reset` | Arquitetura §10 |
| Uploads: tipos/limites (img 10MB, PDF 20MB, áudio 50MB, vídeo 200MB) | `api/v1/routers/uploads.py` | Arquitetura §3, DER |
| Base `/app/` em 3 pontos sincronizados | `vite.config.ts`, `router/index.ts`, `nginx.conf` | Deploy |
| Rotas de frontend | `frontend/src/router/index.ts` | Arquitetura §7 |

---

## 2. Documentação desatualizada / divergente

### 2.1 `config_json.weight` descrito como exclusivo de `boolean` (contradição interna) — ✅ Resolvido

- **Código:** `calculate_score` (`submissions/service.py`) lê `field.config_json.get("weight")` para
  **qualquer** campo com registro de conformidade (todos exceto `section`), não só `boolean`.
- **Doc divergente:** a tabela de `config_json` em `Arquitetura_Smart_Audit.md` (§Formulários) e em
  `DER_Smart_Audit.md` (§`form_fields`) lista `weight` como aplicável apenas a `boolean`.
- **Porém** a própria decisão "Score ponderado via conformities" (Arquitetura §10) já afirma que
  *"qualquer campo respondível pode receber `config_json.weight`"*. As tabelas e a seção de decisão
  se contradizem entre si.
- **Severidade:** baixa. Na prática a UI (`FormFieldEditor.vue`) só expõe `weight` em `boolean`, então
  o efeito visível coincide com a tabela — mas o backend é mais permissivo do que as tabelas declaram.
- **Status (2026-06-09):** ✅ as tabelas de `config_json` na Arquitetura e no DER foram alinhadas
  (peso aplicável a qualquer campo exceto `section`; UI ajusta só em `boolean`).

### 2.2 Inventário de testes não cita lacunas de cobertura — ✅ Resolvido (documentação)

- A seção 9 da Arquitetura lista 16 arquivos de teste backend (confere com o disco), mas o módulo
  `audit-logs` **não possui teste dedicado** (`test_audit_logs.py` inexistente) e o serviço de
  auditoria do frontend (`audit.service.ts`) **não possui** `audit.service.test.ts`. A documentação
  apresenta a auditoria como consolidada sem registrar essa lacuna de cobertura.
- **Status (2026-06-09):** ✅ a Arquitetura §9 foi atualizada e a cobertura backend foi criada:
  `backend/tests/integration/test_audit_logs.py` (4 testes; backend total 220 passed). Resta apenas
  o teste Vitest do `audit.service.ts` no frontend.

> Observação: divergências factuais anteriores (coluna `notification_reads.read`, ausência de
> `audit-logs`/`GET /users/revoked` nas listas de rota) **já foram corrigidas** na documentação nesta
> sessão e por isso não constam mais aqui.

---

## 3. Funcionalidades implementadas sem documentação — ✅ Resolvido

> **Status (2026-06-09):** todos os itens abaixo foram documentados (rate limits, teto de 5000 no
> CSV, teto de 50 na query de notificações, BOM, efeito do anexo em `answers_json` na Arquitetura/DER)
> ou cobertos pela matriz de RBAC da Arquitetura §4 (`GET /companies/me`, VIEWER). A coluna
> "Situação na doc" reflete o estado **na época da auditoria**.

| Funcionalidade | Evidência | Situação na doc |
|---|---|---|
| Rate limits específicos dos endpoints de auth (`login` 10/min, `forgot-password` 5/min, `reset-password` 10/min) | `api/v1/routers/auth.py` (`@limiter.limit(...)`) | CLAUDE.md cita slowapi genericamente; limites por rota não documentados |
| Teto de 5000 linhas na exportação CSV | `submissions/repository.py:list_all_for_export` (`.limit(5000)`) | Não documentado |
| Teto de 50 registros na query de notificações antes do corte de 20 | `submissions/repository.py:list_for_notifications` (`.limit(50)`) | Documentado o cap de 20; o teto de 50 da query é parcial |
| BOM UTF-8 prefixado no CSV (compatibilidade Excel PT-BR) | `submissions/service.py:export_csv` (`b"\xef\xbb\xbf"`) | Não documentado |
| Efeito colateral do anexo: grava `answers_json[field_key] = file_url` | `attachments/service.py:create_attachment` | Em CLAUDE.md; ausente na prosa de Arquitetura/DER |
| `GET /companies/me` legível por qualquer membro; escrita gated por role | `api/v1/routers/companies.py` | Coberto após inclusão da matriz RBAC nesta sessão |
| VIEWER pode fazer upload e criar/remover anexos (apesar de não responder inspeções) | `uploads.py`/`attachments.py` usam `get_current_membership` | Documentado após inclusão da nota de RBAC nesta sessão |

---

## 4. Documentação que descreve funcionalidades inexistentes — ✅ Resolvido

> **Status (2026-06-09):** ✅ o link do `README` foi corrigido para apontar para a pasta
> `redesign-handoff/` (que existe). `PROMPT.md` segue inexistente, mas nunca foi afirmado por
> nenhum documento — não é acionável.

| Afirmação na documentação | Realidade | Arquivo |
|---|---|---|
| Link para `redesign-handoff/README.md` ("handoff visual") | A pasta `redesign-handoff/` existe, mas **não contém `README.md`** (só `.html` e `deck-stage.js`); o link está quebrado | `README.md` (seção Documentação) |
| (Solicitação da auditoria) `PROMPT.md` como fonte | **Arquivo inexistente** no repositório | — |

> Itens factuais anteriores que descreviam comportamento inexistente — notadamente a coluna
> `notification_reads.read` — **já foram removidos** da documentação nesta sessão.

Nenhuma outra rota, entidade ou capacidade declarada na documentação foi encontrada como inexistente:
`corrective_actions` e storage externo (S3/R2) estão corretamente marcados como **evolução futura**,
e o botão "Falar com o comercial" sem ação está corretamente registrado como **limitação conhecida**.

---

## 5. Decisões arquiteturais implícitas encontradas no código — ✅ Resolvido

> **Status (2026-06-09):** ✅ estas decisões foram tornadas explícitas — todas catalogadas em
> `docs/ai/AI_DECISIONS.md` e as estruturais registradas como ADRs em `docs/adr/`. O `field_type`
> validado pela CHECK também foi anotado no DER.

Decisões reais embutidas na implementação, não declaradas explicitamente como decisão na documentação
(ou apenas tangenciadas).

1. **`field_type` validado apenas pela CHECK constraint do banco.** O schema `FormFieldCreateRequest`
   usa `field_type: str` livre e `FormService.validate_fields` não valida o tipo contra a enumeração
   permitida — a barreira efetiva é o `CHECK` em `form_fields` (migrations). Validação de domínio
   delegada à camada de persistência.

2. **`weight` é uma capacidade latente de qualquer campo respondível.** O backend pondera score por
   `config_json.weight` em qualquer campo não-`section` com conformidade; a restrição a `boolean` é
   apenas convenção da UI/tabelas de doc, não do motor de cálculo (ver §2.1).

3. **`create_submission` sempre usa a maior versão do formulário** (`max(form.versions, key=version)`
   em `submissions/service.py`), sem filtrar `status='published'`. Funciona porque toda versão é criada
   como `published`; não há suporte a rascunho de versão não publicada no fluxo atual.

4. **Upload e anexo são responsabilidades separadas e o upload não tem persistência própria.**
   `POST /uploads` grava o arquivo em disco e devolve URL, mas **não cria registro em banco**; a
   persistência de metadados só ocorre quando o cliente chama `POST .../attachments`. O vínculo é
   sempre com `submission_value` (criado on-demand), nunca direto com a submission.

5. **"Lida" como existência de linha não-dispensada.** Não há coluna booleana de leitura; o par
   (lida/dispensada) é codificado por presença de linha + `dismissed`. Consequência de design: não é
   possível representar "li mas não dispensei" e "dispensei sem ler" como estados ortogonais
   (já documentado após correção nesta sessão).

6. **Faixa de score sem notificação.** Os limiares de notificação (`< 80` → `low_score`, `>= 90` →
   `excellent`) deixam a faixa **80–89,99% silenciosa** por design.

7. **Isolamento de teste por savepoint, `populate_existing=True`, `expire_on_commit=False`.** Decisões
   de infraestrutura de teste async documentadas em CLAUDE.md, porém ausentes da Arquitetura/DER —
   são decisões arquiteturais de fato (correção pós-mutação depende de `populate_existing`).

8. **`X-Company-Id` opcional para usuário com membership único.** Resolução de tenant tolerante a
   ausência de header quando há exatamente uma empresa (`memberships/dependencies.py`).

9. **Envio de e-mail fail-soft.** `SmtpEmailSender` roda `smtplib` via `asyncio.to_thread` e engole
   exceções — o fluxo HTTP nunca quebra por falha de SMTP (documentado em Arquitetura §Email, reforçado
   aqui como decisão transversal que sustenta o anti-enumeração do reset).

---

## Síntese

- **Aderência geral alta**, agora ainda maior: todos os achados de documentação foram resolvidos.
- **Divergências (§2.1, §4):** ✅ resolvidas — tabelas de `weight` alinhadas e link do README corrigido.
- **Lacunas de documentação (§2.2, §3):** ✅ resolvidas — detalhes operacionais (rate limits, tetos de
  CSV/query, BOM, efeito do anexo) e RBAC documentados.
- **Decisões implícitas (§5):** ✅ promovidas a explícitas em `docs/ai/AI_DECISIONS.md` e `docs/adr/`.
- **Cobertura de teste do `audit-logs`:** backend coberto por `test_audit_logs.py` (4 testes); resta
  apenas o teste Vitest do `audit.service.ts` no frontend — único item ainda aberto (cobertura, não doc).
