# Backlog Técnico — Smart Audit

Itens de dívida/evolução técnica rastreados fora do escopo imediato de uma tarefa, para não se
perderem ao longo da evolução do produto. Cada item aponta a origem (ADR/DR) e a condição de
disparo.

---

## TB-001 — Limpeza física de arquivos órfãos após exclusão de evidências

**Origem:** [ADR-0017](adr/0017-modelo-unificado-de-evidencias.md) (Q7.2 + revisão de gate, Parte 8).
**Status:** Aberto · **Prioridade:** Média (latente até existir hard-delete de inspeção).

**Contexto — exclusão lógica × exclusão física.** Evidência tem duas exclusões distintas que **não
devem ser confundidas**:

- **Exclusão lógica (linha):** remover a linha em `attachments`. Acontece via
  `AttachmentService.delete_attachment` **ou** via `submission_id ON DELETE CASCADE` quando a
  inspeção é deletada (Q7.2).
- **Exclusão física (arquivo):** remover o arquivo do disco
  (`settings.upload_dir/<company_id>/<uuid>.<ext>`). **Só ocorre** no caminho
  `delete_attachment` (que faz `os.remove`). **Não dispara** num `ON DELETE CASCADE` do banco.

**Problema.** Quando existir um caminho de **hard-delete de inspeção**, o CASCADE apagará as
**linhas** de `attachments`, mas deixará os **arquivos órfãos no disco** (vazamento de
armazenamento). Hoje o risco é **latente**: não há hard-delete de submission no código
(`save_answers` faz upsert; o único `.delete(` em submissions/attachments é o de anexo).

**Ação quando disparar** (ao introduzir expurgo de inspeção, ou periodicamente):
- Job de reconciliação que varre `upload_dir` × `attachments.file_url` e remove arquivos sem linha;
  **ou** padrão outbox/evento na exclusão da inspeção que enfileira a remoção física; **ou** mover a
  remoção de arquivo para um hook de aplicação que rode antes do CASCADE.
- Considerar, no mesmo momento, se a política de retenção (Q7.2) deve mudar para
  `ON DELETE SET NULL` + arquivamento, caso surja exigência regulatória.

**Gatilho de ativação:** primeira de — (a) implementação de exclusão/expurgo de inspeção;
(b) requisito regulatório de retenção; (c) evidência medida de crescimento de arquivos órfãos.
