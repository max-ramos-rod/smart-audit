# Architecture Decision Records — Smart Audit

Registro das decisões arquiteturais **reais**, identificadas por análise do código
(`backend/app/**`, migrations e frontend). Cada ADR segue o formato: **Contexto · Decisão ·
Consequências · Alternativas descartadas**.

ADRs com status **Aceita** descrevem decisões vigentes no código. ADRs com status **Proposta**
registram decisões acordadas mas ainda não implementadas — tipicamente originadas de um Design
Record em [`docs/design-records/`](../design-records/README.md); ao implementar, mudam para
**Aceita** e passam a citar os pontos do código que as sustentam.

Novos ADRs partem de [`template.md`](template.md). Registro inicial em 2026-06-08.

## Ciclo de vida (Status)

- **Proposta** — em discussão, ainda não implementada.
- **Aceita** — implementada e vigente no código.
- **Supersedida** — substituída por outro ADR. Não apagar: mudar o status e preencher
  `Superseded-by` aqui e no ADR; o ADR novo preenche `Supersedes`.
- **Descartada** — avaliada e não adotada.

Ao mudar o status de um ADR (ou criar um que substitui outro), **atualize esta tabela e os
campos `Supersedes`/`Superseded-by` no cabeçalho dos ADRs envolvidos**.

## Índice

| ADR | Decisão | Status | Supersedes | Superseded-by |
|---|---|---|---|---|
| [0001](0001-arquitetura-em-camadas.md) | Arquitetura em camadas e fronteira de transação (commit no service, flush no repository) | Aceita | — | — |
| [0002](0002-backend-assincrono.md) | Backend assíncrono fim-a-fim (SQLAlchemy 2.0 + asyncpg), sem lazy loading | Aceita | — | — |
| [0003](0003-multi-tenancy-memberships.md) | Multi-tenancy por `memberships` N:N com empresa ativa via `X-Company-Id` | Aceita | — | — |
| [0004](0004-rbac-por-guards.md) | Autorização por guards hierárquicos de papel (RBAC) | Aceita | — | — |
| [0005](0005-versionamento-imutavel-de-formularios.md) | Versionamento imutável de formulários | Aceita | — | — |
| [0006](0006-modelo-hibrido-de-respostas.md) | Modelo híbrido de respostas (relacional + snapshot JSON) | Aceita | — | — |
| [0007](0007-config-json-extensao-de-campo.md) | Configuração de campo via `config_json` (JSONB) | Aceita | — | — |
| [0008](0008-score-via-conformities.md) | Score ponderado a partir de `submission_conformities` | Aceita | — | — |
| [0009](0009-soft-delete-por-semantica.md) | Soft delete por semântica da entidade (`revoked_at` vs `is_active`) | Aceita | — | — |
| [0010](0010-notificacoes-derivadas.md) | Notificações derivadas sem tabela própria | Aceita | — | — |
| [0011](0011-contrato-http-envelope-rfc7807.md) | Contrato HTTP: envelope `{data, meta}` + erros RFC 7807 | Aceita | — | — |
| [0012](0012-hash-de-senha-pbkdf2.md) | Hash de senha PBKDF2-SHA256 customizado | Aceita | — | — |
| [0013](0013-email-infra-fail-soft.md) | E-mail como infraestrutura compartilhada fail-soft | Aceita | — | — |
| [0014](0014-convite-reaproveita-reset-de-senha.md) | Convite de usuário reaproveita a máquina de reset de senha | Aceita | — | — |
| [0015](0015-modelo-de-ativos-genericos.md) | Modelo de ativos genéricos (árvore de componentes + `client_id` discriminador) | Aceita | — | — |
| [0016](0016-inspecao-por-componente-revisao-modelo-hibrido.md) | Inspeção por componente: dimensão `asset_id` no modelo híbrido (revisa 0006) | Proposta | — | — |

> Decisões de granularidade mais fina (tetos de CSV, janela de notificações, isolamento de
> testes, `field_type` validado pela CHECK, etc.) estão catalogadas em
> [`docs/ai/AI_DECISIONS.md`](../ai/AI_DECISIONS.md).
