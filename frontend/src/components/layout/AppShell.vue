<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import SvgIcon from '@/components/ui/SvgIcon.vue'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'

const authStore = useAuthStore()
const contextStore = useContextStore()
const router = useRouter()

const initials = computed(() => {
  const name = authStore.user?.name ?? ''
  return name
    .split(' ')
    .map((part: string) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
})

function logout() {
  authStore.logout()
  contextStore.reset()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="app-root">
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
        <RouterLink to="/" class="nav-btn" exact-active-class="active"><SvgIcon name="home" />Resumo</RouterLink>
        <RouterLink to="/forms" class="nav-btn" active-class="active"><SvgIcon name="forms" />Formulários</RouterLink>
        <RouterLink to="/submissions" class="nav-btn" active-class="active"><SvgIcon name="submissions" />Inspeções</RouterLink>
        <RouterLink to="/teams" class="nav-btn" active-class="active"><SvgIcon name="teams" />Equipes</RouterLink>
        <RouterLink to="/users" class="nav-btn" active-class="active"><SvgIcon name="users" />Usuários</RouterLink>

        <div class="sb-sec" style="margin-top: 8px">Ferramentas</div>
        <RouterLink to="/search" class="nav-btn" active-class="active"><SvgIcon name="search" />Buscar</RouterLink>
        <RouterLink to="/notifications" class="nav-btn" active-class="active"><SvgIcon name="bell" />Notificações</RouterLink>
        <RouterLink to="/company-settings" class="nav-btn" active-class="active"><SvgIcon name="settings" />Config. empresa</RouterLink>
      </nav>

      <div class="sb-bottom">
        <RouterLink
          to="/company-settings"
          class="sb-co"
          style="text-decoration: none; display: block; border-radius: var(--r3, 12px); padding: 6px 10px 4px; transition: background 0.15s; cursor: pointer;"
        >
          <div class="sb-co-lbl">Empresa ativa · Configurações</div>
          <div class="sb-co-name">{{ contextStore.activeCompany?.name ?? 'Sem empresa ativa' }}</div>
        </RouterLink>
        <RouterLink to="/select-company" class="nav-btn">
          <SvgIcon name="switch" />Trocar empresa
        </RouterLink>
        <RouterLink to="/profile" class="sb-user">
          <div class="sb-av">{{ initials }}</div>
          <div class="sb-user-name">{{ authStore.user?.name ?? 'Minha conta' }}</div>
        </RouterLink>
        <button class="nav-btn" type="button" @click="logout"><SvgIcon name="logout" />Sair</button>
      </div>
    </aside>

    <header class="mob-hdr">
      <div class="mob-hdr-brand">
        <div class="mob-hdr-mark">SA</div>
        <div class="mob-hdr-name">Smart Audit</div>
      </div>
      <RouterLink to="/profile" class="mob-av">{{ initials }}</RouterLink>
    </header>

    <div class="app-body">
      <slot />
    </div>

    <nav class="bot-nav">
      <RouterLink to="/" class="bn-item" exact-active-class="active"><SvgIcon name="home" :size="21" />Resumo</RouterLink>
      <RouterLink to="/forms" class="bn-item" active-class="active"><SvgIcon name="forms" :size="21" />Formulários</RouterLink>
      <RouterLink to="/submissions" class="bn-item" active-class="active"><SvgIcon name="submissions" :size="21" />Inspeções</RouterLink>
      <RouterLink to="/teams" class="bn-item" active-class="active"><SvgIcon name="teams" :size="21" />Equipes</RouterLink>
      <RouterLink to="/users" class="bn-item" active-class="active"><SvgIcon name="users" :size="21" />Usuários</RouterLink>
    </nav>
  </div>
</template>
