# ADR-0001 — Arquitetura em camadas e fronteira de transação

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

O backend precisa de uma separação clara entre transporte HTTP, regra de negócio e
persistência, para manter endpoints testáveis e evitar lógica de domínio espalhada em
routers. Também é preciso uma fronteira transacional única e previsível por requisição.

## Decisão

Adotar o fluxo **`api → service → repository → db`**, verificado em todos os módulos
(`backend/app/modules/<dominio>/{service,repository,schemas}.py` + `api/v1/routers/`):

- **Routers** parseiam request, resolvem dependências, chamam um método de service e
  serializam via `success_response`/`paginated_response` (`core/responses.py`).
- **Services** concentram regra de negócio e validação de domínio e são os **únicos** que
  chamam `db.commit()`.
- **Repositories** encapsulam queries/persistência; `_save`/`_save_many` (`core/repositories.py`)
  fazem **apenas `db.flush()`** e expõem métodos nomeados de criação (`create_team`, …).

## Consequências

- Regra de negócio fica isolada e testável sem subir HTTP.
- Transação previsível: um `commit` por operação, sempre no service.
- Repositories permanecem livres de regra; trocar query não afeta o service.
- Custo: boilerplate de método nomeado por operação de escrita (nada de `_save` direto no service).
- Disciplina exigida: esquecer o `commit` no service deixa a escrita só em savepoint/flush.

## Alternativas descartadas

- **Lógica no router (fat controllers):** acopla HTTP a domínio, dificulta teste e reuso.
- **Active Record / ORM direto no service:** vaza detalhes de persistência para o domínio.
- **Commit dentro do repository:** quebra a atomicidade da operação composta orquestrada pelo
  service e dificulta compor múltiplas escritas numa transação.
