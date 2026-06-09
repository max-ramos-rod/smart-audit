# ADR-0008 — Score ponderado a partir de `submission_conformities`

**Status:** Aceita · **Data:** 2026-06-08

## Contexto

A nota de uma inspeção (0–100) não é média simples de respostas: o inspetor avalia a
**conformidade** de cada item, e essa avaliação pode acontecer em etapa distinta de responder o
campo. Itens N/A não devem penalizar nem inflar a nota.

## Decisão

Separar **resposta** (`submission_values`) de **avaliação de conformidade**
(`submission_conformities`, `CHECK status IN (conforme, nao_conforme)`) e calcular o score a
partir das conformidades. Verificado em `SubmissionService.calculate_score`:

```
score = round( Σ weight(conforme) / Σ weight(avaliados em submission_conformities) * 100 , 2 )
```

- Fonte do score é `submission_conformities`, não `submission_values`.
- Campos sem registro de conformidade — inclusive N/A — ficam **fora do denominador**.
- `weight` (`config_json`, default 1.0) é lido de qualquer campo não-`section`.
- `score_breakdown.total_boolean` conta todos os campos não-`section` (nome por compat);
  `na_count` retorna sempre `0` (cálculo migrou para o domínio de conformidades).

## Consequências

- Inspetor pode responder e avaliar conformidade em momentos separados.
- N/A e itens não avaliados não distorcem a nota.
- Ponderação por item permite refletir criticidade.
- **Acoplamento de evolução:** mudar a fórmula ou adicionar tipo que pontue exige tocar
  `calculate_score`/`calculate_score_breakdown`.
- Nomes legados (`total_boolean`, `na_count=0`) podem confundir quem lê o contrato — mantidos
  por compatibilidade.

## Alternativas descartadas

- **Score derivado de `submission_values` (resposta = conformidade):** impede avaliar
  conformidade separada da resposta e complica N/A.
- **Média não ponderada:** não distingue itens críticos de triviais.
- **Penalizar N/A no denominador:** distorce a nota de checklists com itens não aplicáveis.
