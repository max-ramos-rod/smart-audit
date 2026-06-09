# ADR-0004 — Autorização por guards hierárquicos de papel (RBAC)

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

Endpoints precisam de controle de acesso por papel (`OWNER`, `ADMIN`, `MANAGER`, `INSPECTOR`,
`VIEWER`) de forma declarativa, sem espalhar `if role == ...` pelos services.

## Decisão

Expor **dependências FastAPI hierárquicas** em `modules/memberships/permissions.py`, cada uma
construída sobre `get_current_membership` e validando um conjunto de papéis:

| Guard | Papéis |
|---|---|
| `get_current_membership` | qualquer membro ativo |
| `get_operator_membership` | OWNER, ADMIN, MANAGER, INSPECTOR |
| `get_manager_membership` | OWNER, ADMIN, MANAGER |
| `get_admin_membership` | OWNER, ADMIN |
| `get_owner_membership` | OWNER |

Aplicação verificada nos routers: leituras usam `get_current_membership`; `submissions`
(escrita) usa operator; `forms`/`teams` (escrita) usam manager; `users`/`audit-logs` e
`PATCH /companies/me` usam admin; `DELETE /companies/me` usa owner. `uploads`/`attachments`
usam apenas membership ativo.

## Consequências

- Autorização declarativa no router; o service recebe um `Membership` já autorizado.
- Hierarquia clara e reaproveitável (403 padronizado).
- **Efeito não óbvio:** como `uploads`/`attachments` exigem só membership ativo, **VIEWER pode
  enviar arquivos e criar/remover anexos** apesar de não responder inspeções.
- A matriz papel×rota é o ponto de verdade; mudanças de política são localizadas.

## Alternativas descartadas

- **Checagem de papel dentro do service:** mistura autorização com regra de negócio e dificulta
  auditar a política por rota.
- **Permissões granulares (ACL por recurso):** mais flexível, porém complexidade desnecessária
  para o conjunto atual de papéis.
- **Middleware global de autorização:** menos explícito por rota e mais difícil de compor com a
  resolução de tenant.
