# ADR-0003 — Multi-tenancy por `memberships` N:N com empresa ativa via `X-Company-Id`

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

O produto é SaaS multiempresa. Um mesmo usuário pode pertencer a mais de uma empresa, e cada
requisição precisa operar no contexto de exatamente uma empresa ativa, com isolamento de dados
entre tenants.

## Decisão

Modelar tenancy como **`User N—N Company` via `memberships`** (com `role` e `revoked_at`). Um
usuário **não** pertence a uma única empresa. Verificado em `db/models/memberships.py` e
`modules/memberships/dependencies.py`:

- A empresa ativa é resolvida pelo header **`X-Company-Id`** (`get_current_membership`).
- Se o usuário tem **1** membership, o header é opcional; com **2+**, é obrigatório (400 se ausente).
- **Toda query de domínio filtra por `membership.company_id`**; memberships ativos exigem
  `revoked_at IS NULL`.
- O frontend espelha: `http.ts` anexa `Authorization` + `X-Company-Id` do `localStorage`.

## Consequências

- Suporte nativo a usuários multiempresa sem duplicar contas.
- Isolamento de tenant depende de disciplina: esquecer o filtro `company_id` vaza dados.
- A troca de empresa ativa é barata (troca de header), sem novo login.
- `revoked_at` permite revogar acesso preservando histórico (ver ADR-0009).
- Requer o passo de seleção de empresa no frontend quando há múltiplos memberships.

## Alternativas descartadas

- **Usuário pertencente a uma única empresa (1:N):** simples, mas impede o mesmo e-mail operar
  em várias empresas — requisito do produto.
- **Banco/schema por tenant:** isolamento forte, porém custo operacional alto (migrations por
  tenant, conexões) desproporcional ao estágio.
- **Empresa ativa em sessão server-side:** o stack é stateless com JWT; o header mantém a API
  sem estado de sessão.
