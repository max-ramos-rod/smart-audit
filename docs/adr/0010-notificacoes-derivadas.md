# ADR-0010 — Notificações derivadas sem tabela própria

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

Os alertas operacionais (inspeção pendente, score baixo, excelência) são funções do estado
atual das inspeções. Persistir uma tabela de notificações exigiria mantê-la sincronizada com
cada mudança de submission.

## Decisão

**Não criar tabela `notifications`.** Derivar os alertas em tempo real de `submissions` e
persistir apenas o estado por usuário em `notification_reads`. Verificado em
`SubmissionService.get_notifications` e `NotificationReadRepository`:

- Regras: `in_progress` há +24h → `pending` (sem piso de data); `completed` finalizada nos
  últimos 30 dias com score `<80` → `low_score`, `>=90` → `excellent`.
- A query lê no máximo 50 submissions; a resposta é limitada às 20 mais recentes.
- Chave determinística (`pending-{id}`, `low-score-{id}`, `excellent-{id}`) permite upsert.
- **`notification_reads` não tem coluna `read`**: "lida" = existência de linha com
  `dismissed = FALSE`; `dismissed = TRUE` é filtrada da resposta.

## Consequências

- Zero sincronização: o alerta sempre reflete o estado atual da inspeção.
- Sem acúmulo de linhas de notificação; só grava quando o usuário interage (ler/dispensar).
- **Limitação de modelagem:** "lida" e "dispensada" compartilham a linha — não há como
  representar "li mas não dispensei" e "dispensei sem ler" como estados ortogonais.
- Faixa de score 80–89% não gera alerta (por design).
- Notificações antigas (completed > 30 dias) deixam de aparecer.

## Alternativas descartadas

- **Tabela `notifications` materializada:** exige produção/atualização a cada transição de
  submission e fica sujeita a divergência.
- **Coluna `read` dedicada:** redundante no design atual (a existência de linha não-dispensada
  já codifica "lida").
- **Fila/event sourcing de notificações:** infraestrutura desproporcional ao escopo.
