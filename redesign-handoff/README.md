# Smart Audit - Redesign Handoff

Esta pasta guarda o material de handoff do redesign visual do Smart Audit.

## Papel atual desta pasta

Ela nao representa mais um pacote para ser aplicado por copia integral.

Hoje ela serve como:

- referencia visual do redesign
- historico da direcao de interface adotada
- base para ajustes incrementais no frontend real

Parte importante desse material ja foi absorvida pelo app atual, especialmente:

- `frontend/src/style.css`
- `frontend/src/components/layout/AppShell.vue`
- `frontend/src/views/auth/LoginView.vue`
- tipografia em `frontend/index.html`

## Conteudo

```text
redesign-handoff/
  PROMPT.md
  style.css
  AppShell.vue
  LoginView.vue
  Smart Audit Redesign.html
  README.md
```

## Como usar hoje

### Recomendado

Use esta pasta como comparativo, nao como script de substituicao cega.

Fluxo sugerido:

1. comparar o arquivo do handoff com o arquivo ativo do frontend
2. identificar apenas o delta visual desejado
3. preservar logica, rotas, stores, services e tipos atuais
4. validar com `npm test` e `npm run build`

### Nao recomendado

- sobrescrever `router/index.ts`
- sobrescrever stores ou services
- substituir `AppShell.vue` sem comparar as rotas e navegacao atuais
- assumir que todas as telas citadas no prompt existem exatamente como no momento em que o handoff foi criado

## O que ja esta incorporado

- paleta azul/slate
- tipografia `Plus Jakarta Sans` e `DM Mono`
- shell com sidebar escura e bottom nav mobile
- login com split layout
- classes visuais base como `scard`, `filter-tabs`, `score-breakdown-grid`

## O que pode divergir do app atual

- contagem de testes
- conjunto de telas existentes
- nomes de rotas
- markup real de algumas views
- comportamento de componentes ja ampliados no app

## Validacao

No estado atual do projeto, a verificacao correta e:

```bash
cd frontend
npm run build
npm test
```

Baseline validado em `2026-05-27`:

- `npm run build` OK
- `npm test`: `68 passed`

## Referencia visual

Abra [Smart Audit Redesign.html](/c:/Projetos/smart-audit/redesign-handoff/Smart%20Audit%20Redesign.html) para ver o prototipo visual de referencia.
