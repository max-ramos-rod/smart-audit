# Architecture Decision Records — Smart Audit

Registro das decisões arquiteturais **reais**, identificadas por análise do código
(`backend/app/**`, migrations e frontend). Cada ADR segue o formato: **Contexto · Decisão ·
Consequências · Alternativas descartadas**.

Status de todos: **Aceita** (já implementada no código). Data de registro: 2026-06-08.

| ADR | Decisão |
|---|---|
| [0001](0001-arquitetura-em-camadas.md) | Arquitetura em camadas e fronteira de transação (commit no service, flush no repository) |
| [0002](0002-backend-assincrono.md) | Backend assíncrono fim-a-fim (SQLAlchemy 2.0 + asyncpg), sem lazy loading |
| [0003](0003-multi-tenancy-memberships.md) | Multi-tenancy por `memberships` N:N com empresa ativa via `X-Company-Id` |
| [0004](0004-rbac-por-guards.md) | Autorização por guards hierárquicos de papel (RBAC) |
| [0005](0005-versionamento-imutavel-de-formularios.md) | Versionamento imutável de formulários |
| [0006](0006-modelo-hibrido-de-respostas.md) | Modelo híbrido de respostas (relacional + snapshot JSON) |
| [0007](0007-config-json-extensao-de-campo.md) | Configuração de campo via `config_json` (JSONB) |
| [0008](0008-score-via-conformities.md) | Score ponderado a partir de `submission_conformities` |
| [0009](0009-soft-delete-por-semantica.md) | Soft delete por semântica da entidade (`revoked_at` vs `is_active`) |
| [0010](0010-notificacoes-derivadas.md) | Notificações derivadas sem tabela própria |
| [0011](0011-contrato-http-envelope-rfc7807.md) | Contrato HTTP: envelope `{data, meta}` + erros RFC 7807 |
| [0012](0012-hash-de-senha-pbkdf2.md) | Hash de senha PBKDF2-SHA256 customizado |
| [0013](0013-email-infra-fail-soft.md) | E-mail como infraestrutura compartilhada fail-soft |
| [0014](0014-convite-reaproveita-reset-de-senha.md) | Convite de usuário reaproveita a máquina de reset de senha |

> Decisões de granularidade mais fina (tetos de CSV, janela de notificações, isolamento de
> testes, `field_type` validado pela CHECK, etc.) estão catalogadas em
> [`docs/ai/AI_DECISIONS.md`](../ai/AI_DECISIONS.md).
