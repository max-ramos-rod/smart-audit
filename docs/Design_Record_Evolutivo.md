# Design Record Evolutivo — Smart Audit como Plataforma de Inspeção e Conformidade de Ativos

> **Papel deste documento: ÍNDICE ESTRATÉGICO / VISÃO CONSOLIDADA.** É o mapa que liga a
> tese de produto, o roadmap e os riscos de escala internacional. O **detalhamento por
> iniciativa** vive em registros focados e independentes em
> [`docs/design-records/`](design-records/README.md) — cada um com as 15 seções completas,
> pronto para originar ADRs/specs/tasks sem rediscutir arquitetura.
>
> | Iniciativa | Design Record focado |
> |---|---|
> | Ativos genéricos (árvore de componentes, owner próprio×cliente) | [DR-0001](design-records/DR-0001-ativos-genericos.md) |
> | Inspeção por componente (toca o core — ADR 0006) | [DR-0002](design-records/DR-0002-inspecao-por-componente.md) |
> | Geração de checklist por IA | [DR-0003](design-records/DR-0003-geracao-checklist-ia.md) |
> | Score regulado (item crítico/knockout + threshold) | [DR-0004](design-records/DR-0004-score-regulado.md) |
> | Ações corretivas + re-inspeção + laudo | [DR-0005](design-records/DR-0005-acoes-corretivas-laudo.md) |
> | Abstração de relatório (`ReportRenderer`) | [DR-0006](design-records/DR-0006-abstracao-relatorio.md) |
>
> **Natureza.** Registro arquitetural durável (não é spec, não é tarefa). Captura decisões,
> contexto e intenção. **Status:** Proposta · **Data:** 2026-06-08 · nada implementado salvo
> onde marcado "já existe".
>
> **Como ler junto do resto:** referencia `docs/Arquitetura_Smart_Audit.md`,
> `docs/DER_Smart_Audit.md`, `docs/Deploy_Smart_Audit.md` e os ADRs em `docs/adr/`. As decisões
> vigentes (ADR 0001–0014) são **invariantes do core** e não são rediscutidas aqui. As seções
> abaixo são a visão consolidada; para profundidade e critérios de aceitação por iniciativa,
> use os DRs focados.

---

## 1. Resumo Executivo

**O que é.** Um plano evolutivo para transformar o Smart Audit de um *motor genérico de
checklists/inspeções* (estado atual) em uma *plataforma de inspeção e conformidade de
ativos* internacionalizável, com três alavancas de produto:

1. **Geração de checklist por IA** — upload de uma norma/contrato/procedimento → a IA produz
   um rascunho de formulário pronto para auditar.
2. **Ativos genéricos** — modelar *qualquer* objeto inspecionável (veículo, apartamento,
   máquina, ponte rolante, contrato) como uma árvore de componentes tipados, sem criar uma
   tabela por domínio.
3. **Ciclo de conformidade** — não conformidade → ação corretiva → re-inspeção → laudo,
   fechando o ciclo da auditoria.

**Problema que resolve.** Hoje o produto *detecta* problemas mas o ciclo morre no relatório;
montar um checklist do zero é a maior fricção de adoção; e o modelo de formulário plano não
representa bem objetos com partes repetidas (4 rodas), levando o inspetor a esquecer itens.

**Quem se beneficia.** Dois mercados servidos pelo **mesmo motor**:
- **Empresas de inspeção (B2B serviço)** — inspecionam ativos de **terceiros** e emitem laudo.
- **Inspeção interna/patrimonial (ex.: grande indústria)** — inspecionam **o próprio**
  patrimônio (manutenção preventiva, conformidade interna).

**Tese estratégica.** O diferencial defensável de longo prazo é a **geração de auditoria por
IA** (raro e vendável), apoiada por uma biblioteca proprietária de checklists e por um loop
de feedback humano. Ativos e ações corretivas destravam o **vertical regulado** (onde está o
orçamento). A maturidade internacional é o **destino**, alcançado subindo de tier de cliente.

---

## 2. Contexto Atual

> Apenas fatos verificados no código/docs (ver `docs/ai/START_HERE.md`).

**Como o sistema funciona hoje:**

- **Multi-tenant** por `memberships` N:N, empresa ativa via `X-Company-Id` (ADR 0003).
- **RBAC** por guards hierárquicos de papel: OWNER · ADMIN · MANAGER · INSPECTOR · VIEWER
  (ADR 0004).
- **Formulários versionados imutáveis**: `forms` → `form_versions` → `form_fields`; publicar
  nova versão nunca muta a anterior (ADR 0005).
- **Tipos de campo**: `boolean`, `text`, `number`, `date`, `select`, `section`. Configuração
  por campo em `config_json` JSONB (ADR 0007).
- **Modelo híbrido de respostas**: `submission_values` (relacional, 1 linha por
  `form_field_id`) + `answers_json` (snapshot) (ADR 0006).
- **Score ponderado** calculado de `submission_conformities` (não de `submission_values`);
  só campos `boolean` pontuam; peso via `config_json.weight`; N/A excluído (ADR 0008).
- **Evidências** como entidade própria ancorada por **escopo** (componente/campo/inspeção/ativo)
  no módulo `attachments`, 1:N por item (ADR-0017); arquivos em **disco local**.
- **Relatório**: exportação **PDF** (fpdf2) e **CSV**; o PDF é gerado diretamente, sem camada
  de template/renderer.
- **E-mail**: infraestrutura compartilhada fail-soft em `core/email/` (ADR 0013).
- **Convite de usuário**: reaproveita a máquina de reset de senha (ADR 0014); resolve
  onboarding **intra-empresa**.
- **Deploy**: Docker Compose atrás de Nginx + Cloudflare Tunnel; SPA sob base `/app/`.

**Limitações atuais (verificadas):**

- **Storage local** — uploads em disco não sobrevivem a múltiplos nós/redeploy efêmero.
- **Provisionamento de empresa nova é manual** — o primeiro OWNER de uma empresa nova é
  criado por script (nenhum membership pode autorizar a criação cross-tenant).
- **Formulário plano** — não há noção de "objeto inspecionado" nem de componentes; para
  inspecionar 4 rodas é preciso criar 4 campos manualmente ou perder granularidade.
- **Score binário-ponderado** — existe peso, mas não há conceito de **item crítico/knockout**
  nem **threshold de aprovação configurável** por norma.
- **PDF acoplado** — não há abstração de relatório (sem Excel/JSON/webhook/API).
- **Sem i18n de conteúdo** — labels de campo são texto único; sem residência de dados.

**Dores identificadas:**

- Onboarding lento: montar checklist do zero é trabalhoso.
- O ciclo de auditoria não fecha (detecta, mas não acompanha correção).
- Risco de inspeção incompleta (inspetor esquece um componente).
- Produto ainda não vende para regulado (falta laudo formal, item crítico, assinatura).

---

## 3. Objetivos

### Objetivos Funcionais

- **OF1.** Gerar rascunho de formulário a partir de documento (norma/contrato/procedimento)
  via IA, com revisão humana obrigatória antes de publicar.
- **OF2.** Cadastrar **qualquer** objeto inspecionável como ativo tipado com árvore de
  componentes, com cardinalidade decidida por instância.
- **OF3.** Vincular uma inspeção a um ativo e **enumerar componentes** no checklist, de modo
  que o inspetor não consiga pular um componente obrigatório.
- **OF4.** Registrar **ações corretivas** vinculadas a itens não conformes, com responsável,
  prazo, status e evidência de resolução; suportar **re-inspeção**.
- **OF5.** Emitir **laudo/certificado** formal (aprovado/reprovado, validade) como entregável.
- **OF6.** Servir os dois mercados (patrimônio próprio × serviço a terceiros) com `owner` no
  ativo, sem bifurcar o produto.
- **OF7.** Suportar **item crítico/knockout** e **threshold de aprovação** configuráveis por
  formulário/norma.
- **OF8.** Exportar relatório em múltiplos formatos via abstração de renderer (PDF, e
  futuramente Excel/JSON/webhook/API).

### Objetivos Não Funcionais

- **ONF1.** Preservar os invariantes do core (ADR 0001–0014); evoluções são **aditivas** e
  isoláveis sempre que possível.
- **ONF2.** Custo de IA controlado: processamento **assíncrono**, dedup por hash de documento,
  resultado armazenado, **nunca reprocessar** o mesmo documento; uso de prompt caching.
- **ONF3.** Escala por **isolamento de tenant** (`company_id`) como eixo primário; estruturas
  de dados que não exijam reescrita para particionar/indexar depois.
- **ONF4.** Caminho para conformidade internacional: **residência de dados** por região,
  **assinatura eletrônica + registro imutável**, **i18n** — projetados para serem adicionados
  sob demanda de contrato, sem reescrever o core.
- **ONF5.** Human-in-the-loop em tudo que a IA produzir (rastreabilidade e responsabilidade).

---

## 4. Não Objetivos

- **NÃO** é objetivo modelar domínios específicos (classes `Veículo`, `Hospital`, `Ponte`).
  O domínio vive em metadados.
- **NÃO** é objetivo, nesta proposta, billing/cobrança automática. Cobrança inicial é manual.
- **NÃO** é objetivo construir RBAC dinâmico (papéis/permissões customizáveis) agora — os
  papéis fixos (ADR 0004) bastam até um contrato exigir granularidade.
- **NÃO** é objetivo i18n de **conteúdo** (tradução de labels autorados) na primeira onda —
  apenas i18n de **produto** (UI) quando necessário.
- **NÃO** é objetivo construir portal de acesso externo do cliente final na primeira onda —
  a entrega do laudo é o PDF.
- **NÃO** é objetivo PWA/offline na primeira onda (entra quando o uso de campo exigir).
- **NÃO** é objetivo substituir o motor de IA por modelo próprio; usa-se LLM gerenciado.

---

## 5. Alternativas Consideradas

### 5.1 Representação de objetos inspecionáveis

**A) Tabela por domínio (`vehicles`, `apartments`, `machines`…)**
- *Vantagens:* schema forte, queries diretas.
- *Desvantagens:* explosão de tabelas; cada novo segmento exige migração e código; impossível
  de manter como produto genérico.
- *Rejeição:* contradiz o posicionamento de motor genérico; vira ERP intratável.

**B) Ativo genérico + atributos JSONB + árvore via `parent_asset_id` (adjacency list)** ✅
- *Vantagens:* um único modelo serve qualquer objeto; reusa o padrão já validado de
  `config_json` (ADR 0007); cardinalidade por instância; aditivo ao core.
- *Desvantagens:* sem validação de schema no banco (validar no service); queries recursivas
  mais complexas.
- *Escolha:* recomendada. É o mesmo movimento arquitetural que o projeto já fez para forms.

**C) Árvore via closure table / materialized path / `ltree` desde o início**
- *Vantagens:* leitura recursiva profunda eficiente.
- *Desvantagens:* complexidade de escrita; otimização prematura — Postgres lida com dezenas de
  milhões de linhas em adjacency list com índice adequado.
- *Rejeição (por ora):* adotar **somente** se/quando consultas recursivas profundas virarem
  gargalo medido. O eixo real de escala é particionamento por tenant, não a árvore.

### 5.2 Geração de checklist por IA

**A) Síncrono no request (upload → LLM → resposta na hora)**
- *Vantagens:* simples.
- *Desvantagens:* request longo, custo no caminho quente, sem controle de retry, sem dedup.
- *Rejeição:* não escala em custo nem em UX para documentos grandes.

**B) Pipeline assíncrono (fila → extração/OCR → chunking → IA → rascunho → revisão)** ✅
- *Vantagens:* custo controlado; dedup por hash; resultado persistido; nunca reprocessa;
  human-in-the-loop natural.
- *Desvantagens:* mais peças (fila, worker, estados).
- *Escolha:* recomendada.

**C) Auto-publicar o formulário gerado pela IA**
- *Rejeição:* norma/contrato exige verificação humana; rompe o controle de qualidade e o
  modelo de versionamento (ADR 0005). A IA sempre gera **rascunho**.

### 5.3 Score para mercado regulado

**A) Manter só peso (`config_json.weight`) — estado atual**
- *Desvantagem:* não expressa "item crítico reprova tudo" nem threshold por norma.
- *Rejeição (como suficiente):* insuficiente para ISO/OSHA/NBR/FDA/GMP.

**B) Adicionar item crítico/knockout + threshold configurável** ✅
- *Escolha:* estende o ADR 0008 sem quebrá-lo (peso continua válido).

### 5.4 Relatório

**A) Manter PDF acoplado** — *rejeição:* mercado pede Excel/JSON/API/webhook.
**B) Abstração `ReportRenderer` (PDF como um renderer)** ✅ — reusa o padrão do `EmailSender`
(ADR 0013); PDF vira uma implementação entre várias.

---

## 6. Solução Recomendada

### 6.1 Modelo conceitual — Ativos genéricos

Três camadas (espelham o padrão template→instância já usado em forms):

- **Metamodelo (`asset_type`)** — define a *forma* de um tipo: atributos esperados e
  blueprint de componentes ("um Veículo é composto de 4 Rodas, 2 Portas, 1 Suspensão").
- **Instância (`asset`)** — objeto concreto, com `attributes_json` (valores), `owner`
  (próprio × cliente) e `parent_asset_id` (a árvore). **Um componente é apenas um `asset`
  cujo pai é outro `asset`.** Isso colapsa "ativo" e "componente" numa estrutura recursiva
  que representa qualquer objeto.
- **Cliente (`client`)** — entidade leve, presente apenas no caso "serviço a terceiros".

### 6.2 Comportamento — Inspeção por componente

- Uma inspeção pode referenciar um `asset` alvo.
- Um `form_field` (ou seção) pode declarar **escopo por tipo de componente**. Na execução, o
  motor **expande** o campo uma vez por componente daquele tipo sob o ativo alvo (4 rodas → 4
  instâncias do item), cada uma com **resposta + conformidade + evidência próprias**.
- O inspetor é obrigado a percorrer cada componente enumerado — não há como esquecer uma roda.

### 6.3 Comportamento — Geração por IA

- Upload de documento entra num **pipeline assíncrono**: extração de texto/OCR → chunking →
  chamada ao LLM → **rascunho** de `form_fields` (com tipos, pesos, instruções sugeridos).
- O rascunho cai no **composer existente** para revisão humana; só então publica (ADR 0005).
- Resultado é **persistido e deduplicado** por hash; o mesmo documento nunca é reprocessado.

### 6.4 Comportamento — Ciclo de conformidade

- Um item **não conforme** pode originar uma **ação corretiva** (responsável, prazo, status,
  evidência de resolução).
- A **re-inspeção** referencia o mesmo ativo/componente; o item só "fecha" após reavaliação.
- O **laudo** formaliza o resultado (aprovado/reprovado + validade), reusando o relatório.

### 6.5 Regras de negócio centrais

- **RN1.** IA nunca publica; produz rascunho revisável.
- **RN2.** Cardinalidade de componentes é decidida na **instância**, não no tipo.
- **RN3.** `asset.client_id` nulo → patrimônio próprio; preenchido → serviço a terceiros —
  mesmo fluxo de inspeção para ambos (sem `owner_kind`; ver DR-0001 Q2).
- **RN4.** Item crítico reprovado força reprovação do laudo, independentemente do score.
- **RN5.** Score continua calculado de `submission_conformities` (ADR 0008), agora podendo ter
  a dimensão componente.
- **RN6.** Tudo é isolado por `company_id` (ADR 0003).

### 6.6 Fluxos (resumo; detalhe na seção 10)

`Cadastrar ativo → (opcional) IA gera checklist → inspeção enumera componentes → score +
itens críticos → não conformidades → ações corretivas → re-inspeção → laudo`.

---

## 7. Impacto Arquitetural

- **Banco de dados.** Novas entidades: `asset_types`, `asset_type_components`, `assets`
  (árvore), `clients`, `corrective_actions`, e (futuro) `inspection_schedules`,
  `report_templates`. **Toque no core (isolado):** dimensão de componente em
  `submission_values`/`submission_conformities` (mudança da unicidade de
  `(submission_id, form_field_id)` para incluir o componente) — afeta o ADR 0006.
- **Backend.** Novos bounded contexts (`assets`, `corrective_actions`), seguindo o padrão
  `service`/`repository`/`schemas` (ADR 0001). Novo serviço de geração por IA + worker de
  fila. Nova abstração `ReportRenderer` (padrão do `EmailSender`, ADR 0013).
- **Frontend.** Telas: cadastro/árvore de ativos; tipo de ativo (blueprint); inspeção com
  componentes enumerados; upload→IA→revisão de rascunho; ações corretivas; laudo. Mantém base
  `/app/` e o composer existente como ponto de revisão da IA.
- **APIs.** Novos recursos REST sob `/api/v1` (assets, asset-types, geração por IA,
  corrective-actions, relatórios). Mantém o envelope `{data, meta}` + RFC 7807 (ADR 0011).
- **Relatórios.** Migrar geração de PDF para trás de `ReportRenderer`; adicionar formatos sob
  demanda (Excel/JSON/webhook/API) — preparação para integração enterprise.
- **Autenticação.** Sem mudança no core (JWT + PBKDF2, ADR 0012). Futuro: SSO/e-signature
  como camadas aditivas para enterprise/regulado.
- **Autorização.** Reusa guards de papel (ADR 0004). Adicionar papéis pontuais quando
  necessário (`CLIENT` externo, `AUDITOR` read-only); **acesso do cliente a "apenas seus
  ativos" é row-level scoping**, não papel. RBAC dinâmico fica como evolução futura.
- **Multi-tenancy.** Todas as novas entidades carregam `company_id` e filtram por ele (ADR
  0003). Residência de dados por região é evolução futura (ONF4).
- **Observabilidade.** Pipeline de IA precisa de métricas (custo/latência/erro por job) e
  estados de fila; inspeção por componente aumenta volume de `submission_values` (monitorar).
- **Auditoria.** `audit_logs` ganha eventos novos (asset.created, ação corretiva, laudo
  emitido). Para regulado: assinatura eletrônica + imutabilidade de registro (evolução).

---

## 8. Impacto em ADRs

**ADRs afetadas (revisar/estender, não necessariamente substituir):**

- **ADR 0005 (versionamento imutável de formulários)** — a IA gera **rascunho** que segue o
  fluxo de versão; reforça o ADR (não o quebra).
- **ADR 0006 (modelo híbrido de respostas)** — **impacto direto**: a dimensão de componente
  em `submission_values`/`submission_conformities` muda a chave de unicidade. Exige ADR nova
  ou revisão explícita do 0006.
- **ADR 0007 (config_json)** — `attributes_json` de ativos e o escopo de componente em campos
  seguem a mesma filosofia; possível extensão.
- **ADR 0008 (score via conformities)** — estender para **item crítico/knockout** e threshold
  configurável; o score por componente também deriva daqui.
- **ADR 0004 (RBAC por guards)** — pode ganhar papéis pontuais; RBAC dinâmico seria ADR nova.
- **ADR 0011 (envelope/RFC 7807)** — mantido; relatórios multi-formato respeitam o contrato.

**Novas ADRs necessárias (candidatas):**

- **ADR — Modelo de ativos genéricos** (árvore adjacency list + JSONB + tipo/blueprint).
- **ADR — Inspeção por componente** (dimensão de componente em valores/conformidades).
- **ADR — Pipeline de geração por IA** (assíncrono, dedup, human-in-the-loop, prompt caching).
- **ADR — Score com item crítico/knockout e threshold por norma.**
- **ADR — Abstração de relatório (`ReportRenderer`).**
- **ADR — Ações corretivas e re-inspeção.**
- **ADR — Residência de dados / multi-região** (quando exigido).
- **ADR — Assinatura eletrônica e imutabilidade de registro** (regulado).

---

## 9. Modelo de Domínio

> Conceitual. Sem DDL. Nomes ilustrativos; o detalhamento físico será objeto de spec/ADR.

### Entidades

- **AssetType** — tipo/molde de objeto (Veículo, Roda, Apartamento). Atributos esperados +
  blueprint de componentes. Pertence a uma empresa.
- **AssetTypeComponent** — relação de composição entre tipos ("Veículo é composto de N Rodas").
- **Asset** — instância concreta; tem tipo, `attributes_json`, `owner`/`client`, `status` e
  `parent_asset_id` (árvore). Pertence a uma empresa.
- **Client** — destinatário do laudo no caso "serviço a terceiros".
- **CorrectiveAction** — remediação vinculada a um item não conforme; responsável, prazo,
  status, evidência.
- **(Futuro) InspectionSchedule** — recorrência por ativo.
- **(Futuro) ReportTemplate** — modelo de laudo por norma/cliente.

### Relacionamentos (texto)

```
Company 1─N AssetType 1─N AssetTypeComponent (parent_type / child_type)
Company 1─N Asset
Asset   1─N Asset            (parent_asset_id — árvore de componentes)
Client  1─N Asset            (via assets.client_id nullable; nulo = patrimônio próprio)
Asset   1─N Submission        (objeto inspecionado)
Asset   1─N SubmissionValue   (resposta por componente)
Asset   1─N SubmissionConformity (conformidade por componente)
SubmissionConformity 1─N CorrectiveAction
AssetType 1─N FormField       (escopo de repetição por tipo de componente)
```

### Agregados

- **Agregado Ativo** — raiz `Asset` + sua subárvore de componentes (`Asset` filhos). A árvore
  é manipulada pela raiz.
- **Agregado Inspeção** — raiz `Submission` + `SubmissionValue` + `SubmissionConformity`
  (já existente), agora com referência opcional a componente.
- **Agregado Conformidade** — `SubmissionConformity` + `CorrectiveAction` derivadas.

### Invariantes

- **INV1.** Todo `Asset`/`AssetType`/`Client`/`CorrectiveAction` pertence a exatamente uma
  empresa e só é visível nela (ADR 0003).
- **INV2.** Um componente (`Asset` com pai) tem o mesmo `company_id` da raiz.
- **INV3.** Não há ciclos na árvore de ativos (um ativo não pode ser ancestral de si mesmo).
- **INV4.** Uma `SubmissionValue`/`SubmissionConformity` com componente referencia um `Asset`
  que pertence à árvore do ativo alvo da inspeção.
- **INV5.** O score deriva exclusivamente de `submission_conformities` (ADR 0008).
- **INV6.** Item crítico reprovado ⇒ laudo reprovado, independentemente do score (RN4).
- **INV7.** Formulário gerado por IA nasce como rascunho; só vira versão publicada por ação
  humana (ADR 0005).

---

## 10. Fluxos

### 10.1 Fluxo principal — inspeção de ativo com componentes

1. Admin/Manager cadastra o ativo (ex.: Veículo placa ABC) a partir de um `AssetType`.
2. O sistema expande o blueprint em componentes-instância (4 Rodas, 2 Portas…); a instância
   ajusta a cardinalidade (caminhão → 6 Rodas).
3. Inspetor inicia inspeção vinculada ao ativo, com um formulário publicado.
4. O motor monta o checklist: campos gerais (sem componente) + campos com escopo de
   componente expandidos por nó (Roda DD/DE/TD/TE).
5. Inspetor responde e avalia conformidade por componente; anexa evidências.
6. Finalização calcula score (de conformities), aplica itens críticos/threshold.
7. Não conformidades podem gerar ações corretivas.
8. Emite-se o laudo (relatório formal) via `ReportRenderer`.

### 10.2 Fluxo alternativo — geração de checklist por IA

1. Usuário faz upload de uma norma/contrato.
2. Job assíncrono: dedup por hash → extração/OCR → chunking → LLM → rascunho de campos.
3. Rascunho aparece no composer; humano revisa, ajusta tipos/pesos/itens críticos.
4. Humano publica a versão (ADR 0005). A partir daí é um formulário normal.

### 10.3 Fluxo alternativo — serviço a terceiros (empresa de inspeção)

- Igual ao 10.1, com `Asset.client_id` apontando ao cliente externo; ao
  final, o laudo é o entregável ao cliente.

### 10.4 Cenários de erro

- **Documento ilegível/sem texto** na geração por IA → job falha de forma controlada; usuário
  é avisado; nenhum rascunho parcial é publicado.
- **IA gera campos inválidos** → revisão humana corrige antes de publicar (gate de qualidade).
- **Cardinalidade divergente** (instância com mais/menos componentes que o blueprint) →
  permitido; a instância prevalece.
- **Componente fora da árvore do ativo** em uma resposta → rejeitado (INV4).
- **Item crítico reprovado** → laudo reprovado mesmo com score alto (RN4/INV6).
- **Falha de envio de laudo por e-mail** → fail-soft, não quebra o fluxo (ADR 0013).

---

## 11. Riscos

### Técnicos

- **R-T1. Mudança no modelo híbrido (ADR 0006).** A dimensão de componente em
  `submission_values` é o ponto mais sensível. *Mitigação:* tratar como ADR dedicada, migração
  bem testada, `asset_id` nulo preservando o comportamento atual (retrocompatível).
- **R-T2. Custo/latência de IA.** *Mitigação:* pipeline assíncrono, dedup por hash, prompt
  caching, geração rara (versionamento reusa).
- **R-T3. Qualidade da geração por IA.** Rascunho ruim destrói confiança. *Mitigação:*
  human-in-the-loop obrigatório; biblioteca curada; loop de feedback.
- **R-T4. Crescimento de volume** (inspeção por componente multiplica linhas). *Mitigação:*
  índices por tenant; particionamento por `company_id` quando medido; evitar otimização
  prematura de árvore.
- **R-T5. Acoplamento do relatório.** *Mitigação:* introduzir `ReportRenderer` cedo, PDF como
  primeiro renderer.

### Negócio

- **R-N1. Moat raso na IA.** "PDF→LLM→checklist" é copiável. *Mitigação:* defender com
  biblioteca proprietária de normas, qualidade e loop de feedback — não com a feature em si.
- **R-N2. Dispersão de mercado.** Tentar atender muitos verticais cedo. *Mitigação:* beachhead
  único; expandir só após dominar.
- **R-N3. Sobre-engenharia precoce.** Construir RBAC dinâmico/i18n/multi-região sem contrato.
  *Mitigação:* tudo "sob demanda de contrato".

### Operacionais

- **R-O1. Storage local.** Perda de evidência em redeploy. *Mitigação:* migrar para storage
  externo (R2/S3) antes de cobrar.
- **R-O2. Provisionamento manual de empresa.** *Mitigação:* painel de plataforma / bootstrap
  em 1 comando.
- **R-O3. Deliverability de e-mail.** Convites/laudos em spam. *Mitigação:* provedor
  transacional com domínio autenticado (SPF/DKIM).
- **R-O4. Compliance/residência de dados** como bloqueador enterprise. *Mitigação:* projetar
  region-pinning como camada aditiva; tratar quando o primeiro contrato exigir.

---

## 12. Estratégia de Implementação

> Incremental, **orientada a receita e a contrato**. Cada fase é destravada por demanda real.
> A numeração reflete dependência/prioridade, não cronograma fixo.

**Fase 0 — Vendável (fundação para cobrar com responsabilidade).**
Storage externo (R2/S3); onboarding de empresa sem SSH; e-mail transacional; cobrança manual.
Vender o produto atual a um beachhead.
*Não depende de nada deste documento além da fundação.*

**Fase 1 — Diferencial: Geração por IA (MVP).**
Pipeline assíncrono upload→rascunho→revisão; dedup; começo da biblioteca de checklists.
*Acelera vendas; baixo risco ao core.*

**Fase 2 — Ativos (vínculo de objeto).**
`AssetType`, `Asset` (árvore), `Client`, `owner`; inspeção **referencia** um ativo (ainda sem
repetição de campo por componente). Atende os dois mercados. *Aditivo ao core.*

**Fase 3 — Score regulado + Relatório.**
Item crítico/knockout + threshold por norma (estende ADR 0008); `ReportRenderer` (PDF→pluggable).

**Fase 4 — Inspeção por componente.**
Dimensão de componente em `submission_values`/`submission_conformities`; expansão de campos por
componente. *Toque cirúrgico no core (ADR 0006) — maior risco, fazer com migração testada.*

**Fase 5 — Ciclo de conformidade.**
`CorrectiveAction` + re-inspeção + laudo formal com validade.

**Fase 6 — Maturidade internacional (sob demanda de contrato).**
Residência de dados/região; assinatura eletrônica + imutabilidade; i18n de conteúdo;
offline/PWA; RBAC dinâmico.

---

## 13. Critérios de Aceitação

> Mensuráveis. Cada um vira base de test plan futuro.

- **CA1 (IA).** Dado um PDF de norma com texto extraível, o sistema produz um rascunho de
  formulário com ≥1 campo por requisito identificável, sem publicar automaticamente, e o
  mesmo documento (mesmo hash) não é reprocessado.
- **CA2 (Ativos).** É possível cadastrar um ativo de qualquer tipo com N componentes em
  árvore; criar um segundo tipo de domínio diferente **não** exige mudança de schema.
- **CA3 (Inspeção por componente).** Para um ativo com 4 componentes do tipo X e um campo com
  escopo X, a inspeção exige 4 respostas/conformidades distintas; finalizar com um componente
  pendente é bloqueado.
- **CA4 (Score regulado).** Com um item marcado como crítico reprovado, o laudo resulta
  "reprovado" mesmo que o score numérico esteja acima do threshold.
- **CA5 (Dois mercados).** A mesma inspeção funciona com `client_id` nulo (próprio) e preenchido
  (cliente externo); no
  segundo caso, o laudo referencia o cliente.
- **CA6 (Ação corretiva).** Uma não conformidade gera ação corretiva com responsável/prazo;
  a re-inspeção do mesmo componente fecha o item.
- **CA7 (Relatório).** O laudo é gerado via `ReportRenderer`; adicionar um novo formato não
  exige alterar o serviço de inspeção.
- **CA8 (Isolamento).** Nenhuma entidade nova vaza entre empresas (consultas filtram
  `company_id`).
- **CA9 (Retrocompatibilidade).** Formulários e inspeções existentes (sem ativo/componente)
  continuam funcionando inalterados após cada fase.

---

## 14. Questões em Aberto

- **Q1.** Blueprint de componentes: cardinalidade fixa por tipo, ou slots nomeados (Roda DD,
  DE…)? Implica UX e modelagem de `AssetTypeComponent`.
- **Q2.** Escopo de componente: declarado por **campo** ou por **seção** (grupo repetível)?
- **Q3.** A IA deve sugerir **peso e item crítico**, ou apenas estrutura de campos?
- **Q4.** Provedor de fila/worker para o pipeline de IA (in-process vs. externo) — depende do
  volume esperado.
- **Q5.** Modelo de `Client`: entidade própria desde já, ou atributo no ativo até existir
  volume de serviço a terceiros?
- **Q6.** Laudo: documento livre (`ReportTemplate`) ou estrutura fixa por norma na 1ª versão?
- **Q7.** Recorrência (`InspectionSchedule`): por ativo, por tipo, ou por contrato?
- **Q8.** Assinatura eletrônica: padrão exigido pelos primeiros clientes regulados (ICP-Brasil,
  21 CFR Part 11, eIDAS)? Define a arquitetura de imutabilidade.
- **Q9.** Residência de dados: pinning por tenant em região única vs. multi-região ativa —
  qual o primeiro requisito real?
- **Q10.** i18n de conteúdo: tradução armazenada por campo vs. geração sob demanda pela IA.

---

## 15. Evoluções Futuras

> Explicitamente **fora** do escopo de implementação atual; registradas para visão de produto.

- **Portal do cliente externo** — login do cliente final para ver/baixar seus laudos
  (padrão de acesso e row-level scoping distintos).
- **Manutenção preventiva e recorrência** — agendamento por ativo, alertas de vencimento,
  histórico por objeto.
- **Integrações enterprise** — webhooks, API pública, conectores (ex.: ERPs/CMMS como SAP,
  Maximo).
- **RBAC dinâmico** — papéis e permissões customizáveis por empresa.
- **i18n de conteúdo e locale completo** — unidades (km/milha), formatos, fuso, moeda.
- **Offline-first / PWA** — inspeção em campo sem conectividade, com sincronização.
- **Assinatura eletrônica e trilha imutável** — para mercados regulados.
- **Multi-região / residência de dados** — para clientes internacionais com exigência legal.
- **Biblioteca pública de checklists de normas** — ativo proprietário que reforça o moat da IA.
- **Billing/self-service** — planos, cobrança automática, upgrades.
