# ADR-0017 — Modelo unificado de evidências (anexo polimórfico por escopo)

**Status:** Proposta · **Data:** 2026-06-11
**Supersedes:** — · **Superseded-by:** —
**Revisa/estende:** [ADR-0006](0006-modelo-hibrido-de-respostas.md) · [ADR-0016](0016-inspecao-por-componente-revisao-modelo-hibrido.md)

<!--
Status Proposta: decisão acordada (Architecture Review de evidências, 2026-06-11; Q7 e Q7.1),
ainda NÃO implementada no código. Ao implementar, mudar Status para "Aceita", citar os símbolos
do código que a sustentam e resolver a Checklist de Sincronização Documental (§Governança).
Revisa o invariante do ADR-0006/0016 segundo o qual a criação de anexo escreve em answers_json:
sob esta ADR o anexo deixa de escrever no snapshot — attachments é a fonte da verdade da evidência.
-->

## Contexto

A inspeção por componente (DR-0002) tornou a unidade de inspeção `(Field × Component)`: respostas
e conformidades já são individualizadas por componente (`submission_values.asset_id`,
`submission_conformities.asset_id`; ADR-0016 / T4–T8). A evidência, porém, ficou para trás.

Modelo vigente (verificado no código):

- `Attachment.submission_value_id` é **FK NOT NULL CASCADE → submission_values**
  (`backend/app/db/models/attachments.py`).
- `AttachmentService.create_attachment` resolve/cria o `submission_value` por
  `(submission_id, form_field_id)` **ignorando `asset_id`** e grava
  `answers_json[field_key] = file_url` como efeito colateral
  (`backend/app/modules/attachments/service.py`).

Consequência: toda evidência de um campo escopado cai no `submission_value` de `asset_id = NULL` —
não há como dizer qual foto pertence a qual componente (Pneu DD vs DE). Para uma plataforma de
compliance/auditoria, isso é defeito de correção, não de UX.

O Architecture Review de 2026-06-11 enumerou cinco cenários que o modelo precisa atender
simultaneamente, sem exigir migração estrutural futura sobre evidência já armazenada:

1. evidência por componente — `(submission × field × component)`;
2. evidência por campo geral — `(submission × field)`, sem componente;
3. evidência da inspeção inteira — `(submission)`, sem campo;
4. documentos permanentes do ativo — `(asset)`, sem inspeção, atravessam inspeções;
5. **múltiplas evidências por item inspecionado** (cardinalidade 1:N).

Restrição de domínio decisiva: **evidência tem ciclo de vida próprio e pode existir sem
`SubmissionValue`** (foto antes da resposta; assinatura da inspeção; documento do ativo). Logo o
modelo deve representar o domínio da evidência, não o fluxo atual de inspeção.

## Decisão

### Q7 — Âncora unificada em uma tabela `attachments` polimórfica por escopo

Evidência é uma **entidade própria 1:N**, numa única tabela `attachments`, ancorada por um
discriminador `scope` e âncoras nullable governadas por `CHECK`. `attachments` é a **fonte da
verdade** da evidência; `answers_json` deixa de carregar mídia (mantém-se focado em
respostas/conformidades — revisa o efeito colateral do ADR-0006/0016).

```
attachments
  id               uuid   PK
  company_id       uuid   NOT NULL  FK companies            -- tenant uniforme (não deriva via value)
  scope            text   NOT NULL                          -- 'component' | 'field' | 'submission' | 'asset'
  submission_id    uuid   NULL  FK submissions ON DELETE CASCADE
  form_field_id    uuid   NULL  FK form_fields
  asset_id         uuid   NULL  FK assets                   -- componente (evento) OU alvo (doc de ativo); SEM cascade
  component_label  text   NULL                              -- rótulo CONGELADO (denorm de components_snapshot)
  file_url         text   NOT NULL
  thumbnail_url    text   NULL
  mime_type        text   NOT NULL
  file_size        bigint NOT NULL
  metadata         jsonb  NULL                              -- escopo-específico (validade de cert, tipo de doc, ART…)
  uploaded_by      uuid   NOT NULL  FK users
  created_at, updated_at

  INDEX (submission_id), (asset_id), (company_id)
  INDEX (submission_id, form_field_id, asset_id)            -- leitura por instância (laudo)

  CHECK (
    (scope='component'  AND submission_id IS NOT NULL AND form_field_id IS NOT NULL AND asset_id IS NOT NULL) OR
    (scope='field'      AND submission_id IS NOT NULL AND form_field_id IS NOT NULL AND asset_id IS NULL)     OR
    (scope='submission' AND submission_id IS NOT NULL AND form_field_id IS NULL     AND asset_id IS NULL)     OR
    (scope='asset'      AND submission_id IS NULL     AND form_field_id IS NULL     AND asset_id IS NOT NULL)
  )
```

Materialização por cenário:

| Cenário | scope | submission | field | asset | component_label |
|---|---|---|---|---|---|
| Pneu DD, "desgaste" | `component` | ✓ | ✓ | ✓ | "Pneu DD" (congelado) |
| Hodômetro (campo geral) | `field` | ✓ | ✓ | — | — |
| Assinatura / foto do veículo | `submission` | ✓ | — | — | — |
| Nota fiscal / certificado | `asset` | — | — | ✓ | (lido do ativo vivo) |
| 3 fotos do mesmo pneu | `component` ×3 | ✓ | ✓ | ✓ | "Pneu DD" |

`metadata jsonb` é a válvula que cumpre "sem migração estrutural futura sobre dados existentes":
novos atributos de documento (validade, tipo, versão) entram como chave; novo escopo entra como
valor de enum + ramo de CHECK — nenhum dos dois reescreve linhas existentes.

### Q7.1 — Remoção de `submission_value_id`

`submission_value_id` é **removido**. A relação "prova desta resposta" permanece recuperável por
filtro indexado em `(submission_id, form_field_id, asset_id)` — 1:1 com o `submission_value`
*quando ele existe*, graças ao `UNIQUE(submission_id, form_field_id, asset_id) NULLS NOT DISTINCT`
(migration `e3f4a5b6c7d8`).

Justificativa: a `SubmissionValue` não é garantida quando há evidência (3 dos 4 escopos não têm
value; além de foto-antes-da-resposta) — não se pode modelar a evidência como filha de uma entidade
que pode não existir. O modelo híbrido alternativo (manter `submission_value_id` opcional) seria
"a âncora polimórfica **mais** um ponteiro redundante", NULL na metade das linhas, com invariante
permanente de sincronização anchor×FK. O CASCADE que justificaria a FK é **teórico** (nenhum
caminho deleta `submission_values` — confirmado: `save_answers` faz upsert, o único `.delete(` é o
de anexo) **e indesejado** (editar resposta não pode apagar prova). A retenção desejada — deletar
inspeção apaga sua evidência — é entregue por `submission_id ON DELETE CASCADE`.

### Q7.2 — Política de retenção (decisão de negócio): evidência de inspeção segue o ciclo da inspeção

**Esta é uma decisão de negócio e de retenção documental, não um detalhe de implementação.**

- Evidências **associadas a inspeções** seguem o **ciclo de vida da inspeção**: deletar a inspeção
  apaga suas evidências de evento.
- Mecanismo: **`submission_id ON DELETE CASCADE`**.
- **Documentos permanentes do ativo** (`scope='asset'`, sem `submission_id`) permanecem
  **independentes** da inspeção e **não são afetados** por este CASCADE — seguem o ciclo de vida do
  ativo (soft delete, ADR-0009/0015).

Justificativa (negócio/retenção): o Smart Audit **não possui hoje requisito regulatório de retenção
independente** de evidências de inspeção. A política de retenção adotada é que a evidência de evento
é parte indivisível do registro da inspeção — não há valor de negócio em preservar prova órfã de uma
inspeção expurgada, e há custo (lixo de armazenamento, ambiguidade de auditoria) em fazê-lo. A
retenção de longo prazo de prova vive, quando necessária, no **documento de ativo**, que é
deliberadamente independente.

Gatilho de reavaliação (decisão de negócio futura): se surgir exigência regulatória/contratual de
**retenção independente** (ex.: laudo que deve sobreviver ao expurgo da inspeção, prazo legal de
guarda de prova), a política muda para `ON DELETE SET NULL` + arquivamento — alteração aditiva,
registrada aqui como gatilho, **não antecipada**.

### Requisitos arquiteturais obrigatórios da implementação

1. Índice composto `(submission_id, form_field_id, asset_id)`.
2. `submission_id ON DELETE CASCADE`; `asset_id` **sem** CASCADE (ativo é soft-deletado — ADR-0009/0015).
3. **Helper único** no `AttachmentRepository` para consultas por âncora usando `IS NOT DISTINCT FROM`
   (evita o footgun `=` com `asset_id` nullable).
4. `CHECK` de consistência `scope` × âncoras (acima).
5. **Backfill completo** dos dados existentes: cada anexo atual → `submission_id/form_field_id/
   asset_id` do seu `submission_value`, `company_id` via submission, `scope = 'component' if
   asset_id else 'field'`; depois `DROP submission_value_id`.
6. Cobertura de testes: migração (up/down), os 4 escopos, retrocompatibilidade (evidência legada
   vira `scope='field'` sem mover arquivo), e cardinalidade **1:N** por item inspecionado.
7. `create_attachment` valida o escopo reusando a **INV1** do T4 (asset ∈ subárvore do alvo + tipo
   bate com `component_type_id` do campo; field ∈ versão) e **não** escreve em `answers_json`.

A implementação ocorre **antes do go-live** (pré-produção), por preferência explícita, para evitar
migração futura sobre evidência real. Substitui e amplia o escopo do item **T8.5** do
`PLANO-DR-0002`, e fecha a limitação Opção-1 do T8.

## Consequências

- **Positivo:** atribuição de evidência por componente/campo/inspeção/ativo; 1:N nativo; laudo
  defensável com rótulo congelado (imune a renomeação, INV6); retenção desacoplada da edição da
  resposta; "evidência por ativo" e "por inspeção" viram queries triviais por coluna direta.
- **Positivo:** uma única forma de ler evidência (scope + âncoras) → contrato uniforme para
  integrações e relatórios; fim da criação de `submission_value` fantasma e da colisão N→1 no
  `answers_json`.
- **Custo / trade-off:** o join resposta↔evidência passa a exigir `IS NOT DISTINCT FROM` sobre a
  âncora nullable — mitigado pelo índice composto e pelo helper único de repositório.
- **Acoplamento de evolução:** revisa o invariante do ADR-0006/0016 (anexo não escreve mais
  `answers_json`); se documento-de-ativo ganhar workflow próprio (aprovação, expiração), `scope='asset'`
  poderá migrar para tabela dedicada — split **aditivo**, nunca migração sobre evidência de inspeção.

## Alternativas descartadas

- **Evidência no Field (modelo conceitual A):** sem atribuição por componente e incompatível com
  1:N como atributo — regressão probatória no domínio veicular/compliance.
- **Híbrido com `submission_value_id` opcional (B):** redundante (a âncora já existe para os escopos
  sem value), FK útil em só 2 de 4 escopos, invariante de sincronização permanente, e CASCADE
  teórico/indesejado. Ver Q7.1.
- **Duas tabelas (`attachments` + `asset_documents`):** duplica pipeline idêntico (storage, mime,
  thumbnail, tenant) por diferença que é de retenção/âncora, não de forma; reservado como split
  aditivo futuro se a semântica de documento-de-ativo divergir.

---

## Governança — Regra permanente de Sincronização Documental

> **Regra (vigente a partir desta ADR).** Toda ADR que alterar **domínio de negócio**, **modelo de
> dados**, **contratos de API** ou **arquitetura de módulos** deve obrigatoriamente produzir, na
> própria ADR, uma **Checklist de Sincronização Documental** que identifique e leve à atualização,
> quando aplicável: ADRs impactadas · DRs impactados · SPECs impactadas · DER · diagramas
> arquiteturais · `CLAUDE.md` · `docs/ai/*` · planos de implementação · relatórios de auditoria
> arquitetural · qualquer documento que deixe de refletir a arquitetura vigente.
>
> **Objetivo:** evitar drift entre ADR, SPEC, código e documentação operacional.
>
> **Definition of Done:** nenhuma implementação derivada de uma ADR é considerada concluída
> enquanto a sua Checklist de Sincronização Documental não estiver integralmente resolvida.

### Checklist de Sincronização Documental — ADR-0017

Resolver **antes** de marcar esta ADR como *Aceita*. Os docs descritivos atualizam **junto com a
implementação** (para refletirem o schema entregue), não antes.

| Documento | Impacto | Status |
|---|---|---|
| `docs/adr/README.md` | adicionar linha ADR-0017 ao índice | ✅ (nesta entrega) |
| `docs/adr/0006-modelo-hibrido-de-respostas.md` | nota: efeito anexo→`answers_json` revisado pela 0017 | ⬜ |
| `docs/adr/0016-inspecao-por-componente-revisao-modelo-hibrido.md` | nota cruzada com 0017 | ⬜ |
| `docs/DER_Smart_Audit.md` | novo DDL `attachments`, relações, diagrama ER, remover notas obsoletas | ⬜ |
| `docs/Arquitetura_Smart_Audit.md` | bounded context "Evidências": âncora por escopo + doc de ativo | ⬜ |
| `docs/ai/AI_MODELS.md` | colunas/relacionamentos de `attachments`; remover efeito `answers_json` | ⬜ |
| `docs/ai/AI_DECISIONS.md` | revisar nota "anexo sempre ligado a submission_value on-demand" | ⬜ |
| `docs/ai/AI_RULES.md` | operacionalizar a Regra de Governança Documental | ✅ (nesta entrega) |
| `docs/ai/START_HERE.md` | ponto de entrada de IA referencia a Regra de Governança | ✅ (nesta entrega) |
| `docs/AUDIT_REPORT.md` | marcar efeito anexo→`answers_json` como superado pela 0017 | ⬜ |
| `docs/specs/SPEC-DR-0002-Fases2-4-InspecaoPorComponente.md` | §7: resolução = ADR-0017; remover "limitação temporária" | ⬜ |
| `docs/specs/PLANO-DR-0002-Fases2-4.md` | T8.5 reescrito com o escopo pleno da 0017 | ⬜ |
| `docs/design-records/README.md` · `docs/Design_Record_Evolutivo.md` | refletir a evolução de evidências | ⬜ |
| `CLAUDE.md` | reescrever seção "Attachments module" para o modelo polimórfico | ⬜ |

> Nota A→B→C: a auditoria de 2026-06-11 não encontrou documento assumindo o modelo híbrido (B);
> todos os docs acima estão no modelo atual (A) e convergem para C (esta ADR).
