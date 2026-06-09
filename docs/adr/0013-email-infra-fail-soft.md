# ADR-0013 — E-mail como infraestrutura compartilhada fail-soft

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

Vários fluxos enviam e-mail (reset de senha, convite). O envio é I/O bloqueante e pode falhar
(SMTP indisponível), mas uma falha de e-mail não pode quebrar o fluxo HTTP — em especial o
forgot-password, que precisa ser fail-soft para não vazar existência de conta.

## Decisão

Centralizar e-mail em **`backend/app/core/email/`** com três camadas (verificadas no código):

- **`sender.py`** — protocolo `EmailSender` + `SmtpEmailSender` (prod) e `ConsoleEmailSender`
  (dev, quando `SMTP_HOST` está vazio). `get_email_sender()` é factory `lru_cache`.
  `SmtpEmailSender` roda `smtplib` via `asyncio.to_thread` e **engole exceções**.
- **`templates.py`** — funções puras que retornam `EmailMessage` (texto + HTML).
- **`service.py`** — `EmailService` com métodos semânticos (`send_password_reset`,
  `send_user_invite`). Modules injetam `EmailService` e chamam intenção, não SMTP.

Links absolutos usam `FRONTEND_URL` (inclui `/app`).

## Consequências

- Falha de SMTP nunca propaga para o request (sustenta o anti-enumeração do forgot-password).
- Trocar transporte (SMTP → Resend/SES) afeta só o `sender`, não os chamadores.
- Dev funciona sem SMTP (loga a mensagem no console).
- **Trade-off:** e-mails perdidos por falha silenciosa não são reportados ao chamador — exige
  observabilidade no transporte para diagnóstico.

## Alternativas descartadas

- **`smtplib` direto nos módulos:** espalha SMTP pelo domínio e dificulta troca de provedor.
- **Envio síncrono no request:** bloqueia o event loop async.
- **Propagar exceções de envio:** quebraria fluxos como o reset e revelaria timing/erro
  explorável para enumeração de contas.
