# ADR-0006 — Modelo híbrido de respostas (relacional + snapshot JSON)

**Status:** Aceita · **Data:** 2026-06-08
**Revisão prevista:** [ADR-0016](0016-inspecao-por-componente-revisao-modelo-hibrido.md) (Proposta) — estende este modelo com a dimensão de componente (`asset_id`); o modelo híbrido permanece.

## Contexto

As respostas de uma inspeção precisam, ao mesmo tempo, ser **consultáveis/relatáveis** (filtros
por campo, agregações) e **lidas rapidamente** como um todo (render da inspeção, finalização)
sem N+1 de queries por campo.

## Decisão

Armazenar a resposta **duas vezes, de propósito** (verificado em
`SubmissionService.save_answers`):

1. **Relacional** em `submission_values` (colunas tipadas: `value_text`, `value_number`,
   `value_boolean`, `value_date`, `value_json`) — para queries e relatórios.
2. **Snapshot denormalizado** em `submissions.answers_json` (`{ field_key: valor }`) — para
   leitura rápida.

Ambos são escritos na mesma operação e devem permanecer sincronizados.

> **Revisado pela [ADR-0017](0017-modelo-unificado-de-evidencias.md):** a criação de anexo **não
> escreve mais** `answers_json` — `attachments` passou a ser a fonte da verdade da evidência. O
> modelo híbrido de **respostas** permanece; só o efeito colateral de evidência foi removido.

## Consequências

- Leitura agregada barata via `answers_json`; consultas tipadas via `submission_values`.
- **Risco de divergência**: qualquer escrita de resposta precisa atualizar os dois lados —
  ponto único de manutenção em `save_answers`.
- Ao adicionar tipo de campo, é preciso tratar ambos (`normalize_value`/`extract_value` +
  serialização do snapshot).
- Custo de escrita ligeiramente maior (duas representações).

## Alternativas descartadas

- **Somente relacional:** leitura completa exige juntar/montar todos os campos a cada acesso
  (N+1 ou joins largos).
- **Somente JSON:** perde tipagem, índices e consultas por campo para relatórios/score.
- **Cache externo do snapshot:** adiciona infraestrutura e invalidação; o snapshot em coluna é
  transacionalmente consistente com a resposta.
