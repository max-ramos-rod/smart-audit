<!--
Antes de abrir: o fluxo do projeto é Documentação → Código → Implementação.
Veja docs/ai/START_HERE.md e docs/ai/AI_RULES.md. Marque o que se aplica; deixe N/A no resto.
-->

## Resumo

<O que muda e por quê. Link para issue/contexto, se houver.>

## Tipo de mudança

- [ ] Correção (bugfix)
- [ ] Funcionalidade
- [ ] Refatoração / interno
- [ ] Documentação
- [ ] Infra / CI

## Checklist anti-drift (código ↔ documentação)

Marque o gatilho e confirme a documentação correspondente atualizada. **Se mudou o
comportamento, a doc da fonte única precisa acompanhar** (ver `docs/adr/` e `docs/ai/`).

- [ ] **Rota/endpoint** novo ou alterado → atualizei a lista/contrato em
      `docs/Arquitetura_Smart_Audit.md` (§7 e o bounded context) e, se mudou request/response,
      o contrato relevante.
- [ ] **Modelo / migration** (tabela, coluna, constraint, enum) → atualizei
      `docs/DER_Smart_Audit.md` e `docs/ai/AI_MODELS.md`.
- [ ] **Regra de negócio / padrão de fluxo** (camadas, async, RBAC, score, notificações) →
      atualizei `CLAUDE.md` e/ou `docs/ai/AI_RULES.md` / `docs/ai/AI_DECISIONS.md`.
- [ ] **Decisão arquitetural** tomada ou alterada → criei/atualizei um ADR a partir de
      `docs/adr/template.md` e ajustei o índice `docs/adr/README.md` (Status / Supersedes /
      Superseded-by). Decisões substituídas viram **Supersedida**, não são apagadas.
- [ ] **Comando / workflow** de dev mudou → atualizei `docs/ai/AI_WORKFLOWS.md`.
- [ ] **Nenhuma** das anteriores se aplica (mudança sem impacto em documentação).

## Verificação

- [ ] Backend: `python -m pytest` passou (com Postgres migrado).
- [ ] Frontend: `npm run build` (inclui `vue-tsc`) e `npm test` passaram, quando aplicável.
- [ ] Verifiquei o comportamento no código real — não assumi (ver `docs/ai/START_HERE.md`).

## Notas adicionais

<Riscos, decisões em aberto, pontos para revisão.>
