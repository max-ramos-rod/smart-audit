# ADR-0017 — Modelo unificado de evidências (anexo polimórfico por escopo)

**Status:** Aceita · **Data:** 2026-06-11
**Supersedes:** — · **Superseded-by:** —
**Revisa/estende:** [ADR-0006](0006-modelo-hibrido-de-respostas.md) · [ADR-0016](0016-inspecao-por-componente-revisao-modelo-hibrido.md)

> **Implementada.** Símbolos que a sustentam: modelo `backend/app/db/models/attachments.py`
> (`Attachment` com `scope`/`company_id`/`submission_id`/`form_field_id`/`asset_id`/`component_label`/
> `metadata_json`; sem `submission_value_id`); migrations `e4f5a6b7c8d9` (expand) + `f5a6b7c8d9e0`
> (contract: `ck_attachments_scope_anchor`, índices não-únicos, drop do vínculo legado);
> `AttachmentService._resolve_scope`/`_validate_component` (escopo + INV1/INV-E2; não escreve
> `answers_json`); `AttachmentRepository.list_for_anchor` (`IS NOT DISTINCT FROM`); frontend
> `SubmissionDetailView`/`SubmissionReportView` re-chaveiam evidência por instância e enviam
> `asset_id`. Testes: `backend/tests/integration/test_attachments_evidence_scope.py` (INV-E1, escopos,
> INV1) + `frontend/src/__tests__/attachments.service.test.ts`.

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
  metadata_json    jsonb  NULL                              -- escopo-específico (validade de cert, tipo de doc, ART…)
                                                            -- NÃO usar o nome `metadata` (reservado no SQLAlchemy declarativo);
                                                            -- segue a convenção do projeto (`answers_json`, `config_json`, `attributes_json`).
  uploaded_by      uuid   NOT NULL  FK users
  created_at, updated_at

  -- TODOS os índices abaixo são NÃO-ÚNICOS por design (ver INV-E1). Nenhum UNIQUE/PK
  -- pode tocar a âncora (submission_id, form_field_id, asset_id) — isso capparia 1:N.
  INDEX (submission_id), (asset_id), (company_id)                       -- não-único
  INDEX (submission_id, form_field_id, asset_id)                        -- não-único; leitura por instância (laudo)

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

`metadata_json` (jsonb) é a válvula que cumpre "sem migração estrutural futura sobre dados existentes":
novos atributos de documento (validade, tipo, versão) entram como chave; novo escopo entra como
valor de enum + ramo de CHECK — nenhum dos dois reescreve linhas existentes.

### Q7.3 — Cardinalidade 1:N de evidências por item inspecionado (invariante INV-E1, protegida)

> Ledger de decisões: Q7 (modelo) · Q7.1 (remoção de `submission_value_id`) · Q7.2 (retenção) ·
> **Q7.3 (cardinalidade 1:N = INV-E1)** · Q7.4 (governança). A numeração é um catálogo, não uma
> ordem posicional.

**Um item inspecionado — `(submission, field, component)` ou qualquer escopo — admite N evidências.
Esta cardinalidade é uma garantia de negócio permanente e não pode ser limitada por acidente.**

Regras de proteção (vinculam toda evolução futura do schema):

1. **Proibido** qualquer `UNIQUE`, `PRIMARY KEY` (além de `id`) ou índice único que inclua
   `submission_id`, `form_field_id` e/ou `asset_id` — isoladamente ou em combinação. A âncora é
   deliberadamente **não-única**.
2. Todo índice sobre a âncora é criado **explicitamente não-único** (performance de leitura), nunca
   `unique=True`.
3. **Diferença essencial vs. respostas/conformidades:** `submission_values`/`submission_conformities`
   têm `UNIQUE(submission_id, form_field_id, asset_id) NULLS NOT DISTINCT` (uma resposta por item).
   **`attachments` é o oposto e por design:** zero constraints de unicidade sobre a âncora. Não
   copiar o padrão de unicidade daquelas tabelas para esta.
4. **Guarda de regressão obrigatória:** um teste insere ≥ 2 anexos com âncora idêntica (mesmo
   `submission_id`+`form_field_id`+`asset_id`) e **exige sucesso**; qualquer migração futura que
   reintroduza unicidade quebra esse teste antes de chegar à produção.

Esta invariante é citada pela Checklist de Sincronização: qualquer ADR/migration que toque
`attachments` deve reafirmar INV-E1.

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

1. Índice composto `(submission_id, form_field_id, asset_id)` — **não-único** (INV-E1); nenhum
   `UNIQUE`/PK pode tocar a âncora.
2. `submission_id ON DELETE CASCADE`; `asset_id` **sem** CASCADE (ativo é soft-deletado — ADR-0009/0015).
3. **Helper único** no `AttachmentRepository` para consultas por âncora usando `IS NOT DISTINCT FROM`
   (evita o footgun `=` com `asset_id` nullable).
4. `CHECK` de consistência `scope` × âncoras (acima).
5. **Backfill completo** dos dados existentes: cada anexo atual → `submission_id/form_field_id/
   asset_id` do seu `submission_value`, `company_id` via submission, `scope = 'component' if
   asset_id else 'field'`; depois `DROP submission_value_id`.
6. Cobertura de testes: migração (up/down), os 4 escopos, retrocompatibilidade (evidência legada
   vira `scope='field'` sem mover arquivo), e a **guarda de regressão de INV-E1** — inserir ≥ 2
   anexos com âncora idêntica e exigir sucesso (cardinalidade **1:N** por item inspecionado).
7. `create_attachment` valida o escopo reusando a **INV1** do T4 (asset ∈ subárvore do alvo + tipo
   bate com `component_type_id` do campo; field ∈ versão) e **não** escreve em `answers_json`.
8. **INV-E2 — coerência de tenant.** O `CHECK` não consegue validar tenancy; o service **deve**
   garantir que `company_id` do anexo = `company_id` da submission (escopos de evento) ou do asset
   (`scope='asset'`), senão 400/403. Teste de cross-tenant obrigatório (anexo não pode referenciar
   submission/asset de outra empresa).
9. **Efeitos colaterais a tratar (regressões conhecidas):**
   (a) `AttachmentService.serialize_attachment` resolve `field_key` via
   `attachment.submission_value.form_field.key` — esse caminho **morre** com a remoção de
   `submission_value_id`; passa a resolver via `attachment.form_field.key` (FK direto) ou
   `form_field_id`→key. (b) **Arquivo órfão no disco:** `submission_id ON DELETE CASCADE` apaga as
   **linhas**, mas o arquivo físico só é removido em `delete_attachment` (não dispara em cascade DB);
   enquanto não houver hard-delete de submission no código (hoje **não há** — confirmado), o risco é
   latente — registrar como follow-up de limpeza (job/outbox) para quando surgir o expurgo de
   inspeção. (c) Remover os relationships `SubmissionValue.attachments` e `Attachment.submission_value`.

A implementação ocorre **antes do go-live** (pré-produção), por preferência explícita, para evitar
migração futura sobre evidência real. Substitui e amplia o escopo do item **T8.5** do
`PLANO-DR-0002`, e fecha a limitação Opção-1 do T8.

**Segurança da migration (Parte 8 da revisão de gate):** `ADD COLUMN` nullable é metadata-only
(rápido); `SET NOT NULL` e o `CHECK` validam a tabela — em produção usar `ADD CONSTRAINT … NOT
VALID` seguido de `VALIDATE CONSTRAINT` (evita lock `ACCESS EXCLUSIVE` prolongado); índices em
tabela populada via `CREATE INDEX CONCURRENTLY` (fora de transação — incompatível com a transação
default do Alembic, exige `op.execute` com autocommit). Pré-produção a tabela é pequena → custo
negligível, mas o padrão seguro fica registrado. **Sem perda de dados** (aditivo + backfill;
`DROP submission_value_id` só após backfill verificado). **Rollback:** recria `submission_value_id`
re-derivando o value por `(submission_id, form_field_id, asset_id)` — ambíguo apenas se um
`submission_value` tiver sido deletado após a migração (não ocorre no fluxo atual).

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

### Q7.4 — A Checklist é padrão obrigatório de toda ADR + template oficial

A prática inaugurada por esta ADR é **promovida a padrão permanente** (não fica restrita à 0017):

- **Obrigatória, com N/A explícito.** Toda ADR inclui a seção Checklist de Sincronização
  Documental. ADRs que **não** alteram domínio/dados/API/módulos marcam
  `N/A — não altera domínio/dados/API/módulos` (decisão visível, não esquecida); as que alteram
  **devem** preencher e resolver.
- **Verificável, não teatral.** Cada item marcado **nomeia arquivo + mudança**; caixa marcada sem
  diff correspondente reprova o PR.
- **Template oficial canônico:** [`docs/adr/ADR_TEMPLATE.md`](ADR_TEMPLATE.md) (o antigo
  `template.md` passa a apontar para ele). Inclui o núcleo, as seções de impacto "se aplicável"
  (schema · API · migração/rollout · operacional · critérios de aceite) e a Checklist obrigatória.
- **Definition of Done** de toda ADR inclui a checklist resolvida (já vigente em `AI_RULES.md` /
  `START_HERE.md`).

### Checklist de Sincronização Documental — ADR-0017

Resolvida — todos os itens sincronizados nesta finalização da ADR.

| Documento | Impacto | Status |
|---|---|---|
| `docs/adr/README.md` | linha ADR-0017 no índice | ✅ |
| `docs/adr/ADR_TEMPLATE.md` + `template.md` | template oficial com Checklist (Q7.4) | ✅ |
| `docs/adr/0006-modelo-hibrido-de-respostas.md` | nota: efeito anexo→`answers_json` revisado pela 0017 | ✅ |
| `docs/adr/0016-inspecao-por-componente-revisao-modelo-hibrido.md` | nota cruzada com 0017 | ✅ |
| `docs/DER_Smart_Audit.md` | novo DDL `attachments`, relações, diagrama ER, notas obsoletas removidas | ✅ |
| `docs/Arquitetura_Smart_Audit.md` | bounded context "Evidências": âncora por escopo + doc de ativo | ✅ |
| `docs/ai/AI_MODELS.md` | colunas/relacionamentos de `attachments`; efeito `answers_json` removido | ✅ |
| `docs/ai/AI_DECISIONS.md` | nota de evidência por escopo (sem submission_value on-demand) | ✅ |
| `docs/ai/AI_RULES.md` | Regra de Governança Documental | ✅ |
| `docs/ai/START_HERE.md` | ponto de entrada de IA referencia a Regra de Governança | ✅ |
| `docs/AUDIT_REPORT.md` | efeito anexo→`answers_json` marcado como superado pela 0017 | ✅ |
| `docs/specs/SPEC-DR-0002-Fases2-4-InspecaoPorComponente.md` | §7: limitação T8 resolvida pela 0017 | ✅ |
| `docs/specs/PLANO-DR-0002-Fases2-4.md` | T8.5 marcado concluído pela 0017 | ✅ |
| `docs/design-records/Design_Record_Evolutivo.md` | evolução de evidências (âncora por escopo) | ✅ |
| `CLAUDE.md` | seção "Attachments module" reescrita para o modelo polimórfico | ✅ |
| `docs/TECH_BACKLOG.md` | TB-001 (limpeza física de arquivos órfãos) | ✅ |

> Nota A→B→C: a auditoria de 2026-06-11 não encontrou documento assumindo o modelo híbrido (B);
> todos os docs acima estão no modelo atual (A) e convergem para C (esta ADR).
