<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'

const authStore = useAuthStore()
const contextStore = useContextStore()
const router = useRouter()

const companies = computed(() => contextStore.companies)
const activeCompanyId = computed(() => contextStore.activeCompany?.id ?? null)

const initials = computed(() => {
  const name = authStore.user?.name ?? ''
  return name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
})

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
  <div class="app-root">

    <!-- ── SIDEBAR DESKTOP ── -->
    <aside class="sidebar">
      <div class="sb-top">
        <div class="sb-logo">
          <div class="sb-logo-mark">SA</div>
          <div>
            <div class="sb-logo-name">Smart Audit</div>
            <div class="sb-logo-sub">Plataforma operacional</div>
          </div>
        </div>
      </div>

      <nav class="sb-nav">
        <div class="sb-sec">Principal</div>
        <RouterLink to="/"            class="nav-btn" exact-active-class="active">Resumo</RouterLink>
        <RouterLink to="/forms"       class="nav-btn" active-class="active">Formulários</RouterLink>
        <RouterLink to="/submissions" class="nav-btn" active-class="active">Inspeções</RouterLink>
        <RouterLink to="/teams"       class="nav-btn" active-class="active">Equipes</RouterLink>
        <RouterLink to="/users"       class="nav-btn" active-class="active">Usuários</RouterLink>
      </nav>

      <div class="sb-bottom">
        <div class="sb-co">
          <div class="sb-co-lbl">Empresa ativa</div>
          <select
            class="sb-co-select"
            :value="activeCompanyId ?? ''"
            @change="handleCompanyChange"
          >
            <option v-for="company in companies" :key="company.id" :value="company.id">
              {{ company.name }}
            </option>
          </select>
        </div>
        <RouterLink to="/profile" class="sb-user">
          <div class="sb-av">{{ initials }}</div>
          <div class="sb-user-name">{{ authStore.user?.name }}</div>
        </RouterLink>
        <button class="nav-btn" type="button" @click="logout">Sair</button>
      </div>
    </aside>

    <!-- ── MOBILE HEADER ── -->
    <header class="mob-hdr">
      <div class="mob-hdr-brand">
        <div class="mob-hdr-mark">SA</div>
        <div class="mob-hdr-name">Smart Audit</div>
      </div>
      <RouterLink to="/profile" class="mob-av">{{ initials }}</RouterLink>
    </header>

    <!-- ── MAIN CONTENT ── -->
    <div class="app-body">
      <slot />
    </div>

    <!-- ── BOTTOM NAV MOBILE ── -->
    <nav class="bot-nav">
      <RouterLink to="/"            class="bn-item" exact-active-class="active">Resumo</RouterLink>
      <RouterLink to="/forms"       class="bn-item" active-class="active">Formulários</RouterLink>
      <RouterLink to="/submissions" class="bn-item" active-class="active">Inspeções</RouterLink>
      <RouterLink to="/teams"       class="bn-item" active-class="active">Equipes</RouterLink>
      <RouterLink to="/users"       class="bn-item" active-class="active">Usuários</RouterLink>
    </nav>

  </div>
</template>
