# ADR-0007 — Configuração de campo via `config_json` (JSONB)

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

Tipos de campo distintos têm parâmetros distintos (peso, permitir N/A, opções de select), e
novos parâmetros tendem a surgir. Modelar cada parâmetro como coluna geraria colunas esparsas e
migrações frequentes.

## Decisão

Guardar a configuração específica de campo em **`form_fields.config_json` (JSONB)**. Verificado
em `forms/schemas.py` e `submissions/service.py`:

- `weight` (float, default 1.0) — peso no score; o motor lê de qualquer campo não-`section`.
- `allow_na` (bool) — habilita N/A em `boolean`.
- `options` (string[]) — opções do `select` (validado no schema: select exige ≥1 opção).
- O service interpreta/valida o conteúdo; a estrutura é responsabilidade da aplicação.

## Consequências

- Novos parâmetros de campo não exigem migração de schema.
- Sem colunas esparsas/nulas por tipo de campo.
- **Contrato implícito:** a validação de cada chave vive no código (schema/service), não no
  banco — risco de configs inconsistentes se não validadas.
- O peso é uma capacidade latente de qualquer campo, ainda que a UI só o exponha em `boolean`.

## Alternativas descartadas

- **Uma coluna por parâmetro:** explosão de colunas nulas e migração a cada novo parâmetro.
- **Tabela `field_config` (EAV):** consultas complexas e overhead para um JSON pequeno e local.
- **Subclasses/tabelas por tipo de campo:** rigidez estrutural alta para variações pequenas de
  configuração.
