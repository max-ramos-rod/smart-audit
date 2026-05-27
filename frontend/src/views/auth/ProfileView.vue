<script setup lang="ts">
import { ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'

const authStore = useAuthStore()
const contextStore = useContextStore()

const tab = ref<'profile' | 'companies' | 'security'>('profile')

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
  if (tab.value === 'profile' && name.value.trim() && name.value.trim() !== authStore.user?.name) {
    payload.name = name.value.trim()
  }
  if (tab.value === 'security' && password.value) {
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
    <div class="page">

      <div class="phdr">
        <div>
          <p class="eyebrow">Conta</p>
          <h2 class="page-h1">Meu perfil</h2>
        </div>
      </div>

      <div class="filter-tabs" style="max-width: 480px;">
        <button
          class="filter-tab"
          :class="{ active: tab === 'profile' }"
          @click="tab = 'profile'; localError = null; successMessage = null"
        >
          Meu perfil
        </button>
        <button
          class="filter-tab"
          :class="{ active: tab === 'companies' }"
          @click="tab = 'companies'; localError = null; successMessage = null"
        >
          Empresas
        </button>
        <button
          class="filter-tab"
          :class="{ active: tab === 'security' }"
          @click="tab = 'security'; localError = null; successMessage = null"
        >
          Segurança
        </button>
      </div>

      <!-- tab: perfil -->
      <div v-if="tab === 'profile'" class="card card-p" style="max-width: 480px;">
        <form class="grid gap-4" @submit.prevent="handleSubmit">
          <label class="grid gap-2">
            <span>E-mail</span>
            <input type="email" :value="authStore.user?.email" disabled />
          </label>

          <label class="grid gap-2">
            <span>Nome</span>
            <input v-model="name" type="text" placeholder="Seu nome" maxlength="100" />
          </label>

          <p v-if="localError" class="text-sm text-sa-danger">{{ localError }}</p>
          <p v-else-if="contextStore.updateProfileError" class="text-sm text-sa-danger">
            {{ contextStore.updateProfileError }}
          </p>
          <p v-if="successMessage" class="text-sm" style="color: var(--sa-ok);">{{ successMessage }}</p>

          <button type="submit" class="btn-primary" :disabled="contextStore.isUpdatingProfile">
            {{ contextStore.isUpdatingProfile ? 'Salvando...' : 'Salvar alterações' }}
          </button>
        </form>
      </div>

      <!-- tab: empresas -->
      <div v-else-if="tab === 'companies'" class="card" style="overflow-x: auto;">
        <table>
          <thead>
            <tr>
              <th>Empresa</th>
              <th>Plano</th>
              <th>Papel</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="company in contextStore.companies" :key="company.id">
              <td class="font-medium">{{ company.name }}</td>
              <td>{{ company.plan }}</td>
              <td>
                <span class="role-badge" :class="'role-' + company.role.toLowerCase()">
                  {{ company.role }}
                </span>
              </td>
              <td>
                <span class="status-chip" :class="{ 'status-chip--inactive': !company.is_active }">
                  {{ company.is_active ? 'Ativa' : 'Inativa' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- tab: segurança -->
      <div v-else-if="tab === 'security'" class="card card-p" style="max-width: 480px;">
        <form class="grid gap-4" @submit.prevent="handleSubmit">
          <label class="grid gap-2">
            <span>Nova senha <span style="font-weight: 400;">(mínimo 8 caracteres)</span></span>
            <input
              v-model="password"
              type="password"
              placeholder="••••••••"
              autocomplete="new-password"
            />
          </label>

          <label class="grid gap-2">
            <span>Confirmar nova senha</span>
            <input
              v-model="confirmPassword"
              type="password"
              placeholder="Repita a nova senha"
              autocomplete="new-password"
            />
          </label>

          <p v-if="localError" class="text-sm text-sa-danger">{{ localError }}</p>
          <p v-else-if="contextStore.updateProfileError" class="text-sm text-sa-danger">
            {{ contextStore.updateProfileError }}
          </p>
          <p v-if="successMessage" class="text-sm" style="color: var(--sa-ok);">{{ successMessage }}</p>

          <button type="submit" class="btn-primary" :disabled="contextStore.isUpdatingProfile">
            {{ contextStore.isUpdatingProfile ? 'Salvando...' : 'Alterar senha' }}
          </button>
        </form>
      </div>

    </div>
  </AppShell>
</template>
