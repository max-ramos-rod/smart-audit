<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'

const router = useRouter()
const authStore = useAuthStore()
const contextStore = useContextStore()

const form = reactive({
  email: '',
  password: '',
})

async function submit() {
  await authStore.login(form)
  await contextStore.bootstrap()
  router.push({ name: 'home' })
}
</script>

<template>
  <div class="login-root">

    <!-- ── PAINEL DE MARCA (desktop only) ── -->
    <div class="login-brand">
      <div class="lb-inner">
        <div class="lb-mark">SA</div>
        <h2 class="lb-h">
          Auditorias.<br />
          Rastreabilidade.<br />
          Controle operacional.
        </h2>
        <p class="lb-p">
          Plataforma de gestão de checklists, inspeções e evidências para operações críticas.
        </p>
      </div>
      <div class="lb-pills">
        <div class="lb-pill">Checklists versionados por empresa</div>
        <div class="lb-pill">Rastreabilidade completa por inspeção</div>
        <div class="lb-pill">Evidências fotográficas integradas</div>
        <div class="lb-pill">Score operacional automatizado</div>
      </div>
    </div>

    <!-- ── FORMULÁRIO ── -->
    <div class="lfa">
      <div class="lfb">

        <!-- Logo mobile -->
        <div class="lf-mob-logo">
          <div class="lf-mob-mark">SA</div>
          <div class="lf-mob-name">Smart Audit</div>
        </div>

        <h1 class="lf-h">Entrar na plataforma</h1>
        <p class="lf-sub">Acesse com suas credenciais corporativas</p>

        <form class="lf-form" @submit.prevent="submit">
          <label class="grid gap-2">
            <span>E-mail</span>
            <input
              v-model="form.email"
              type="email"
              autocomplete="username"
              required
              placeholder="seu@email.com"
            />
          </label>

          <label class="grid gap-2">
            <span>Senha</span>
            <input
              v-model="form.password"
              type="password"
              autocomplete="current-password"
              required
              placeholder="••••••••"
            />
          </label>

          <p v-if="authStore.error" class="lf-err">{{ authStore.error }}</p>

          <button
            type="submit"
            class="lf-btn"
            :disabled="authStore.isLoading"
          >
            {{ authStore.isLoading ? 'Autenticando...' : 'Entrar' }}
          </button>

          <RouterLink to="/forgot-password" class="lf-forgot">
            Esqueceu sua senha?
          </RouterLink>
        </form>

        <div style="margin-top: 24px; font-size: 11px; color: var(--sa-muted); text-align: center;">
          Smart Audit · Plataforma Operacional
        </div>
      </div>
    </div>

  </div>
</template>
