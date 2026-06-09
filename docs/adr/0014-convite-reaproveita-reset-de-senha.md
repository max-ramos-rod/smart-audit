# ADR-0014 — Convite de usuário reaproveita a máquina de reset de senha

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

É preciso onboarding intra-empresa: um admin convida um usuário que ainda não tem senha. Isso é
quase idêntico a um reset de senha — gerar um token, enviar link, deixar o usuário definir a
senha — e duplicar essa máquina geraria dois fluxos de "ativação" para manter.

## Decisão

O convite **reusa a tabela `password_reset_tokens` e o endpoint `POST /auth/reset-password`**.
Verificado em `UserService.invite_user`:

- `POST /users/invite` (admin) cria o usuário com **senha aleatória inutilizável**
  (`hash_password(secrets.token_urlsafe(32))`) e o vincula via membership.
- Gera token na **mesma** `password_reset_tokens`, com TTL maior
  (`invite_token_ttl_hours`, default 72h vs 1h do reset).
- O convidado define a senha pela **mesma** tela/endpoint do reset.
- Audita `user.invited`. O onboarding cross-empresa (primeiro OWNER) permanece manual (scripts).

## Consequências

- Uma única máquina de tokens serve reset e convite (menos código, menos superfície de bug).
- Convidado não consegue logar até definir a senha (senha inutilizável).
- O TTL configurável separa as durações dos dois usos.
- **Acoplamento:** mudar o fluxo de reset afeta o convite — devem evoluir juntos.

## Alternativas descartadas

- **Fluxo de "ativação de conta" separado:** duplicaria token + endpoint + tela do reset.
- **Criar usuário já com senha temporária enviada por e-mail:** expõe senha em trânsito e exige
  troca obrigatória no primeiro login.
- **Auto-cadastro/self-service:** muda o modelo de provisionamento (hoje admin-gated +
  scripts); fora do escopo atual.
