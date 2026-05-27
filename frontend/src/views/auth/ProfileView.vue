<script setup lang="ts">
import { computed, ref } from 'vue'

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

const activeCompanyName = computed(() => contextStore.activeCompany?.name ?? 'Sem empresa ativa')

async function handleSubmit() {
  localError.value = null
  successMessage.value = null

  if (password.value && password.value !== confirmPassword.value) {
    localError.value = 'As senhas nao coincidem.'
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
    // error already handled in store
  }
}

function clearMessages() {
  localError.value = null
  successMessage.value = null
}
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="phdr">
        <div>
          <p class="eyebrow">Conta</p>
          <h2 class="page-h1">Meu perfil</h2>
          <p class="page-desc">Gerencie seus dados básicos, empresas associadas e segurança de acesso.</p>
        </div>
      </div>

      <div class="info-box" style="margin-bottom: 16px;">
        Empresa ativa na sessão: <strong>{{ activeCompanyName }}</strong>.
      </div>

      <div class="filter-tabs" style="max-width: 520px;">
        <button
          class="filter-tab"
          :class="{ active: tab === 'profile' }"
          @click="tab = 'profile'; clearMessages()"
        >
          Meu perfil
        </button>
        <button
          class="filter-tab"
          :class="{ active: tab === 'companies' }"
          @click="tab = 'companies'; clearMessages()"
        >
          Empresas
        </button>
        <button
          class="filter-tab"
          :class="{ active: tab === 'security' }"
          @click="tab = 'security'; clearMessages()"
        >
          Segurança
        </button>
      </div>

      <div v-if="tab === 'profile'" class="card card-p" style="max-width:520px;">
        <form style="display:grid;gap:14px;" @submit.prevent="handleSubmit">
          <label class="field">
            <span class="flabel">E-mail</span>
            <input type="email" :value="authStore.user?.email" disabled />
          </label>
          <label class="field">
            <span class="flabel">Nome</span>
            <input v-model="name" type="text" placeholder="Seu nome" maxlength="100" />
          </label>
          <p v-if="localError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ localError }}</p>
          <p v-else-if="contextStore.updateProfileError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">
            {{ contextStore.updateProfileError }}
          </p>
          <p v-if="successMessage" style="font-size:13px;font-weight:600;color:var(--sa-ok);">{{ successMessage }}</p>
          <div>
            <button type="submit" class="btn-primary" :disabled="contextStore.isUpdatingProfile">
              {{ contextStore.isUpdatingProfile ? 'Salvando...' : 'Salvar alterações' }}
            </button>
          </div>
        </form>
      </div>

      <div v-else-if="tab === 'companies'" class="card card-p">
        <div class="slabel" style="margin-bottom: 12px;">Empresas associadas</div>
        <div style="display: grid; gap: 10px;">
          <div
            v-for="company in contextStore.companies"
            :key="company.id"
            class="card"
            style="padding: 14px 16px;"
          >
            <div style="display: flex; justify-content: space-between; gap: 12px; align-items: flex-start;">
              <div>
                <div style="font-size: 14px; font-weight: 700; color: var(--sa-text);">
                  {{ company.name }}
                </div>
                <div style="font-size: 12px; color: var(--sa-muted); margin-top: 2px;">
                  Perfil: {{ company.role }}
                </div>
              </div>
              <span v-if="company.id === contextStore.activeCompany?.id" class="status-chip">
                Ativa
              </span>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="tab === 'security'" class="card card-p" style="max-width:520px;">
        <form style="display:grid;gap:14px;" @submit.prevent="handleSubmit">
          <div class="info-box">
            A troca de senha usa o endpoint de perfil atual. Este fluxo cobre o básico e ainda não possui histórico, MFA
            ou reset autônomo por e-mail.
          </div>
          <label class="field">
            <span class="flabel">Nova senha</span>
            <input v-model="password" type="password" minlength="8" placeholder="Mínimo de 8 caracteres" />
          </label>
          <label class="field">
            <span class="flabel">Confirmar nova senha</span>
            <input v-model="confirmPassword" type="password" minlength="8" placeholder="Repita a nova senha" />
          </label>
          <p v-if="localError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ localError }}</p>
          <p v-else-if="contextStore.updateProfileError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">
            {{ contextStore.updateProfileError }}
          </p>
          <p v-if="successMessage" style="font-size:13px;font-weight:600;color:var(--sa-ok);">{{ successMessage }}</p>
          <button type="submit" class="btn-primary" :disabled="contextStore.isUpdatingProfile">
            {{ contextStore.isUpdatingProfile ? 'Salvando...' : 'Atualizar senha' }}
          </button>
        </form>
      </div>
    </div>
  </AppShell>
</template>
