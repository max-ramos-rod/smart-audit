# ADR-0015 — Modelo de ativos genéricos (árvore de componentes + `client_id` discriminador)

**Status:** Aceita · **Data:** 2026-06-08 · **Implementada:** 2026-06-10 (Fase 1)
**Supersedes:** — · **Superseded-by:** —

<!--
Aceita na Fase 1 (DR-0001): instância (árvore) + tipo + cliente discriminador, com soft
delete em cascata e reativação top-down. Blueprint de composição (asset_type_components) e
validação de attributes_schema ficaram fora da Fase 1 — ver "## Implementação (Fase 1)".
-->

## Contexto

O Smart Audit precisa representar o **objeto inspecionado** — veículo, apartamento, máquina,
ponte rolante, contrato — e suas **partes** (4 rodas, 2 portas, suspensão). Hoje o formulário é
"plano": não há entidade de objeto nem de componente; para granularidade por roda é preciso
criar campos manuais (rígido) ou perder detalhe, e o inspetor pode esquecer um componente. Não
há histórico por objeto nem como distinguir patrimônio próprio de ativo de cliente.

Há ainda uma força de negócio verificada: o **primeiro cliente esperado é uma empresa de
inspeção** (serviço a terceiros), cujo fluxo primário é `cliente externo → ativos → inspeções →
laudo`. O modelo precisa nascer com a dimensão de cliente, sob risco de migração conceitual.

Restrições do projeto que moldam a decisão: multi-tenancy por `company_id` (ADR-0003);
configuração flexível em JSONB validada no service (ADR-0007); soft delete por semântica da
entidade (ADR-0009); autorização por guards hierárquicos de papel (ADR-0004); arquitetura em
camadas (ADR-0001). Decisão e alternativas detalhadas em
[`docs/design-records/DR-0001-ativos-genericos.md`](../design-records/DR-0001-ativos-genericos.md).

## Decisão

Adotar um **modelo de ativos genérico**, sem tabela por domínio, com três camadas e um
discriminador de dono único. (Núcleo implementado na Fase 1 — ver "## Implementação (Fase 1)".)

- **Tipo (molde):** `asset_types` define a forma de um tipo (atributos esperados + blueprint de
  componentes), por empresa. Análogo ao papel de `form_versions` para campos (ADR-0005).
- **Blueprint (composição entre tipos):** `asset_type_components(label, default_quantity,
  position)` descreve "um Veículo é composto de N Rodas, M Portas". Abordagem **híbrida** (Q1):
  quantidade gera N instâncias; slots nomeados = N linhas com `default_quantity = 1`.
- **Instância (árvore):** `assets` é o objeto concreto, com `attributes_json` (JSONB) e
  `parent_asset_id` **nullable** (NULL = raiz; preenchido = componente). **Um componente é
  apenas um `asset` cujo pai é outro `asset`** — colapsa "ativo" e "componente" numa estrutura
  recursiva (adjacency list) de profundidade livre. A **cardinalidade real é decidida na
  instância**, não no tipo (caminhão → 6 rodas sem criar tipo novo).
- **Dono via discriminador único:** `assets.client_id` **nullable** distingue patrimônio próprio
  (NULL) de ativo de cliente externo (preenchido). **Não há campo `owner_kind`** — o próprio
  `client_id` é o discriminador (Q2). `clients` é entidade **mínima** (`id, company_id, name,
  is_active`) presente **desde a primeira fase**, por causa do beachhead empresa de inspeção;
  atributos ricos (CNPJ, contato) entram com o laudo (DR-0005).
- **Atributos sem schema forte:** `asset_types.attributes_schema` (JSONB) é **opcional** (Q5);
  quando presente, o service valida `attributes_json` contra ele; quando ausente, atributos são
  chave-valor livres — mesma filosofia do `config_json` (ADR-0007).
- **Soft delete** (Q4, ADR-0009): `assets.status` e `asset_types.is_active`; nunca hard delete
  (preserva inspeções, relatórios e auditoria). Tipo arquivado bloqueia novas instâncias;
  histórico permanece.
- **Autorização** (Q3, ADR-0004): escrita de `asset_types`, `assets` e `clients` =
  **MANAGER+** (`get_manager_membership`, hierárquico — já inclui ADMIN e OWNER); leitura = todo
  membro.
- **Isolamento:** toda entidade carrega `company_id` e filtra por ele (ADR-0003).

A repetição de campo por componente na inspeção (enumerar as 4 rodas no checklist) **não** faz
parte desta decisão — é tratada à parte porque toca o modelo híbrido de respostas (ADR-0006);
ver DR-0002.

## Implementação (Fase 1)

Entregue em [`docs/specs/SPEC-DR-0001-Fase1-Ativos.md`](../specs/SPEC-DR-0001-Fase1-Ativos.md) /
[`PLANO-DR-0001-Fase1.md`](../specs/PLANO-DR-0001-Fase1.md) (tarefas T1–T8).

**Schema** — migration `c1d2e3f4a5b6_add_assets_clients_asset_types.py`, três tabelas em ordem
de dependência:

- `clients` — [`Client`](../../backend/app/db/models/clients.py): entidade mínima (`company_id`,
  `name`, `is_active`), como decidido para o beachhead.
- `asset_types` — [`AssetType`](../../backend/app/db/models/asset_types.py): `name`,
  `description`, `attributes_schema` (JSONB **nullable**), `is_active`.
- `assets` — [`Asset`](../../backend/app/db/models/assets.py): `asset_type_id`,
  `parent_asset_id` (nullable, self-FK `ON DELETE CASCADE`), `client_id` (nullable), `identifier`,
  `attributes_json` (JSONB), `status`. Árvore via `relationship` `parent`/`components`
  (adjacency list). CHECKs `ck_assets_client_only_on_root` (M6) e `ck_assets_status`; índices por
  `company_id` (tenant).

**API** (`/api/v1`, registradas em
[`router.py`](../../backend/app/api/v1/router.py)): `clients_router`, `asset_types_router`,
`assets_router`. Cada domínio segue `api → service → repository` (ADR-0001); escrita
`get_manager_membership`, leitura `get_current_membership` (Q3/ADR-0004); isolamento por
`company_id` (ADR-0003).

**Soft delete (Q4/ADR-0009).** `clients`/`asset_types` por `is_active`; `assets` por `status`.
Desativar um ativo desativa **toda a subárvore** em cascata na mesma transação
(`AssetRepository.deactivate_subtree`, CTE recursiva — V6); reativação é **top-down** — só com o
pai ativo, sem cascatear (`AssetService.update_asset` — V7).

**Frontend.** Telas de `clients`, `asset-types` e `assets` (cadastro raiz/componente + filhos
diretos + filtros), sob `/app/` (T6–T8).

**Fora da Fase 1 (adiado, sem contradizer a decisão):**

- **Blueprint de composição entre tipos** (`asset_type_components`): a cardinalidade real é
  decidida na instância; o molde de composição não foi necessário para a Fase 1.
- **Validação de `attributes_schema`** contra `attributes_json` (M1): a coluna existe, mas os
  atributos são aceitos livres — mesma postura adiável do `config_json` (ADR-0007).

## Consequências

- Um único modelo representa qualquer objeto e qualquer profundidade; adicionar um domínio novo
  (hospital, ponte) **não** exige migração de schema.
- O discriminador `client_id` nullable atende os dois mercados (próprio × serviço a terceiros)
  sem bifurcar o produto e sem a invariante extra que um `owner_kind` separado exigiria.
- `clients` desde a Fase 1 evita migração conceitual no beachhead empresa de inspeção.
- **Custo:** atributos em JSONB não têm validação no banco — a consistência depende do service
  (mesmo trade-off do ADR-0007).
- **Custo:** a árvore em adjacency list exige CTE recursiva para ler subárvores; aceitável no
  porte atual. Closure table/`ltree` só se consultas recursivas profundas virarem gargalo medido
  (otimização adiada de propósito).
- **Acoplamento de evolução:** vincular a inspeção ao ativo (`submissions.asset_id`) e, depois, a
  inspeção por componente (ADR-0006/DR-0002) dependem deste modelo. O `submissions.asset_id` é a
  fronteira que destrava o DR-0002.
- Cresce o número de linhas (componentes por ativo); mitigado por índices por tenant
  (`company_id`).

## Alternativas descartadas

- **Tabela por domínio (`vehicles`, `apartments`, `machines`…):** explosão de tabelas e
  migrações; intratável como produto genérico; contradiz o posicionamento de motor genérico.
- **Tabela `asset_components` separada de `assets`:** duplica o conceito (componente tem as
  mesmas propriedades de um ativo e pode ter sub-componentes); dificulta sub-árvores. Componente
  **é** um `asset` com pai.
- **Closure table / materialized path / `ltree` desde o início:** otimização prematura; Postgres
  lida com a árvore em adjacency list no porte atual; o eixo real de escala é o particionamento
  por tenant.
- **`owner_kind` (enum) + `client_id`:** redundante — `client_id` nullable já discrimina
  próprio × cliente; o enum só adicionaria uma invariante a manter consistente.
- **`Client` apenas como atributo de texto no ativo:** sem listagem por cliente, sem dados para
  o laudo, sem reuso; insuficiente para empresa de inspeção.
- **`attributes_schema` obrigatório por tipo:** adiciona fricção (definir schema antes de usar)
  sem ganho proporcional num domínio genérico; opcional segue a filosofia do `config_json`.
- **Hard delete de tipos/ativos:** órfãnaria inspeções/relatórios; viola a preservação de
  histórico (ADR-0009).
