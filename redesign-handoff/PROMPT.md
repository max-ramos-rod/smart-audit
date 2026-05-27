# Smart Audit - Redesign Implementation Prompt

Voce esta trabalhando no frontend do Smart Audit.

## Contexto

Projeto atual:

- Vue 3
- Pinia
- Vue Router
- Tailwind CSS v4
- TypeScript
- Vitest

Estado importante:

- o redesign ja foi parcialmente absorvido pelo app real
- o shell, o login e a base de estilos ja nao estao no estado antigo
- existem mais telas e rotas no app atual do que no momento em que este handoff foi criado

## Objetivo

Usar esta pasta como guia de redesign incremental.

Nao trate este material como pacote de substituicao total.

## Regras

1. Nao altere `stores/`, `services/` ou `types/` sem necessidade funcional real.
2. Preserve logica Vue existente.
3. Preserve rotas existentes, a menos que o objetivo seja explicitamente corrigir navegacao.
4. Compare sempre o arquivo do handoff com o arquivo real antes de aplicar qualquer mudanca.
5. Valide com `npm test` e `npm run build`.

## Procedimento recomendado

### Passo 1

Comparar:

- `redesign-handoff/style.css`
- `frontend/src/style.css`

Aplicar apenas o que ainda nao estiver absorvido.

### Passo 2

Comparar:

- `redesign-handoff/AppShell.vue`
- `frontend/src/components/layout/AppShell.vue`

Preservar:

- rotas reais do app
- iconografia atual
- estado de sessao atual
- selecao de empresa atual

### Passo 3

Comparar:

- `redesign-handoff/LoginView.vue`
- `frontend/src/views/auth/LoginView.vue`

Preservar:

- fluxo de login atual
- bootstrap do contexto

### Passo 4

Aplicar o mesmo sistema visual nas views operacionais:

- dashboard
- formularios
- detalhe de formulario
- historico de versoes
- inspecoes
- detalhe de inspecao
- relatorio de inspecao
- usuarios
- equipes
- perfil

### Passo 5

Revisar as telas auxiliares:

- busca
- notificacoes
- configuracoes da empresa

Nessas telas, priorizar consistencia visual e clareza de UX, sem inventar fluxo de backend que nao exista.

## O que validar ao final

- build do frontend
- testes Vitest
- navegacao desktop
- navegacao mobile
- legibilidade de tipografia
- consistencia de espacamento
- ausencia de rotas quebradas

## Observacoes

- O app atual possui rotas e views que nao existiam no momento original do handoff.
- O link `forgot-password` do login deve ser tratado como pendencia funcional se continuar sem rota.
- O foco aqui e evolucao segura do frontend real, nao retorno a um snapshot antigo.
