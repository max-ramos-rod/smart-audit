# DR-0001 — Ativos Genéricos

**Status:** Proposta · **Data:** 2026-06-08 · **Depende de:** — · **Toca o core:** Não (aditivo)
**ADRs relacionadas:** 0003 (multi-tenancy), 0007 (config_json) · **Habilita:** DR-0002, DR-0005

---

## 1. Resumo Executivo

**O que é.** Um modelo único e genérico para representar **qualquer objeto inspecionável** —
veículo, apartamento, máquina de produção, ponte rolante, contrato — como uma **árvore de
componentes tipados**, sem criar uma tabela por domínio. Inclui a noção de **dono do ativo**
(`owner`) para servir, com o mesmo modelo, tanto inspeção patrimonial (objeto próprio) quanto
empresa de inspeção (objeto de cliente externo).

**Problema que resolve.** Hoje o formulário é "plano": não há entidade que represente o objeto
inspecionado nem suas partes. Para inspecionar um carro com 4 rodas, o autor precisa criar 4
campos manuais (rígido) ou 1 campo "rodas" (perde granularidade). Não há histórico por objeto,
nem como distinguir "patrimônio próprio" de "ativo de cliente".

**Quem se beneficia.** Os dois mercados, com o mesmo motor, discriminados por `assets.client_id`
(nullable): inspeção interna/patrimonial (`client_id` nulo) e empresa de inspeção que emite
laudo para terceiros (`client_id` preenchido). **Beachhead (2026-06-08):** o primeiro cliente
esperado é uma **empresa de inspeção** — por isso `Client` é entidade desde a Fase 1 (ver Q2 e
nota de faseamento).

> Este DR entrega **apenas o cadastro e a árvore de ativos + o vínculo da inspeção a um ativo**.
> A *repetição de campo por componente* (enumerar 4 rodas no checklist) é o DR-0002, que toca o
> core e vem depois.

---

## 2. Contexto Atual

> Fatos verificados (ver `docs/Arquitetura_Smart_Audit.md`, `docs/DER_Smart_Audit.md`, ADRs).

- **Multi-tenant** por `company_id`, empresa ativa via `X-Company-Id` (ADR 0003). Toda entidade
  de domínio filtra por empresa.
- **Formulários versionados** (`forms`/`form_versions`/`form_fields`) e **inspeções**
  (`submissions`/`submission_values`/`submission_conformities`) existem e funcionam.
- **`config_json` (JSONB)** já é o padrão para configuração flexível de campo (ADR 0007) — prova
  de que o projeto adota "estrutura flexível em JSONB validada no service".
- **Não existe** nenhuma entidade de "objeto"/"ativo"/"componente". A inspeção (`submissions`)
  referencia apenas `form_version_id` e `company_id`.
- Padrão de módulo: `service`/`repository`/`schemas` por bounded context (ADR 0001); PK UUID +
  `TimestampMixin`; envelope `{data, meta}` + RFC 7807 (ADR 0011).

**Dores:** inspeção sem objeto associado; granularidade por componente impossível sem editar o
formulário; sem histórico por objeto; impossível separar patrimônio de ativo de cliente.

---

## 3. Objetivos

### Funcionais

- **OF1.** Definir **tipos de ativo** (molde): atributos esperados e blueprint de componentes.
- **OF2.** Cadastrar **instâncias de ativo** com atributos livres (JSONB) e **árvore de
  componentes** (cardinalidade decidida na instância).
- **OF3.** Expandir, opcionalmente, o blueprint do tipo ao criar a instância (Veículo → 4 Rodas,
  2 Portas), permitindo ajuste (caminhão → 6 Rodas).
- **OF4.** Representar o **dono** do ativo via `client_id` nullable: nulo = patrimônio próprio;
  preenchido = ativo de cliente externo (sem `owner_kind`).
- **OF5.** Cadastrar **clientes** (entidade mínima: id, company_id, name, is_active) — fluxo
  primário do beachhead (empresa de inspeção).
- **OF6.** **Vincular uma inspeção a um ativo** (referência), sem ainda repetir campo por
  componente.
- **OF7.** Listar/consultar ativos por tipo, por cliente e por hierarquia.

### Não Funcionais

- **ONF1.** Aditivo ao core: nenhuma entidade existente é alterada nesta fase (apenas
  `submissions` ganha referência **opcional** a ativo).
- **ONF2.** Genérico por construção: adicionar um novo domínio (hospital, ponte) **não** exige
  migração de schema.
- **ONF3.** Isolamento por `company_id` em todas as entidades novas (ADR 0003).
- **ONF4.** Escala por tenant; estrutura de árvore que não exija reescrita para indexar/
  particionar depois.

---

## 4. Não Objetivos

- **NÃO** repetir campo por componente no checklist (isso é o **DR-0002**).
- **NÃO** modelar domínios específicos como classes (`Vehicle`, `Apartment`).
- **NÃO** implementar recorrência/agendamento de inspeção por ativo (evolução futura).
- **NÃO** construir portal de acesso do cliente externo (o laudo é entregue como arquivo).
- **NÃO** validar schema de atributos no banco — validação fica no service (como `config_json`).

---

## 5. Alternativas Consideradas

### 5.1 Representação do objeto

**A) Tabela por domínio (`vehicles`, `apartments`, …).**
- *Vantagens:* schema forte, queries diretas.
- *Desvantagens:* explosão de tabelas/migrações; intratável como produto genérico.
- *Rejeição:* contradiz o posicionamento de motor genérico.

**B) Ativo genérico + `attributes_json` + árvore via `parent_asset_id` (adjacency list).** ✅
- *Vantagens:* um modelo serve qualquer objeto; reusa a filosofia do `config_json` (ADR 0007);
  cardinalidade por instância; aditivo.
- *Desvantagens:* sem validação de schema no banco; queries recursivas mais complexas.
- *Escolha:* recomendada. É o mesmo movimento template→instância já validado em forms.

**C) Closure table / materialized path / `ltree` desde o início.**
- *Vantagens:* leitura recursiva profunda eficiente.
- *Desvantagens:* complexidade de escrita; otimização prematura.
- *Rejeição (por ora):* adotar só se consultas recursivas profundas virarem gargalo medido.

### 5.2 Modelagem do "componente"

**A) Tabela `asset_components` separada de `assets`.**
- *Desvantagens:* duplica conceito; um componente tem as mesmas propriedades de um ativo
  (tipo, atributos, pode ter sub-componentes).
- *Rejeição:* viola DRY; dificulta sub-árvores (amortecedor dentro da suspensão).

**B) Componente **é** um `asset` com `parent_asset_id`.** ✅
- *Escolha:* colapsa ativo e componente numa estrutura recursiva única — representa qualquer
  objeto e qualquer profundidade.

### 5.3 Cliente (owner externo)

**A) Atributo de texto livre no ativo (`owner_name`).**
- *Vantagens:* zero modelagem.
- *Desvantagens:* sem consultas por cliente, sem reuso, sem dados de contato para laudo.
- *Rejeição:* insuficiente para empresa de inspeção, que organiza por cliente.

**B) Entidade `clients` mínima + `assets.client_id` nullable como discriminador.** ✅
- *Escolha:* permite listar ativos por cliente e enriquecer o laudo. `client_id` nulo =
  patrimônio próprio (não há `owner_kind` separado). **Decidido como Fase 1** (Q2), pois o
  primeiro cliente é uma empresa de inspeção cujo fluxo gira em torno do cliente externo.

---

## 6. Solução Recomendada

### Modelo conceitual (três camadas)

- **AssetType (molde, por empresa)** — define a forma de um tipo: `attributes_schema` (hints de
  atributos) e o blueprint de componentes. Análogo a `form_versions` para campos.
- **AssetTypeComponent (blueprint / BOM)** — relação de composição entre tipos: "Veículo é
  composto de N Rodas, M Portas". Cada linha: tipo-pai, tipo-filho, label, `default_quantity`.
- **Asset (instância, árvore)** — objeto concreto: `asset_type_id`, `attributes_json` (valores),
  `parent_asset_id` (NULL = raiz; preenchido = componente), `client_id` **nullable**
  (NULL = patrimônio próprio; preenchido = ativo de cliente externo — **discriminador único**,
  sem `owner_kind`), `identifier`, `status`.
- **Client (mínimo, Fase 1)** — `id, company_id, name, is_active`. Dono externo do ativo e
  destinatário do laudo; atributos ricos (CNPJ, contato) entram com o DR-0005.

### Comportamento

- Criar um `Asset` raiz de um tipo pode **expandir** o blueprint em componentes-instância
  (`Asset` filhos), mas a instância pode divergir (mais/menos componentes).
- Um componente é apenas um `Asset` cujo `parent_asset_id` aponta para outro `Asset`; a árvore
  pode ter qualquer profundidade (suspensão → amortecedor).
- Uma `Submission` ganha referência **opcional** a um `Asset` alvo (`asset_id` nullable).

### Regras de negócio

- **RN1.** Todo `Asset` pertence a uma empresa; um componente herda o `company_id` da raiz.
- **RN2.** Cardinalidade de componentes é decidida na **instância**, não no tipo.
- **RN3.** `client_id` nulo ⇒ patrimônio próprio; `client_id` preenchido ⇒ ativo de cliente
  externo. Não há `owner_kind` — o próprio `client_id` (nullable) é o discriminador.
- **RN4.** A árvore não tem ciclos (um ativo não pode ser ancestral de si mesmo).
- **RN5.** Soft delete por `status`/`is_active` segue a semântica da entidade (ADR 0009).

---

## 7. Impacto Arquitetural

- **Banco.** Novas tabelas: `asset_types`, `asset_type_components`, `assets`, `clients`. Única
  alteração no existente: `submissions.asset_id` (FK nullable). Índices: `(company_id,
  parent_asset_id)`, `(company_id, asset_type_id)`, `(company_id, client_id)`.
- **Backend.** Novos bounded contexts `assets` e `clients` (`service`/`repository`/`schemas`,
  ADR 0001). Validação de `attributes_json`/blueprint no service (ADR 0007).
- **Frontend.** Telas: tipos de ativo (blueprint), cadastro/edição de ativo com árvore de
  componentes, seleção de ativo ao iniciar inspeção, cadastro de clientes. Base `/app/`.
- **APIs.** Recursos REST sob `/api/v1` (`asset-types`, `assets`, `clients`); envelope + RFC
  7807 (ADR 0011). Schemas de request com `Field(min/max)` (regra do projeto).
- **Auth/Autorização.** Reusa guards de papel (ADR 0004): leitura para qualquer membro; escrita
  de `asset_types`, `assets` e `clients` = **MANAGER+** (`get_manager_membership`, hierárquico —
  inclui ADMIN e OWNER). No beachhead de empresa de inspeção, cliente é dado **operacional**,
  não comercial (ver Q3). **Acesso do cliente externo a "apenas seus ativos" é row-level
  scoping** (portal externo) — fora deste DR.
- **Multi-tenancy.** Todas as entidades carregam `company_id` (ADR 0003).
- **Observabilidade/Auditoria.** `audit_logs` ganha eventos `asset.created`, `asset.updated`,
  `client.created` (seguindo o padrão existente).

---

## 8. Impacto em ADRs

- **Reusa** ADR 0003 (multi-tenancy), 0007 (filosofia JSONB), 0009 (soft delete), 0001
  (camadas), 0011 (contrato HTTP) — sem alterá-los.
- **ADR originada:** [ADR-0015 — Modelo de ativos genéricos](../adr/0015-modelo-de-ativos-genericos.md)
  (Status: Proposta), registrando árvore adjacency list + JSONB + componente-é-ativo +
  `client_id` discriminador + soft delete + MANAGER+. Passa a **Aceita** e cita o código quando
  implementada.

---

## 9. Modelo de Domínio

### Entidades

- **AssetType** — tipo/molde de objeto (por empresa).
- **AssetTypeComponent** — composição entre tipos (blueprint/BOM).
- **Asset** — instância concreta; raiz da árvore ou componente (via `parent_asset_id`).
- **Client** — dono externo (opcional).

### Relacionamentos

```
Company 1─N AssetType 1─N AssetTypeComponent (parent_type_id / child_type_id)
Company 1─N Asset
AssetType 1─N Asset
Asset   1─N Asset            (parent_asset_id — árvore de componentes, profundidade livre)
Company 1─N Client 1─N Asset (via assets.client_id nullable; nulo = patrimônio próprio)
Asset   0─N Submission        (asset_id opcional em submissions)
```

### Atributos conceituais (sem DDL)

```
AssetType:  id, company_id, name, slug, description, attributes_schema(JSONB), is_active, ts
AssetTypeComponent: id, parent_type_id, child_type_id, label, default_quantity, position
Asset:      id, company_id, asset_type_id, parent_asset_id?, identifier,
            attributes_json(JSONB), client_id?, status, ts
            -- client_id NULL = patrimônio próprio; preenchido = ativo de cliente (sem owner_kind)
Client:     id, company_id, name, is_active, ts
            -- mínimo na Fase 1; document/contact_email entram com o DR-0005 (laudo)
```

### Agregados e invariantes

- **Agregado Ativo** — raiz `Asset` + subárvore de componentes; manipulada pela raiz.
- **INV1.** `Asset`/`AssetType`/`Client` visíveis só na própria empresa (ADR 0003).
- **INV2.** Componente tem o mesmo `company_id` da raiz.
- **INV3.** Árvore sem ciclos.
- **INV4.** `client_id`, quando presente, referencia um `Client` ativo da mesma empresa
  (`company_id`). `client_id` nulo significa patrimônio próprio (não há `owner_kind` a manter
  consistente — eliminado por construção).
- **INV5.** `default_quantity ≥ 0`; cardinalidade real é da instância.

---

## 10. Fluxos

### Principal — cadastrar ativo e vincular à inspeção

1. Define-se (ou reusa-se) o `AssetType` "Veículo" com blueprint [4× Roda, 2× Porta, 1×
   Suspensão].
2. Cadastra-se o `Asset` "Veículo placa ABC" → o sistema expande o blueprint em componentes.
3. (Opcional) ajusta-se a árvore (remove/adiciona componentes; caminhão → 6 Rodas).
4. Ao iniciar uma inspeção, seleciona-se o ativo alvo (`submissions.asset_id`).
5. A inspeção corre normalmente (campos do formulário); o vínculo dá histórico por objeto.

### Alternativo — serviço a terceiros

- Cadastra-se o `Client` "Transportadora Y"; o `Asset` recebe `client_id = Y` (sem
  `owner_kind`). O restante é igual.

### Cenários de erro

- **Ciclo na árvore** (definir um ativo como filho de seu descendente) → rejeitado (INV3).
- **`client_id` de cliente de outra empresa** → rejeitado (INV4).
- **Componente de empresa diferente da raiz** → rejeitado (INV2).
- **Excluir tipo em uso por instâncias** → bloqueado/soft delete (a definir na spec).

---

## 11. Riscos

### Técnicos
- **R-T1. Modelagem da árvore.** Adjacency list é simples mas consultas recursivas profundas
  (toda a subárvore) exigem CTE recursiva. *Mitigação:* CTE recursiva no repositório; closure
  table só se medido como gargalo.
- **R-T2. Atributos sem schema forte.** Configs inconsistentes. *Mitigação:* validar
  `attributes_json` contra `attributes_schema` no service (padrão ADR 0007).

### Negócio
- **R-N1. Complexidade de UX da árvore.** Usuário se perde montando componentes. *Mitigação:*
  blueprint do tipo gera a árvore pronta; edição é exceção.

### Operacionais
- **R-O1. Crescimento de linhas** (muitos componentes por ativo). *Mitigação:* índices por
  tenant; medir antes de otimizar.

---

## 12. Estratégia de Implementação

- **Fase 1.** `clients` (mínimo) + `asset_types` + `assets` (árvore, `client_id` nullable, sem
  blueprint automático) + CRUD + telas. Listagem de ativos por cliente.
- **Fase 2.** `asset_type_components` (blueprint) + expansão automática ao criar instância.
- **Fase 3.** `submissions.asset_id` (vínculo da inspeção ao ativo) + histórico por objeto/cliente.
- **Fase 4.** Atributos ricos do cliente (CNPJ, contato) — quando o laudo exigir (DR-0005).

> **Nota de faseamento (beachhead = empresa de inspeção, 2026-06-08).** Como o primeiro cliente
> organiza tudo por cliente externo (`cliente → ativos → inspeções → laudo`), o `Client` subiu
> para a **Fase 1** (antes Fase 3) e o **vínculo da inspeção ao ativo** (`submissions.asset_id`)
> subiu para a **Fase 3** (antes Fase 4) — pois a inspeção precisa estar ligada ao ativo/cliente
> para o laudo fazer sentido já no primeiro produto utilizável. A árvore profunda e o blueprint
> automático (Fase 2) podem vir depois. Cada fase continua aditiva; a Fase 3 é pré-requisito do
> DR-0002.

---

## 13. Critérios de Aceitação

- **CA1.** É possível criar dois tipos de ativo de domínios diferentes (ex.: Veículo e
  Apartamento) **sem** mudança de schema.
- **CA2.** Um ativo pode ter componentes em árvore de profundidade ≥ 2 (ex.: Veículo → Suspensão
  → Amortecedor).
- **CA3.** A cardinalidade de componentes da instância pode divergir do blueprint do tipo.
- **CA4.** Um ativo pode ser criado **com** `client_id` (pertence ao cliente) ou **sem**
  (patrimônio próprio); listar ativos por cliente retorna apenas os daquele cliente; `client_id`
  de outra empresa é rejeitado.
- **CA5.** Uma inspeção pode ser criada com e sem `asset_id` (retrocompatível).
- **CA6.** Nenhum ativo/tipo/cliente vaza entre empresas (consultas filtram `company_id`).
- **CA7.** Tentar criar ciclo na árvore é rejeitado com erro RFC 7807.

---

## 14. Questões em Aberto

> **Todas as questões fundamentais (Q1–Q5) foram decididas em 2026-06-08.** O que resta são
> refinamentos de menor risco, marcados *Em aberto*, a resolver na spec técnica.

- **Q1. DECIDIDO (2026-06-08).** Abordagem **híbrida**: `asset_type_components` carrega
  `(label, default_quantity, position)`. Default de UX = quantidade ("Roda" ×4 → gera Roda 1..4);
  slots nomeados = múltiplas linhas com `default_quantity = 1` ("Roda DD", "Roda DE"…). O nome
  final fica no `assets.identifier` (livre). Cardinalidade real é da **instância** (RN2) —
  caminhão → 6 rodas sem criar tipo novo. O modelo acomoda os dois sem escolher um.
- **Q2. DECIDIDO (2026-06-08).** `Client` é entidade **mínima desde a Fase 1**
  (`id, company_id, name, is_active`) — porque o primeiro cliente esperado é uma **empresa de
  inspeção**, cujo fluxo primário é `cliente externo → ativos → inspeções → laudo`. O vínculo
  do ativo ao cliente usa **`assets.client_id` nullable como discriminador único** (nulo =
  patrimônio próprio; preenchido = ativo de cliente externo), **eliminando o `owner_kind`**.
  Atributos ricos do cliente (CNPJ, contato) entram quando o laudo exigir (DR-0005). Ver nota
  de faseamento na seção 12.
- **Q3. DECIDIDO (2026-06-08).** Escrita de `asset_types`, `assets` e `clients` = **MANAGER+**;
  leitura = qualquer membro. Como os guards são **hierárquicos** (ADR 0004,
  `ALLOWED_MANAGER_ROLES = {OWNER, ADMIN, MANAGER}`), MANAGER+ **já inclui ADMIN e OWNER** com
  permissão de escrita — não é preciso um guard separado para ADMIN.
- **Q4. DECIDIDO (2026-06-08).** **Soft delete**, nunca hard delete (ADR 0009): `assets.status`
  (`active`/`inactive`/`retired`) e `asset_types.is_active`. Tipo arquivado bloqueia **novas**
  instâncias; instâncias e histórico de inspeções permanecem intactos. Hard delete não é opção
  para ativo de negócio (preserva Submissions, relatórios e auditoria).
- **Q5. DECIDIDO (2026-06-08).** `attributes_schema` **opcional** (`asset_types.attributes_schema`
  JSONB nullable). Se presente, o service valida `attributes_json` contra ele e a UI renderiza
  inputs tipados; se ausente, atributos são chave-valor livres. Segue a filosofia do `config_json`
  (ADR 0007): flexível, validado quando definido; começa permissivo, endurece sob demanda.

*Em aberto (refinamentos menores para a spec, não bloqueiam o ADR):* (a) relaxar futuramente
para INSPECTOR cadastrar ativo em campo (hoje MANAGER+); (b) excluir tipo em uso — soft delete
simples vs aviso de impacto.

---

## 15. Evoluções Futuras

> Fora do escopo deste DR.

- **Inspeção por componente** — enumerar componentes no checklist (**DR-0002**).
- **Recorrência por ativo** — agendamento de inspeção, alerta de vencimento, histórico.
- **Portal do cliente externo** — login do cliente para ver seus ativos/laudos.
- **Importação de ativos em massa** (CSV/planilha de frota).
- **Geolocalização/QR por ativo** — identificar o objeto físico em campo.
