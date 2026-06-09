# ADR-0012 — Hash de senha PBKDF2-SHA256 customizado

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

A autenticação precisa armazenar senhas de forma segura. As senhas já existentes no banco estão
em um formato específico, o que torna qualquer troca de algoritmo uma questão de migração.

## Decisão

Usar um hash **PBKDF2-SHA256 customizado** no formato
`pbkdf2_sha256$iterations$salt$digest`, implementado em `backend/app/core/security.py`
(`hash_password`/`verify_password`). O login valida via `verify_password`
(`AuthService.login`).

## Consequências

- Sem dependência de bibliotecas externas de hashing (PBKDF2 está na stdlib).
- Formato auto-descritivo (iterações/salt embutidos) permite verificar hashes antigos.
- **Restrição operacional:** trocar para passlib/bcrypt exige plano de migração para os hashes
  existentes — não é troca transparente.
- Reset e convite reescrevem o hash pelo mesmo caminho (`hash_password`).

## Alternativas descartadas

- **bcrypt/argon2 via passlib:** algoritmos fortes, mas trocar agora invalida os hashes já
  gravados sem uma rotina de migração.
- **Hash sem salt / rápido (MD5/SHA simples):** inseguro contra brute force/rainbow tables.
- **Delegar auth a provedor externo (OAuth/IdP):** muda o modelo de identidade do produto;
  fora do escopo atual.
