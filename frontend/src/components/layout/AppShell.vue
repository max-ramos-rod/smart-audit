<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Separator } from 'radix-vue'

import BaseButton from '@/components/ui/BaseButton.vue'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'

const authStore = useAuthStore()
const contextStore = useContextStore()
const router = useRouter()

const companies = computed(() => contextStore.companies)
const activeCompanyId = computed(() => contextStore.activeCompany?.id ?? null)

async function handleCompanyChange(event: Event) {
  const target = event.target as HTMLSelectElement
  await contextStore.selectCompany(target.value)
}

function logout() {
  authStore.logout()
  contextStore.reset()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="grid min-h-screen gap-4 p-3 lg:grid-cols-[280px_minmax(0,1fr)] lg:p-4">
    <aside
      class="surface-panel flex flex-col gap-5 p-4 sm:p-5 lg:sticky lg:top-4 lg:h-[calc(100vh-2rem)] lg:justify-between"
    >
      <div class="space-y-5">
        <div class="flex items-start justify-between gap-4 lg:block lg:space-y-3">
          <div class="space-y-2">
            <p class="eyebrow">Smart Audit</p>
            <h1 class="max-w-56 text-xl font-semibold tracking-tight text-sa-text sm:text-2xl">
              Painel operacional
            </h1>
            <p class="muted-copy max-w-60 text-sm">
              Base única para auditorias, execução de checklist e rastreabilidade por empresa.
            </p>
          </div>

          <BaseButton type="button" variant="ghost" class="lg:hidden" @click="logout">Sair</BaseButton>
        </div>

        <div class="rounded-3xl border border-[color:var(--sa-line)] bg-white/70 p-4 lg:hidden">
          <p class="eyebrow">Sessão autenticada</p>
          <strong class="mt-2 block text-sm font-semibold text-sa-text">{{ authStore.user?.name }}</strong>
          <span class="mt-1 block text-sm text-sa-muted">{{ authStore.user?.email }}</span>
        </div>

        <Separator class="h-px bg-[color:var(--sa-line)]" />

        <label class="grid gap-2">
          <span class="text-sm text-sa-muted">Empresa ativa</span>
          <select :value="activeCompanyId ?? ''" @change="handleCompanyChange">
            <option v-for="company in companies" :key="company.id" :value="company.id">
              {{ company.name }} · {{ company.role }}
            </option>
          </select>
        </label>

        <nav class="grid grid-cols-2 gap-2 lg:grid-cols-1">
          <RouterLink
            to="/"
            class="rounded-2xl px-4 py-3 text-center text-sm font-medium text-sa-text transition hover:bg-white/70 lg:text-left"
            active-class="bg-gradient-to-br from-sa-brand to-sa-brand-strong text-white shadow-lg shadow-amber-950/15"
          >
            Resumo
          </RouterLink>
          <RouterLink
            to="/users"
            class="rounded-2xl px-4 py-3 text-center text-sm font-medium text-sa-text transition hover:bg-white/70 lg:text-left"
            active-class="bg-gradient-to-br from-sa-brand to-sa-brand-strong text-white shadow-lg shadow-amber-950/15"
          >
            Usuários
          </RouterLink>
          <RouterLink
            to="/forms"
            class="rounded-2xl px-4 py-3 text-center text-sm font-medium text-sa-text transition hover:bg-white/70 lg:text-left"
            active-class="bg-gradient-to-br from-sa-brand to-sa-brand-strong text-white shadow-lg shadow-amber-950/15"
          >
            Formulários
          </RouterLink>
          <RouterLink
            to="/submissions"
            class="rounded-2xl px-4 py-3 text-center text-sm font-medium text-sa-text transition hover:bg-white/70 lg:text-left"
            active-class="bg-gradient-to-br from-sa-brand to-sa-brand-strong text-white shadow-lg shadow-amber-950/15"
          >
            Inspeções
          </RouterLink>
          <RouterLink
            to="/teams"
            class="rounded-2xl px-4 py-3 text-center text-sm font-medium text-sa-text transition hover:bg-white/70 lg:text-left"
            active-class="bg-gradient-to-br from-sa-brand to-sa-brand-strong text-white shadow-lg shadow-amber-950/15"
          >
            Equipes
          </RouterLink>
        </nav>
      </div>

      <div class="hidden space-y-4 lg:block">
        <Separator class="h-px bg-[color:var(--sa-line)]" />
        <div class="space-y-1">
          <p class="eyebrow">Sessão autenticada</p>
          <strong class="block text-sm font-semibold text-sa-text">{{ authStore.user?.name }}</strong>
          <span class="block text-sm text-sa-muted">{{ authStore.user?.email }}</span>
          <RouterLink
            to="/profile"
            class="mt-1 block text-sm font-medium text-sa-brand hover:underline"
          >
            Meu perfil
          </RouterLink>
        </div>
        <BaseButton type="button" variant="ghost" :full-width="true" @click="logout">Sair</BaseButton>
      </div>
    </aside>

    <main class="grid content-start gap-4">
      <slot />
    </main>
  </div>
</template>
