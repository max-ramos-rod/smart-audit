# ADR-0009 — Soft delete por semântica da entidade

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

Revogar acesso de usuário e desativar equipe/empresa não podem apagar histórico (inspeções,
membros, auditoria). Diferentes entidades têm semântica diferente: "quando o acesso foi
revogado" carrega informação temporal; "equipe ativa?" é um estado booleano.

## Decisão

Usar **dois mecanismos de soft delete conforme a semântica**, verificados no código:

- **`memberships.revoked_at TIMESTAMPTZ NULL`** — `NULL` = ativo; preenchido = revogado.
  Toda query de membership ativo filtra `revoked_at IS NULL` (auth, listagem de usuários,
  `/me/usage`, contexto).
- **`teams.is_active BOOLEAN`** — `FALSE` = desativada. Listagem/detalhe filtram
  `is_active = TRUE`; `DELETE /teams/{id}` desativa em vez de excluir.

`DELETE /companies/me` desativa a empresa (`is_active=FALSE`) e faz cascade lógico: revoga
memberships e desativa teams (`CompanyRepository.deactivate_company`).

## Consequências

- Histórico de inspeções, membros e auditoria preservado em todos os casos.
- `revoked_at` registra **quando** a revogação ocorreu (útil para auditoria); `is_active` é
  binário e simples.
- **Custo recorrente:** todas as queries relevantes precisam incluir o filtro de atividade —
  esquecer expõe registros revogados/inativos.
- Reativação é possível (membership) limpando `revoked_at`.

## Alternativas descartadas

- **Hard delete:** perde histórico exigido por auditoria e quebra FKs de inspeções.
- **Um único padrão (`is_active` para tudo):** perde o carimbo temporal da revogação de acesso.
- **Coluna `deleted_at` global genérica:** uniformiza mas ignora a diferença semântica entre
  "revogado em" e "ativo/inativo".
