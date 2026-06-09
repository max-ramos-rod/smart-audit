# ADR-0011 — Contrato HTTP: envelope `{data, meta}` + erros RFC 7807

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

O frontend precisa de um formato de resposta uniforme para sucesso, paginação e erro, evitando
tratar cada endpoint de forma ad-hoc.

## Decisão

Padronizar o contrato HTTP (verificado em `core/responses.py`, `core/pagination.py`,
`core/errors.py`):

- **Sucesso:** `{ "data": ..., "meta": {...} }` via `success_response`.
- **Paginação:** `meta` = `PageMeta` (`total`, `page`, `page_size`, `has_next`, `total_pages`)
  via `paginated_response`.
- **Erro:** **RFC 7807** (`application/problem+json`: `type`, `title`, `status`, `detail`,
  `instance`).
- Serialização sempre com `model_dump(mode="json")` (UUID/datetime como string).
- Mensagens de erro do backend evitam acentos (encoding de logs).

## Consequências

- Cliente trata sucesso/erro/paginação de forma única; o `problem.ts` do frontend depende disso.
- Testes de integração asseguram a forma do envelope — quebrá-la quebra a suíte.
- Erros padronizados facilitam logging e mapeamento no frontend.
- Custo: toda nova resposta precisa passar pelos helpers (não retornar dict cru).

## Alternativas descartadas

- **Respostas cruas por endpoint:** inconsistência e tratamento ad-hoc no cliente.
- **Erros em formato próprio (não RFC 7807):** perde interoperabilidade e padronização já
  consolidada.
- **Paginação por offset/cursor exposta sem `meta`:** dificulta navegação e contagem no cliente.
