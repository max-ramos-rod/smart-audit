# Smart Audit — Redesign Handoff

Pasta com todos os arquivos prontos para implementar o redesign visual no projeto Vue.

## Conteúdo

```
redesign-handoff/
  PROMPT.md        ← Prompt completo para o Claude Code (12 passos)
  style.css        ← Substitui frontend/src/style.css (paleta + AppShell + Login)
  AppShell.vue     ← Substitui frontend/src/components/layout/AppShell.vue
  LoginView.vue    ← Substitui frontend/src/views/auth/LoginView.vue
  README.md        ← Este arquivo
```

## Como usar

### Opção A — Claude Code (recomendado)
1. Abra o Claude Code com o projeto `smart-audit` como contexto
2. Cole o conteúdo de `PROMPT.md` no chat
3. Siga os passos na ordem indicada

### Opção B — Manual (passo a passo)

**Passo 1:** Copiar `redesign-handoff/style.css` → `frontend/src/style.css`

**Passo 2:** Adicionar no `frontend/index.html` (no `<head>`):
```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

**Passo 3:** Copiar `redesign-handoff/AppShell.vue` → `frontend/src/components/layout/AppShell.vue`

**Passo 4:** Copiar `redesign-handoff/LoginView.vue` → `frontend/src/views/auth/LoginView.vue`

**Passos 5-12:** Seguir o `PROMPT.md` para atualizar as views restantes.

## O que muda

| Aspecto | Antes | Depois |
|---|---|---|
| Paleta | Âmbar / bege quente | Azul / slate frio |
| Sidebar | Glass panel lateral flutuante | Dark sidebar fixa |
| Mobile nav | Sem bottom nav | Bottom nav fixo |
| Tipografia | Segoe UI Variable | Plus Jakarta Sans |
| Cards | Blur + transparência | Flat, bordas limpas |
| Botões | Gradiente âmbar | Azul sólido |

## O que NÃO muda

- Toda a lógica Vue (stores, services, types, router)
- Todos os guards e fluxos de autenticação
- Todos os endpoints e chamadas de API
- Testes (Vitest) — todos devem continuar passando

## Verificação final

```bash
cd frontend
npm run build   # TypeScript check + build
npm test        # Vitest — deve passar 37/37
```

## Referência visual

Abrir o arquivo `Smart Audit Redesign.html` no browser para ver o resultado esperado.
Todas as 20 telas estão implementadas no protótipo como referência.
