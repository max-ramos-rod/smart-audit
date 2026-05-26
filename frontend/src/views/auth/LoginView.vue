<script setup lang="ts">
import { reactive } from 'vue'
import { useRouter } from 'vue-router'

import BaseButton from '@/components/ui/BaseButton.vue'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'

const router = useRouter()
const authStore = useAuthStore()
const contextStore = useContextStore()

const form = reactive({
  email: 'admin@smartaudit.local',
  password: 'admin123456',
})

async function submit() {
  await authStore.login(form)
  await contextStore.bootstrap()
  router.push({ name: 'home' })
}
</script>

<template>
  <section class="grid min-h-screen place-items-center p-4 sm:p-6">
    <div class="surface-panel w-full max-w-xl p-6 sm:p-8">
      <p class="eyebrow">Smart Audit</p>
      <h1 class="mt-3 max-w-lg text-3xl font-semibold tracking-tight text-sa-text sm:text-4xl">
        Entrar para operar com contexto e rastreabilidade
      </h1>
      <p class="muted-copy mt-4 max-w-xl text-base">
        O frontend ja nasce conectado aos contratos reais do backend: autenticacao, empresa ativa e modulos de operacao.
      </p>

      <form class="mt-6 grid gap-4" @submit.prevent="submit">
        <label class="grid gap-2">
          <span>Email</span>
          <input v-model="form.email" type="email" autocomplete="username" required />
        </label>

        <label class="grid gap-2">
          <span>Senha</span>
          <input v-model="form.password" type="password" autocomplete="current-password" required />
        </label>

        <p v-if="authStore.error" class="text-sm font-medium text-sa-danger">{{ authStore.error }}</p>

        <BaseButton type="submit" :disabled="authStore.isLoading" :full-width="true">
          {{ authStore.isLoading ? 'Entrando...' : 'Entrar' }}
        </BaseButton>
      </form>
    </div>
  </section>
</template>
