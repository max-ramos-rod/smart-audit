# Smart Audit — Redesign Implementation Prompt

Você é um desenvolvedor frontend sênior trabalhando no projeto **Smart Audit**.

## Contexto

Este projeto é um SaaS B2B de auditorias operacionais com:
- **Frontend:** Vue 3 + Pinia + Vue Router + TailwindCSS v4 + TypeScript
- **Estrutura:** `frontend/src/` com stores/, services/, views/, components/, types/

## Objetivo desta tarefa

Implementar o redesign visual do produto. A lógica de negócio (stores, services, types, router guards) **não muda**. Apenas CSS, layout e markup das views e componentes.

## Regras importantes

1. **Não altere nada em:** `stores/`, `services/`, `types/`, `router/index.ts`
2. **Preserve toda lógica Vue:** `v-model`, `v-if`, `v-for`, `@submit`, `computed`, `onMounted`, etc.
3. **Siga o padrão Tailwind v4 do projeto:** use `@layer base`, `@layer components`, `@theme` no style.css
4. **Execute os passos na ordem indicada** — cada passo depende do anterior

---

## PASSO 1 — Substituir frontend/src/style.css

Substitua o conteúdo COMPLETO do arquivo `frontend/src/style.css` pelo arquivo `redesign-handoff/style.css` fornecido nesta pasta.

Este arquivo contém:
- Novos tokens CSS (paleta azul professional)
- Classes utilitárias atualizadas (surface-panel, eyebrow, status-chip)
- Estilos do AppShell (sidebar, bottom nav, mobile header)
- Estilos do Login (split layout)
- Utilitários de layout (filter-tabs, sticky-act, role-badge)

---

## PASSO 2 — Atualizar frontend/index.html

Adicionar Google Fonts no `<head>`, ANTES de qualquer outro link:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet" />
```

---

## PASSO 3 — Substituir frontend/src/components/layout/AppShell.vue

Substituir o conteúdo COMPLETO por `redesign-handoff/AppShell.vue`.

O novo AppShell tem:
- Sidebar escura fixa (desktop) com logo, nav links, seletor de empresa, usuário
- Mobile header fixo no topo com logo + avatar
- Bottom nav fixo no rodapé (mobile)
- Sem glass morphism — flat design

A lógica Vue (handleCompanyChange, logout, computed companies) está preservada.

---

## PASSO 4 — Substituir frontend/src/views/auth/LoginView.vue

Substituir o conteúdo COMPLETO por `redesign-handoff/LoginView.vue`.

O novo LoginView tem:
- Split layout: painel escuro com branding (desktop) + formulário à direita
- Link "Esqueceu sua senha?" abaixo do botão
- Lógica submit() preservada — apenas markup muda

---

## PASSO 5 — Atualizar frontend/src/views/dashboard/HomeView.vue

O filtro de período (?period=7d|30d|90d|all) JÁ ESTÁ implementado. Apenas atualizar as classes visuais:

**5a.** Adicionar `class="page"` na tag raiz do template (`<AppShell>` → primeiro filho):
```vue
<!-- ANTES -->
<AppShell>
  <section class="surface-panel ...">

<!-- DEPOIS -->
<AppShell>
  <div class="page">
    <section class="surface-panel ...">
  </div>
</AppShell>
```

**5b.** Nos cards de métrica, trocar de `surface-panel p-5` para o padrão flat:
```vue
<!-- ANTES -->
<article class="surface-panel p-5">
  <span class="eyebrow">Total</span>
  <strong class="mt-2 block text-3xl ...">{{ stats?.total_submissions ?? '—' }}</strong>

<!-- DEPOIS -->
<article class="scard">
  <div class="sc-label">Total</div>
  <div class="sc-value">{{ stats?.total_submissions ?? '—' }}</div>
  <div class="sc-desc">inspecoes criadas</div>
</article>
```

**5c.** Substituir a tabela de inspeções recentes por list rows:
```vue
<!-- Para cada submission em stats.recent: -->
<div class="lrow" @click="router.push({ name: 'submission-detail', params: { id: submission.id } })">
  <div class="lrow-main">
    <div class="lrow-title">{{ submission.form_name }}</div>
    <div class="lrow-sub">Iniciada {{ new Date(submission.started_at).toLocaleString('pt-BR') }}</div>
  </div>
  <div class="lrow-end">
    <span v-if="submission.score !== null" class="score-val"
      :class="submission.score >= 85 ? 'ok' : submission.score >= 65 ? 'warn' : 'err'">
      {{ submission.score }}%
    </span>
    <span class="status-chip" :class="{
      'status-chip--warn': submission.status === 'in_progress',
      'status-chip--inactive': submission.status === 'cancelled'
    }">{{ statusLabel(submission.status) }}</span>
  </div>
</div>
```

---

## PASSO 6 — Atualizar frontend/src/views/submissions/SubmissionsView.vue

Os filtros server-side JÁ ESTÃO implementados. Atualizar apenas visual das tabs:

**6a.** Substituir as tabs de status por filter-tabs:
```vue
<div class="filter-tabs">
  <button
    v-for="opt in STATUS_OPTIONS"
    :key="String(opt.value)"
    type="button"
    class="filter-tab"
    :class="{ active: activeStatus === opt.value }"
    @click="setStatus(opt.value)"
  >
    {{ opt.label }}
    <span v-if="opt.count != null" style="opacity:.6">({{ opt.count }})</span>
  </button>
</div>
```

**6b.** Substituir cards/rows de inspeção por `.lrow` (mesmo padrão do dashboard).

---

## PASSO 7 — Atualizar frontend/src/views/submissions/SubmissionDetailView.vue

A validação de campos obrigatórios JÁ ESTÁ implementada. Atualizar visual:

**7a.** Campo `select` com opções reais (se config_json.options existir):
```vue
<!-- ANTES -->
<input v-else-if="field.field_type === 'select'" v-model="draftAnswers[field.key]" type="text" />

<!-- DEPOIS -->
<template v-else-if="field.field_type === 'select'">
  <select
    v-if="field.config_json?.options?.length"
    v-model="draftAnswers[field.key]"
    :disabled="isCompleted"
  >
    <option value="">— Selecione —</option>
    <option v-for="opt in field.config_json.options" :key="opt" :value="opt">{{ opt }}</option>
  </select>
  <input v-else v-model="draftAnswers[field.key]" type="text" :disabled="isCompleted" />
</template>
```

**7b.** ScoreBreakdown na seção de score (após inspeção concluída):
```vue
<div v-if="submission.score_breakdown" class="score-breakdown-grid">
  <div class="sbd-card ok">
    <div class="sbd-label">Conformes</div>
    <div class="sbd-val">{{ submission.score_breakdown.conformes }}</div>
  </div>
  <div class="sbd-card err">
    <div class="sbd-label">Não conformes</div>
    <div class="sbd-val">{{ submission.score_breakdown.nao_conformes }}</div>
  </div>
  <div class="sbd-card neu">
    <div class="sbd-label">Sem resposta</div>
    <div class="sbd-val">{{ submission.score_breakdown.sem_resposta }}</div>
  </div>
</div>
```

**7c.** Sticky actions no rodapé:
```vue
<div class="sticky-act" v-if="!isCompleted">
  <button type="button" class="btn-secondary" @click="handleSave">
    {{ isSaving ? 'Salvando...' : savedOnce ? '✓ Salvo' : 'Salvar rascunho' }}
  </button>
  <button type="button" class="btn-primary" @click="handleFinish" :disabled="isFinishing">
    {{ isFinishing ? 'Finalizando...' : 'Finalizar inspeção' }}
  </button>
</div>
```

---

## PASSO 8 — Atualizar frontend/src/views/users/UsersView.vue

**8a.** Adicionar two-col layout:
```vue
<div class="page">
  <div class="users-layout">
    <!-- Formulário lado esquerdo -->
    <div class="card card-p" style="align-self: flex-start; position: sticky; top: 20px;">
      <!-- form existente -->
    </div>
    <!-- Tabela lado direito -->
    <div class="card" style="overflow-x: auto;">
      <!-- tabela existente -->
    </div>
  </div>
</div>
```

**8b.** Role badges:
```vue
<!-- ANTES -->
<td>{{ user.role }}</td>

<!-- DEPOIS -->
<td><span class="role-badge" :class="'role-' + user.role.toLowerCase()">{{ user.role }}</span></td>
```

---

## PASSO 9 — Atualizar frontend/src/views/forms/FormsView.vue

**9a.** Adicionar input de opções para campo select:
```vue
<!-- Dentro do v-for de campos, após o select de field_type -->
<label v-if="field.field_type === 'select'" class="grid gap-2 sm:col-span-2">
  <span>Opções (separadas por vírgula)</span>
  <input
    :value="field.config_json?.options?.join(', ') ?? ''"
    type="text"
    placeholder="Ex: Conforme, Não conforme, Parcial"
    @input="(e) => {
      const opts = e.target.value.split(',').map(o => o.trim()).filter(Boolean)
      field.config_json = opts.length ? { options: opts } : {}
    }"
  />
</label>
```

**9b.** Limpar config_json ao trocar field_type:
```vue
<select v-model="field.field_type" @change="() => { if (field.field_type !== 'select') field.config_json = {} }">
```

**9c.** Adicionar botão "Histórico" em cada card de formulário:
```vue
<button
  type="button"
  class="inline-action"
  @click="router.push({ name: 'form-versions', params: { formId: form.id } })"
>
  Histórico
</button>
```

---

## PASSO 10 — Atualizar frontend/src/views/forms/FormVersionsView.vue

FormVersionsView.vue JÁ EXISTE. Atualizar apenas o visual usando as classes do redesign:
- Wrapper: `<div class="page">`
- Cards de versão: usar `.lrow` com badge de versão em font mono
- Versão atual: border azul `border-sa-brand`

---

## PASSO 11 — Atualizar frontend/src/views/auth/ProfileView.vue

ProfileView.vue JÁ EXISTE. Adicionar tabs:
```vue
<div class="filter-tabs">
  <button class="filter-tab" :class="{ active: tab === 'profile' }" @click="tab = 'profile'">Meu perfil</button>
  <button class="filter-tab" :class="{ active: tab === 'companies' }" @click="tab = 'companies'">Empresas</button>
  <button class="filter-tab" :class="{ active: tab === 'security' }" @click="tab = 'security'">Segurança</button>
</div>

<!-- Conteúdo condicional por tab -->
<div v-if="tab === 'profile'"><!-- formulário existente --></div>
<div v-else-if="tab === 'companies'"><!-- tabela de empresas --></div>
<div v-else-if="tab === 'security'"><!-- formulário de senha --></div>
```

---

## PASSO 12 — Verificação final

Após implementar todos os passos:

```bash
cd frontend
npm run build   # verifica TypeScript + build
npm run dev     # verifica em browser
npm test        # garante que nenhum teste quebrou
```

Verificar visualmente:
- [ ] Login: split layout desktop, centralizado mobile
- [ ] Dashboard: sidebar escura, métricas flat, filter de período funciona
- [ ] Formulários: campo select mostra input de opções
- [ ] Inspeções: tabs server-side, sticky actions, score breakdown
- [ ] Usuários: two-col layout, role badges coloridos
- [ ] Mobile: bottom nav aparece, sidebar some
- [ ] Perfil: 3 tabs funcionando

---

## Arquivos nesta pasta handoff

```
redesign-handoff/
  PROMPT.md          ← este arquivo
  style.css          ← substitui frontend/src/style.css completo
  AppShell.vue       ← substitui frontend/src/components/layout/AppShell.vue
  LoginView.vue      ← substitui frontend/src/views/auth/LoginView.vue
  README.md          ← referência rápida
```
