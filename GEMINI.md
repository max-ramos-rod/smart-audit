# GEMINI.md — Smart Audit

> **Shim de entrada para o Gemini CLI.** Sem regras próprias — aponta para a documentação
> canônica. A fonte única da verdade é o código e os documentos em `docs/`. Não duplicar aqui.

Este projeto mantém suas instruções para agentes em **`docs/ai/`** e em **`AGENTS.md`**.
Antes de qualquer implementação, leia, nesta ordem:

1. [`docs/ai/START_HERE.md`](docs/ai/START_HERE.md)
2. [`docs/ai/AI_RULES.md`](docs/ai/AI_RULES.md)
3. ADRs relevantes em [`docs/adr/`](docs/adr/README.md)

Entrada equivalente para outros agentes: [`AGENTS.md`](AGENTS.md). Referência operacional:
[`CLAUDE.md`](CLAUDE.md).

**Fluxo obrigatório:** Documentação → Código → Implementação. Nunca assuma comportamento —
verifique no código real (models, services, routers, migrations).

**Ao abrir PR:** siga o checklist anti-drift em
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).
