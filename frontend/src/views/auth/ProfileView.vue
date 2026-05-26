<script setup lang="ts">
import { ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'

const authStore = useAuthStore()
const contextStore = useContextStore()

const name = ref(authStore.user?.name ?? '')
const password = ref('')
const confirmPassword = ref('')
const localError = ref<string | null>(null)
const successMessage = ref<string | null>(null)

async function handleSubmit() {
  localError.value = null
  successMessage.value = null

  if (password.value && password.value !== confirmPassword.value) {
    localError.value = 'As senhas não coincidem.'
    return
  }

  const payload: { name?: string; password?: string } = {}
  if (name.value.trim() && name.value.trim() !== authStore.user?.name) {
    payload.name = name.value.trim()
  }
  if (password.value) {
    payload.password = password.value
  }

  if (!Object.keys(payload).length) {
    localError.value = 'Nenhuma alteração detectada.'
    return
  }

  try {
    const updated = await contextStore.updateProfile(payload)
    authStore.setUser({ id: updated.id, name: updated.name, email: updated.email })
    name.value = updated.name
    password.value = ''
    confirmPassword.value = ''
    successMessage.value = 'Perfil atualizado com sucesso.'
  } catch {
    // error already in contextStore.updateProfileError
  }
}
</script>

<template>
  <AppShell>
    <section class="px-1">
      <p class="eyebrow">Conta</p>
      <h2 class="mt-2 text-2xl font-semibold tracking-tight text-sa-text">Meu perfil</h2>
      <p class="mt-2 text-sm text-sa-muted">Atualize seu nome e senha de acesso.</p>
    </section>

    <div class="surface-panel max-w-md p-6">
      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div class="grid gap-1.5">
          <label class="text-sm font-medium text-sa-text" for="profile-email">E-mail</label>
          <input
            id="profile-email"
            type="email"
            :value="authStore.user?.email"
            disabled
            class="opacity-60"
          />
        </div>

        <div class="grid gap-1.5">
          <label class="text-sm font-medium text-sa-text" for="profile-name">Nome</label>
          <input
            id="profile-name"
            v-model="name"
            type="text"
            placeholder="Seu nome"
            maxlength="100"
          />
        </div>

        <div class="grid gap-1.5">
          <label class="text-sm font-medium text-sa-text" for="profile-password">
            Nova senha
            <span class="font-normal text-sa-muted">(deixe em branco para não alterar)</span>
          </label>
          <input
            id="profile-password"
            v-model="password"
            type="password"
            placeholder="Mínimo 8 caracteres"
            autocomplete="new-password"
          />
        </div>

        <div class="grid gap-1.5">
          <label class="text-sm font-medium text-sa-text" for="profile-confirm">
            Confirmar nova senha
          </label>
          <input
            id="profile-confirm"
            v-model="confirmPassword"
            type="password"
            placeholder="Repita a nova senha"
            autocomplete="new-password"
          />
        </div>

        <p v-if="localError" class="text-sm text-red-600">{{ localError }}</p>
        <p v-else-if="contextStore.updateProfileError" class="text-sm text-red-600">
          {{ contextStore.updateProfileError }}
        </p>
        <p v-if="successMessage" class="text-sm text-green-700">{{ successMessage }}</p>

        <BaseButton type="submit" :disabled="contextStore.isUpdatingProfile">
          {{ contextStore.isUpdatingProfile ? 'Salvando...' : 'Salvar alterações' }}
        </BaseButton>
      </form>
    </div>
  </AppShell>
</template>
