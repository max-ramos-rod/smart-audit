<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import BrandLogo from '@/components/ui/BrandLogo.vue'
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
          <BrandLogo variant="dark-mode" :height="34" />
        </div>
      </div>

      <nav class="sb-nav">
        <!-- ── Visão Geral ── -->
        <div class="sb-sec">Visão Geral</div>
        <RouterLink to="/" class="nav-btn" exact-active-class="active">
          <SvgIcon name="home" />Resumo
        </RouterLink>

        <!-- ── Operacional (uso diário) ── -->
        <div class="sb-sec">Operacional</div>
        <RouterLink to="/clients" class="nav-btn" active-class="active">
          <SvgIcon name="clients" />Clientes
        </RouterLink>
        <RouterLink to="/submissions" class="nav-btn" active-class="active">
          <SvgIcon name="submissions" />Inspeções
        </RouterLink>

        <!-- ── Configuração (setup, uso esporádico) ── -->
        <div class="sb-sec">Configuração</div>
        <RouterLink to="/forms" class="nav-btn" active-class="active">
          <SvgIcon name="forms" />Formulários
        </RouterLink>
        <RouterLink to="/asset-types" class="nav-btn" active-class="active">
          <SvgIcon name="assetTypes" />Tipos de ativo
        </RouterLink>
        <RouterLink to="/assets" class="nav-btn" active-class="active">
          <SvgIcon name="assets" />Ativos
        </RouterLink>

        <!-- ── Administração (raramente usada em campo) ── -->
        <div class="sb-sec">Administração</div>
        <RouterLink to="/users" class="nav-btn" active-class="active">
          <SvgIcon name="users" />Usuários
        </RouterLink>
        <RouterLink to="/teams" class="nav-btn" active-class="active">
          <SvgIcon name="teams" />Equipes
        </RouterLink>
        <RouterLink to="/company-settings" class="nav-btn" active-class="active">
          <SvgIcon name="settings" />Configurações
        </RouterLink>

        <!-- ── Ferramentas ── -->
        <div class="sb-sec" style="margin-top: 8px">Ferramentas</div>
        <RouterLink to="/search" class="nav-btn" active-class="active">
          <SvgIcon name="search" />Buscar
        </RouterLink>
        <RouterLink to="/notifications" class="nav-btn" active-class="active">
          <SvgIcon name="bell" />Notificações
        </RouterLink>
        <RouterLink to="/audit" class="nav-btn" active-class="active">
          <SvgIcon name="search" />Auditoria
        </RouterLink>
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
        <button class="nav-btn" type="button" @click="logout">
          <SvgIcon name="logout" />Sair
        </button>
      </div>
    </aside>

    <header class="mob-hdr">
      <div class="mob-hdr-brand">
        <BrandLogo variant="horizontal" :height="24" />
      </div>
      <RouterLink to="/profile" class="mob-av">{{ initials }}</RouterLink>
    </header>

    <div class="app-body">
      <slot />
    </div>

    <!--
      Bottom nav mobile — Sprint 1
      Antes: Resumo | Formulários | Inspeções | Equipes | Usuários
      Depois: Início | Clientes | [+ Nova] | Inspeções | Perfil
    -->
    <nav class="bot-nav">
      <RouterLink to="/" class="bn-item" exact-active-class="active">
        <SvgIcon name="home" :size="21" />Início
      </RouterLink>
      <RouterLink to="/clients" class="bn-item" active-class="active">
        <SvgIcon name="clients" :size="21" />Clientes
      </RouterLink>
      <!-- FAB central: atalho de Nova Inspeção -->
      <RouterLink to="/submissions" class="bn-item bn-fab-wrap" active-class="">
        <span class="bn-fab" aria-label="Nova inspeção">
          <SvgIcon name="plus" :size="22" />
        </span>
        <span class="bn-fab-lbl">Nova</span>
      </RouterLink>
      <RouterLink to="/submissions" class="bn-item" active-class="active">
        <SvgIcon name="submissions" :size="21" />Inspeções
      </RouterLink>
      <RouterLink to="/profile" class="bn-item" active-class="active">
        <SvgIcon name="profile" :size="21" />Perfil
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
/* ── FAB central no bottom nav ──────────────────────────── */
.bn-fab-wrap {
  /* Cancela o estilo padrão de .bn-item para o wrapper do FAB */
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 0;
  /* Empurra o FAB para cima do nav */
  margin-top: -14px;
}

.bn-fab {
  width: 48px;
  height: 48px;
  background: var(--sa-primary, #2563eb);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 14px rgba(37, 99, 235, 0.45);
  transition: background 0.15s, transform 0.15s;
  flex-shrink: 0;
}

.bn-fab-wrap:active .bn-fab,
.bn-fab-wrap:hover .bn-fab {
  background: #1d4ed8;
  transform: scale(0.96);
}

.bn-fab-lbl {
  font-size: 10px;
  font-weight: 600;
  color: var(--sa-primary, #2563eb);
  margin-top: 2px;
}
</style>
