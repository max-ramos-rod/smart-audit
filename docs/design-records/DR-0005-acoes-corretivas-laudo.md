# DR-0005 — Ações Corretivas, Re-inspeção e Laudo

**Status:** Proposta · **Data:** 2026-06-08 · **Depende de:** DR-0004 (veredito p/ laudo);
relaciona DR-0006 (renderer) · **Toca o core:** Não (aditivo)
**ADRs relacionadas:** 0008 (conformidades), 0010 (notificações derivadas), 0011, 0001

---

## 1. Resumo Executivo

**O que é.** Fechar o **ciclo de conformidade**: transformar uma não conformidade detectada numa
**ação corretiva** gerenciada (responsável, prazo, status, evidência de resolução), suportar a
**re-inspeção** que verifica a correção, e formalizar o resultado num **laudo/certificado**
(aprovado/reprovado, com validade).

**Problema que resolve.** Hoje a inspeção *detecta* problemas (itens `nao_conforme`) mas o ciclo
**morre no relatório**: não há acompanhamento da correção nem re-verificação. Em contexto
regulado/recorrente, isso é o coração do valor.

**Quem se beneficia.** Empresas de inspeção (laudo é o entregável) e inspeção patrimonial/
manutenção preventiva (gestão de remediação interna).

---

## 2. Contexto Atual

> Fatos verificados.

- **Conformidade (ADR 0008):** `submission_conformities` registra `conforme`/`nao_conforme` por
  campo, com `justification` opcional. É a fonte natural de "o que reprovou".
- **Evidências:** módulo `attachments` permite anexar arquivos a respostas — reutilizável como
  evidência de resolução.
- **Notificações (ADR 0010):** derivadas do estado das submissions, sem tabela própria; estado
  de leitura/dismiss em `notification_reads`.
- **Relatório:** PDF/CSV existem; **não há** conceito de laudo formal com veredito/validade
  (veredito vem do DR-0004; renderização multi-formato vem do DR-0006).
- **Não existe:** entidade de ação corretiva, nem fluxo de re-inspeção, nem laudo.

**Dor:** o ciclo de auditoria não fecha; o cliente não tem como acompanhar e comprovar correção.

---

## 3. Objetivos

### Funcionais

- **OF1.** Criar uma **ação corretiva** vinculada a uma não conformidade
  (`submission_conformity`): descrição, responsável, prazo, status.
- **OF2.** Anexar **evidência de resolução** (reusa `attachments`).
- **OF3.** Acompanhar o **status** (ex.: `aberta` → `em_andamento` → `concluida` /
  `cancelada`).
- **OF4.** **Re-inspeção:** registrar uma nova inspeção que reavalia os itens não conformes,
  vinculada à inspeção/ativo original, fechando os itens.
- **OF5.** Emitir **laudo** formal: veredito (DR-0004) + breakdown + não conformidades + ações
  corretivas + validade, renderizado via abstração de relatório (DR-0006).
- **OF6.** **Notificar** responsável (atribuição) e alertar prazos vencidos (estende ADR 0010).

### Não Funcionais

- **ONF1. Aditivo ao core:** não altera `submissions`/`submission_values`; só referencia
  `submission_conformities`.
- **ONF2.** Isolamento por `company_id` (ADR 0003).
- **ONF3.** Trilha de auditoria de cada transição (abertura, atribuição, conclusão) em
  `audit_logs`.
- **ONF4.** Laudo determinístico e congelado (reflete o estado no momento da emissão).

---

## 4. Não Objetivos

- **NÃO** definir o **veredito** de aprovação (isso é o **DR-0004**); aqui ele é consumido.
- **NÃO** implementar a renderização multi-formato (isso é o **DR-0006**); o laudo usa o
  renderer.
- **NÃO** implementar recorrência/agendamento de re-inspeção (evolução futura).
- **NÃO** implementar assinatura eletrônica do laudo (evolução futura — mercado regulado).
- **NÃO** criar portal externo para o cliente acompanhar ações (evolução futura).

---

## 5. Alternativas Consideradas

### 5.1 A que a ação corretiva se vincula

**A) À `submission_conformity` específica (o item que reprovou).** ✅
- *Vantagens:* granularidade exata (com DR-0002, aponta o componente exato); rastreável.
- *Escolha:* recomendada.

**B) À `submission` inteira.**
- *Desvantagens:* perde o "qual item"; não conecta à re-inspeção por item.
- *Rejeição:* granularidade insuficiente.

### 5.2 Como modelar a re-inspeção

**A) Nova `submission` vinculada à original (campo `reinspection_of` / origem).** ✅
- *Vantagens:* reusa todo o motor de inspeção/score/veredito; histórico encadeado.
- *Escolha:* recomendada.

**B) Reabrir/editar a inspeção original.**
- *Desvantagens:* viola a imutabilidade do registro (auditoria/regulado); perde histórico.
- *Rejeição:* registro de inspeção deve ser imutável.

### 5.3 Laudo

**A) Artefato derivado da inspeção (veredito + dados), renderizado on-demand via DR-0006.** ✅
- *Vantagens:* sem duplicar dados; formatos plugáveis.
- *Escolha:* recomendada. Pode-se **persistir uma versão emitida** (snapshot) para imutabilidade.

**B) Documento totalmente manual.**
- *Rejeição:* perde automação e consistência com a inspeção.

---

## 6. Solução Recomendada

### Conceitos

- **CorrectiveAction** — remediação de uma não conformidade: `submission_conformity_id`,
  descrição, `assignee` (usuário responsável), `due_date`, `status`, evidência (attachments),
  notas de resolução.
- **Re-inspeção** — `submission` nova marcada como re-inspeção de outra (`reinspection_of`),
  sobre o mesmo ativo; ao concluir, pode **fechar** ações corretivas correspondentes.
- **Laudo** — emissão formal do resultado: veredito (DR-0004) + breakdown + não conformidades +
  ações corretivas + validade; renderizado via DR-0006; opcionalmente persistido como snapshot
  imutável.

### Regras de negócio

- **RN1.** Ação corretiva sempre referencia uma `submission_conformity` `nao_conforme`.
- **RN2.** Transições de status são auditadas (`audit_logs`).
- **RN3.** Atribuição gera notificação ao responsável; prazo vencido gera alerta (ADR 0010).
- **RN4.** Re-inspeção é uma `submission` independente e imutável, ligada à origem; não edita a
  original.
- **RN5.** Item "fecha" quando a re-inspeção o avalia como `conforme` (ou a ação é concluída com
  evidência — política a definir, Q2).
- **RN6.** O laudo reflete o **veredito congelado** (DR-0004) no momento da emissão.

---

## 7. Impacto Arquitetural

- **Banco.** Novas tabelas: `corrective_actions` (FK → `submission_conformities`, `assignee` →
  `users`, `status`, `due_date`, timestamps) e, opcional, `report_emissions`/`laudos` (snapshot
  do laudo emitido). `submissions` ganha `reinspection_of` (FK nullable → `submissions`) — campo
  aditivo, não altera o modelo híbrido.
- **Backend.** Novo bounded context `corrective_actions` (`service`/`repository`/`schemas`, ADR
  0001). Extensão das notificações derivadas (ADR 0010) para atribuição/prazo. Emissão de laudo
  usa o renderer (DR-0006) e o veredito (DR-0004).
- **Frontend.** Telas: lista/quadro de ações corretivas (por inspeção, por responsável, por
  prazo); criar ação a partir de um item não conforme; fluxo de re-inspeção; emitir/baixar
  laudo. Base `/app/`.
- **APIs.** Recursos sob `/api/v1` (`corrective-actions`, re-inspeção como submission com origem,
  emissão de laudo). Envelope + RFC 7807 (ADR 0011).
- **Notificações/Observabilidade.** Alertas de prazo; métricas de ações abertas/vencidas/
  concluídas por empresa.
- **Auditoria.** `audit_logs`: `corrective_action.created/assigned/closed`, `report.emitted`.

---

## 8. Impacto em ADRs

- **ADR 0010 (notificações derivadas) — extensão.** Hoje as notificações derivam só de
  submissions. Ações corretivas introduzem alertas de **atribuição** e **prazo** — pode exigir
  derivação a partir de `corrective_actions` (ou nova ADR). Avaliar se permanece "derivada" ou
  ganha origem própria.
- **Reusa** ADR 0008 (conformidades como origem), 0001, 0011, 0003.
- **Nova ADR:** *"Ciclo de conformidade: ações corretivas, re-inspeção e laudo"*.

---

## 9. Modelo de Domínio

### Entidades

- **CorrectiveAction** — remediação de uma não conformidade.
- **(Opcional) ReportEmission/Laudo** — snapshot imutável de um laudo emitido.

### Relacionamentos

```
SubmissionConformity 1─N CorrectiveAction
User                 1─N CorrectiveAction (assignee)
Submission           0─1 Submission        (reinspection_of — encadeia re-inspeções)
Submission           1─N ReportEmission     (laudos emitidos da inspeção)
Company              1─N CorrectiveAction / ReportEmission
```

### Invariantes

- **INV1.** Ação corretiva pertence à mesma empresa da conformidade que a originou.
- **INV2.** Re-inspeção referencia uma submission origem da mesma empresa e mesmo ativo.
- **INV3.** A inspeção original é imutável; re-inspeção é registro novo.
- **INV4.** Laudo emitido reflete veredito e dados congelados no momento da emissão.
- **INV5.** Transições de status são monotônicas e auditadas (sem "desfazer" silencioso).

---

## 10. Fluxos

### Principal — ciclo de conformidade

1. Inspeção finaliza com itens `nao_conforme` (e veredito do DR-0004).
2. Para um item, cria-se uma **ação corretiva** (responsável, prazo).
3. Responsável é notificado (ADR 0010); executa; anexa evidência; marca `concluida`.
4. **Re-inspeção** reavalia os itens; se `conforme`, fecha o item.
5. Emite-se o **laudo** (veredito + não conformidades + ações + validade) via renderer (DR-0006).

### Cenários de erro/limite

- **Ação sem responsável/prazo** → permitido como rascunho? (Q3) — provável exigir ao atribuir.
- **Prazo vencido** → alerta; status continua até ação humana.
- **Re-inspeção que ainda reprova** → novo ciclo de ações; laudo reflete reprovação.
- **Emitir laudo de inspeção não finalizada** → bloqueado.

---

## 11. Riscos

### Técnicos
- **R-T1. Encadeamento de re-inspeções** (origem → re-inspeção → re-inspeção). *Mitigação:*
  `reinspection_of` simples; consultas de cadeia via origem.
- **R-T2. Notificações de prazo** exigem avaliação temporal. *Mitigação:* derivação por data
  (padrão ADR 0010) ou job leve.

### Negócio
- **R-N1. Processo não adotado** (clientes não acompanham ações). *Mitigação:* quadro simples
  (kanban) + alertas; valor claro no laudo.
- **R-N2. Laudo com peso legal** sem assinatura. *Mitigação:* deixar e-signature como evolução
  explícita; comunicar limite.

### Operacionais
- **R-O1. Volume de notificações** de prazo. *Mitigação:* agregação/digest.

---

## 12. Estratégia de Implementação

- **Fase 1.** `corrective_actions` (CRUD + status + evidência via attachments) ligadas a
  conformidades; quadro no frontend.
- **Fase 2.** Notificações de atribuição/prazo (estende ADR 0010).
- **Fase 3.** Re-inspeção (`reinspection_of`) + fechamento de itens.
- **Fase 4.** Laudo formal (veredito DR-0004 + renderer DR-0006) + snapshot imutável + validade.

---

## 13. Critérios de Aceitação

- **CA1.** É possível criar uma ação corretiva a partir de um item `nao_conforme`, com
  responsável e prazo.
- **CA2.** A evolução de status é auditada e a evidência de resolução é anexável.
- **CA3.** O responsável recebe notificação ao ser atribuído; prazo vencido gera alerta.
- **CA4.** Uma re-inspeção é um registro novo, ligado à origem, sem alterar a inspeção original.
- **CA5.** Um item reavaliado como `conforme` na re-inspeção é fechado.
- **CA6.** O laudo é emitido com veredito (DR-0004), não conformidades e ações, e reflete estado
  congelado.
- **CA7.** Nenhuma entidade vaza entre empresas.

---

## 14. Questões em Aberto

- **Q1.** Estados da ação corretiva (mínimo: aberta/em_andamento/concluída/cancelada?).
- **Q2.** Item "fecha" pela **re-inspeção conforme** ou pela **conclusão da ação com evidência**
  (ou ambos)?
- **Q3.** Ação corretiva exige responsável/prazo na criação ou permite rascunho?
- **Q4.** Notificações de prazo permanecem "derivadas" (ADR 0010) ou ganham origem própria?
- **Q5.** Laudo: sempre snapshot imutável persistido, ou render on-demand com opção de "emitir"?
- **Q6.** Validade do laudo: campo manual, ou derivada de recorrência por norma/ativo?

---

## 15. Evoluções Futuras

> Fora do escopo deste DR.

- **Assinatura eletrônica** do laudo + trilha imutável (mercado regulado; ICP-Brasil/eIDAS/
  21 CFR Part 11).
- **Recorrência/agendamento** de re-inspeção por ativo/norma (próxima inspeção vence em X).
- **Portal do cliente externo** para acompanhar ações e baixar laudos.
- **SLA e escalonamento** de ações vencidas (notificar gestor).
- **Indicadores de conformidade** (tempo médio de correção, reincidência por ativo/componente).
