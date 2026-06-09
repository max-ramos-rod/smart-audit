# ADR-0002 — Backend assíncrono fim-a-fim, sem lazy loading

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

A API atende I/O-bound (DB, e-mail, arquivos) e precisa escalar concorrência sem threads
pesadas. SQLAlchemy async impõe restrições: lazy loading implícito levanta `MissingGreenlet`,
e conexões `asyncpg` se vinculam ao event loop em que foram criadas.

## Decisão

Usar **SQLAlchemy 2.0 async + `asyncpg`** em todo o backend. Endpoints, services, repositories
e dependências são `async def`. Regras verificadas no código:

- `db.add()`/`db.add_all()` são síncronos; `flush`/`commit`/`execute`/`scalar(s)`/`get`/`delete`
  exigem `await`.
- **Sem lazy loading:** relacionamentos acessados após a query são carregados com
  `selectinload` (encadeado para aninhados).
- Leituras base (`_get_one`, `_list_from_stmt`) usam `execution_options(populate_existing=True)`
  para recarregar objetos do resultado e reconciliar FKs `uuid.UUID`.
- `DATABASE_URL` usa o driver `asyncpg` (`postgresql+asyncpg://…`); `psycopg` não está instalado.
- Alembic roda sync sobre conexão async via `connection.run_sync(...)` (`alembic/env.py`).

## Consequências

- Alta concorrência de I/O sem custo de threads.
- Eager loading explícito torna o custo de query visível e previsível (evita N+1 acidental).
- `populate_existing=True` evita estado obsoleto no identity map após mutações.
- Custo cognitivo: todo acesso a relacionamento precisa ser planejado na query; novos
  desenvolvedores erram com `MissingGreenlet`.
- Testes precisam de loop de evento único por sessão (ver ADR de isolamento em AI_DECISIONS).

## Alternativas descartadas

- **Backend síncrono (psycopg + WSGI):** mais simples, mas limita concorrência de I/O e
  contraria a escolha de stack.
- **Lazy loading habilitado:** inviável em async (exceções em runtime) e mascara N+1.
- **Driver `psycopg` async:** decisão explícita de padronizar em `asyncpg` (não readicionar
  `psycopg`).
