# AI_RULES — Regras invioláveis

Regras derivadas de `CLAUDE.md` e **confirmadas no código**. Quebrar qualquer uma delas
quebra testes ou contratos. Os caminhos citados existem no repositório.

## Arquitetura em camadas

- **`api → service → repository → db`.** Routers (`backend/app/api/v1/routers/`) só parseiam
  request, resolvem dependências, chamam um método de service e serializam via
  `success_response`/`paginated_response` (`backend/app/core/responses.py`).
- **Regra de negócio fica no service**, persistência no repository.
- **Services commitam; repositories dão flush.** `repository._save`/`_save_many`
  (`backend/app/core/repositories.py`) chamam `db.flush()`; o `db.commit()` é do service.
  **Nunca** commitar dentro de repository.
- **Repositories expõem métodos nomeados de criação** (`create_team`, `create_member`,
  `create_submission`, …). Services **não** chamam `_save` diretamente.

## Async SQLAlchemy

- `db.add()` e `db.add_all()` são **síncronos** (sem `await`). Tudo o mais exige `await`:
  `flush`, `commit`, `delete`, `get`, `scalar`, `scalars`, `execute`.
- **Sem lazy loading** — async levanta `MissingGreenlet`. Relacionamentos acessados após a
  query precisam de `selectinload` (ou `joinedload`) na mesma query. Aninhados:
  `.options(selectinload(A.bs).selectinload(B.cs))`.
- Métodos de leitura base (`_get_one`, `_list_from_stmt`) usam `populate_existing=True`.
  **Não remova** — sem isso, FKs setadas como string no objeto não são recarregadas como
  `uuid.UUID` e o `selectinload` falha silenciosamente.
- `DATABASE_URL` **deve** usar driver `asyncpg` (`postgresql+asyncpg://…`). `psycopg` não
  está instalado — não readicione.

## Contratos HTTP

- Sucesso: `{ "data": ..., "meta": {...} }`. Paginação usa `PageMeta`
  (`backend/app/core/pagination.py`). Erros: **RFC 7807** (`application/problem+json`,
  `backend/app/core/errors.py`).
- **Todo campo `str` de request schema usa `Field(min_length=..., max_length=...)`.**
  Nunca `name: str` puro.
- Routers serializam com `model_dump(mode="json")` (UUID/datetime viram string).

## Multi-tenancy e RBAC

- Toda query de domínio filtra por `membership.company_id`. Empresa ativa resolvida por
  `X-Company-Id` (`backend/app/modules/memberships/dependencies.py`); opcional se o usuário
  tem exatamente 1 membership, obrigatório se tem mais de 1.
- **Guards de papel** (`backend/app/modules/memberships/permissions.py`):

  | Guard | Papéis | Usado em (escrita) |
  |---|---|---|
  | `get_current_membership` | qualquer membro ativo | leituras; `attachments`; `uploads`; `search` |
  | `get_operator_membership` | OWNER, ADMIN, MANAGER, INSPECTOR | `submissions` (create/answers/conformity/finish) |
  | `get_manager_membership` | OWNER, ADMIN, MANAGER | `forms` e `teams` (escrita) |
  | `get_admin_membership` | OWNER, ADMIN | `users/*`, `audit-logs`, `PATCH /companies/me` |
  | `get_owner_membership` | OWNER | `DELETE /companies/me` |

- **VIEWER é só leitura no fluxo de inspeção** (não cria/responde submissions), mas **pode
  fazer upload e criar/remover anexos** (esses endpoints exigem só membership ativo).
- Memberships ativos = `revoked_at IS NULL`. Filtre por isso em toda query que dependa de
  membership ativo.

## Domínio: formulários e inspeções

- **Tipos de campo válidos:** `boolean`, `text`, `number`, `date`, `select`, `section`
  (CHECK constraint em `form_fields`). **Não readicione** `photo` nem `evidence` (removidos).
- Ao **adicionar um novo tipo de campo**, atualize em
  `backend/app/modules/submissions/service.py`: `normalize_value`, `serialize_raw_value`,
  `extract_value` e (se contar no score) `calculate_score`/`calculate_score_breakdown`.
- **Publicar nova versão nunca muta a versão anterior** — cria `FormVersion` + `FormField`
  novos (`FormService.publish_new_version`). Submissions ficam presas à versão usada.
- **Resposta gravada em dois lugares** e devem ficar em sincronia: `submission_values`
  (tipado) e `submissions.answers_json` (snapshot). Ambos escritos em `save_answers`.
- **Score** sai de `submission_conformities` (não de `submission_values`).

## Segurança e infraestrutura

- Hash de senha é **PBKDF2-SHA256 customizado** (`pbkdf2_sha256$iterations$salt$digest`,
  `backend/app/core/security.py`). **Não** troque por passlib/bcrypt sem plano de migração.
- **E-mail só via `backend/app/core/email/`** (sender + templates + service). Nunca
  `smtplib` direto. Envio é fail-soft (exceções engolidas).
- Links absolutos em e-mail usam `FRONTEND_URL` (já inclui `/app`). Sem `/app` hardcoded.
- Rate limiting via `slowapi` (`backend/app/core/limiter.py`). Em testes o fixture `client`
  já desabilita — **não** desabilite manualmente em testes individuais.

## Migrations

- Escritas **à mão** (sem boilerplate de autogenerate), `id` listado primeiro. Rode do
  **repo root** (`alembic.ini` aponta para `backend/alembic`).
- `alembic.ini` tem `sqlalchemy.url` hardcoded só para o CLI local; o runtime usa
  `DATABASE_URL` do `.env` (na **raiz** do repo).

## Testes

- **Use `python -m pytest`** (nunca `pytest` puro — quebra o `sys.path`).
- Os testes exigem **PostgreSQL real migrado** (`alembic upgrade head` antes). Há isolamento
  por savepoint em `backend/tests/conftest.py`; não escreva SQL de limpeza.

## Frontend

- HTTP centralizado em `frontend/src/services/api/http.ts`. **Nunca** use `axios` direto em
  views/stores. O cliente anexa `Authorization` + `X-Company-Id` do `localStorage`.
- A base `/app/` vive em **3 lugares que devem ficar em sincronia**: `vite.config.ts`,
  `frontend/src/router/index.ts`, `frontend/nginx.conf`.
- Lógica de score/threshold só em `frontend/src/utils/score.ts` (não inline nas views).

## Git / processo

- **Só comite ou pushe quando o usuário pedir.** Se estiver em `main` (branch default),
  **crie branch antes**.
- Mensagens de commit terminam com `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Mensagens de erro do backend evitam acentos (encoding de logs).

## Governança documental (sincronização obrigatória)

Regra permanente do projeto, formalizada na
[ADR-0017](../adr/0017-modelo-unificado-de-evidencias.md) (§Governança).

- **Toda ADR usa o template oficial [`docs/adr/ADR_TEMPLATE.md`](../adr/ADR_TEMPLATE.md)** e
  **DEVE conter uma _Checklist de Sincronização Documental_.** ADRs que alterarem domínio de
  negócio, modelo de dados, contratos de API ou arquitetura de módulos preenchem e resolvem a
  checklist; as demais marcam `N/A — não altera domínio/dados/API/módulos`.
- A checklist identifica e leva à atualização, quando aplicável: ADRs · DRs · SPECs · DER ·
  diagramas arquiteturais · `CLAUDE.md` · `docs/ai/*` · planos de implementação · relatórios de
  auditoria arquitetural · qualquer documento que deixe de refletir a arquitetura vigente.
- **Definition of Done:** nenhuma implementação derivada de uma ADR é concluída enquanto a sua
  Checklist de Sincronização Documental não estiver integralmente resolvida.
- Objetivo: evitar drift entre ADR, SPEC, código e documentação operacional.
