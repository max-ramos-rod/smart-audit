# START HERE — Guia para IAs no Smart Audit

Você é uma IA prestes a trabalhar no **Smart Audit**. Leia este arquivo primeiro; ele
aponta para os demais guias e resume o essencial verificado no código.

## O que é o projeto

Plataforma web **multiempresa** para execução de checklists, auditorias e inspeções
operacionais, com formulários versionados, score ponderado por conformidade, evidências
(anexos) e exportação PDF/CSV. SaaS com empresa ativa resolvida por contexto.

## Layout do repositório (monorepo)

- `backend/` — FastAPI (Python 3.12), SQLAlchemy 2.0 **async** (`asyncpg`), Alembic, PostgreSQL. Porta `8003`.
- `frontend/` — Vue 3 SPA (Vite, Pinia, Vue Router, Axios, Tailwind CSS v4). Servido sob a base `/app/`. Porta dev `5174`.
- `landing/` — landing institucional estática na raiz `/`.
- `docs/` — documentação canônica (ver abaixo).
- `backend/alembic/versions/` — migrations (schema canônico).
- `docker-compose.yml` — `db` + `backend` + `frontend`.

## Ordem de leitura recomendada

1. **`CLAUDE.md`** (raiz) — instruções operacionais do projeto. **Autoritativo.**
2. **`docs/Arquitetura_Smart_Audit.md`** — bounded contexts, rotas, contratos, decisões.
3. **`docs/DER_Smart_Audit.md`** — modelo de dados (tabelas, constraints, relacionamentos).
4. **`docs/Deploy_Smart_Audit.md`** — topologia Docker/Nginx, base `/app/`, SMTP, onboarding.
5. **`docs/AUDIT_REPORT.md`** — auditoria documentação × código (divergências e decisões implícitas).
6. Os guias deste diretório:
   - **`AI_RULES.md`** — regras invioláveis (faça/não faça).
   - **`AI_MODELS.md`** — mapa do modelo de dados.
   - **`AI_WORKFLOWS.md`** — comandos e receitas (rodar, testar, adicionar coisas).
   - **`AI_DECISIONS.md`** — decisões arquiteturais (explícitas e implícitas).

## Stack verificada

| Camada | Tecnologias |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0 async + asyncpg, Alembic, PostgreSQL, slowapi, fpdf2 |
| Frontend | Vue 3, Pinia, Vue Router, Tailwind CSS v4, Axios, Vitest, Playwright |
| Auth | JWT bearer + PBKDF2-SHA256 customizado (`backend/app/core/security.py`) |
| Uploads | disco local (`settings.upload_dir/<company_id>/<uuid>.<ext>`) |

## Os 7 fatos que mais importam

1. **Fluxo de camadas obrigatório:** `api → service → repository → db`. Endpoints são finos.
2. **Tudo é async.** `db.add()`/`db.add_all()` são síncronos; o resto exige `await`. **Sem lazy loading** — use `selectinload`.
3. **Multiempresa:** toda query de domínio filtra por `membership.company_id`. Header `X-Company-Id`.
4. **Envelope de resposta:** `{ data, meta }`; erros em **RFC 7807**. Não quebre o formato.
5. **Score** vem de `submission_conformities` (ponderado), não de `submission_values`.
6. **Não recrie** os tipos de campo removidos (`photo`, `evidence`). Evidência é capacidade via `attachments`.
7. **Git:** só comite/pushe quando pedido; se estiver em `main`, crie branch antes.

## Papéis (roles)

`OWNER` · `ADMIN` · `MANAGER` · `INSPECTOR` · `VIEWER` — ver matriz de RBAC em `AI_RULES.md` e
em `docs/Arquitetura_Smart_Audit.md` §4.

> Regra de ouro deste diretório: **só documente o que está verificado no código.** Se algo
> não foi confirmado, marque como não verificado em vez de afirmar.
