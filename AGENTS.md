# AGENTS.md — Smart Audit

> **Shim de entrada para agentes de IA.** Este arquivo **não** contém regras próprias: ele
> redireciona para a documentação canônica em `docs/ai/`. A fonte única da verdade é o
> repositório e os documentos abaixo — não duplique o conteúdo deles aqui.

## Leia antes de qualquer implementação (ordem obrigatória)

1. [`docs/ai/START_HERE.md`](docs/ai/START_HERE.md) — orientação inicial e os fatos críticos.
2. [`docs/ai/AI_RULES.md`](docs/ai/AI_RULES.md) — regras invioláveis (camadas, async, RBAC, contratos, testes, git).
3. ADRs relevantes em [`docs/adr/`](docs/adr/README.md) — decisões arquiteturais e seus porquês.

Referência operacional do projeto: [`CLAUDE.md`](CLAUDE.md). Comandos e receitas:
[`docs/ai/AI_WORKFLOWS.md`](docs/ai/AI_WORKFLOWS.md). Modelo de dados:
[`docs/ai/AI_MODELS.md`](docs/ai/AI_MODELS.md). Decisões finas:
[`docs/ai/AI_DECISIONS.md`](docs/ai/AI_DECISIONS.md).

## Fluxo obrigatório

**Documentação → Código → Implementação.** Nunca assuma comportamento: verifique no código
real (models, services, routers, migrations) antes de implementar.

## Guardrails (apenas ponteiros — detalhes nos docs acima)

- Camadas `api → service → repository → db`; services commitam, repositories dão flush. → `AI_RULES.md`
- Backend é async; sem lazy loading, use `selectinload`. → `AI_RULES.md` / ADR-0002
- Multi-tenancy por `company_id` + `X-Company-Id`; RBAC por guards de papel. → ADR-0003 / ADR-0004
- Contrato `{ data, meta }` + erros RFC 7807. → ADR-0011
- Não readicionar os tipos de campo removidos (`photo`, `evidence`). → `AI_RULES.md`
- Testes: `python -m pytest` (backend), `npm test`/`npm run build` (frontend). → `AI_WORKFLOWS.md`
- Só comitar/pushar quando solicitado; em `main`, criar branch antes. → `AI_RULES.md`

## Ao abrir um PR

Siga o checklist anti-drift em
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) para manter código,
`docs/ai`, ADRs e documentação arquitetural sincronizados.
