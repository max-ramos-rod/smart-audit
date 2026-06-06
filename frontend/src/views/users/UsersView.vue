<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { useContextStore } from '@/stores/context/context.store'
import { useUsersStore } from '@/stores/users/users.store'
import type {
  UserCreatePayload,
  UserInvitePayload,
  UserListItem,
  UserRevokedItem,
  UserUpdatePayload,
} from '@/types/users'

const usersStore = useUsersStore()
const contextStore = useContextStore()
const tab = ref<'active' | 'revoked'>('active')
const isEditing = ref(false)
// Modo de criação: 'invite' envia link por email; 'password' define senha inicial.
const createMode = ref<'invite' | 'password'>('invite')
const revokeError = ref<string | null>(null)
const reactivateError = ref<string | null>(null)
const formError = ref<string | null>(null)
const savedOnce = ref(false)
const invitedOnce = ref(false)
const form = reactive({
  id: '',
  name: '',
  email: '',
  password: '',
  role: 'VIEWER',
  is_active: true,
})

const title = computed(() => (isEditing.value ? 'Editar usuário' : 'Novo usuário'))
const submitLabel = computed(() => {
  if (usersStore.isSaving) {
    if (isEditing.value) return 'Salvando...'
    return createMode.value === 'invite' ? 'Enviando convite...' : 'Criando...'
  }
  if (isEditing.value) return 'Salvar alterações'
  return createMode.value === 'invite' ? 'Enviar convite' : 'Criar usuário'
})

onMounted(() => {
  usersStore.load()
})

const currentUserId = computed(() => contextStore.context?.user?.id)

function resetForm() {
  form.id = ''
  form.name = ''
  form.email = ''
  form.password = ''
  form.role = 'VIEWER'
  form.is_active = true
  isEditing.value = false
  formError.value = null
  revokeError.value = null
  usersStore.clearSelectedUser()
}

async function switchTab(t: 'active' | 'revoked') {
  tab.value = t
  if (t === 'revoked' && usersStore.revokedItems.length === 0) {
    await usersStore.loadRevoked()
  }
}

async function confirmReactivate(user: UserRevokedItem) {
  if (!confirm(`Reativar o acesso de "${user.name}" nesta empresa?`)) return
  reactivateError.value = null
  try {
    await usersStore.reactivate(user.id)
  } catch (err: any) {
    reactivateError.value = extractProblemMessage(err, 'Não foi possível reativar o acesso.')
  }
}

async function confirmRevoke(user: UserListItem) {
  if (!confirm(`Revogar o acesso de "${user.name}" a esta empresa? O usuário não conseguirá mais fazer login nesta empresa.`)) return
  revokeError.value = null
  try {
    await usersStore.revoke(user.id)
    if (isEditing.value && form.id === user.id) resetForm()
  } catch (err: any) {
    revokeError.value = extractProblemMessage(err, 'Não foi possível revogar o acesso.')
  }
}

function fillFormFromUser(user: UserListItem & { company_id?: string }) {
  form.id = user.id
  form.name = user.name
  form.email = user.email
  form.password = ''
  form.role = user.role
  form.is_active = user.is_active
  isEditing.value = true
  formError.value = null
}

async function editUser(user: UserListItem) {
  const detail = await usersStore.loadUser(user.id)
  fillFormFromUser(detail)
}

async function submit() {
  formError.value = null

  try {
    if (isEditing.value) {
      const payload: UserUpdatePayload = {
        name: form.name,
        role: form.role,
        is_active: form.is_active,
      }

      if (form.password) {
        payload.password = form.password
      }

      await usersStore.update(form.id, payload)
    } else if (createMode.value === 'invite') {
      const payload: UserInvitePayload = {
        name: form.name,
        email: form.email,
        role: form.role,
      }
      await usersStore.invite(payload)
      invitedOnce.value = true
      setTimeout(() => { invitedOnce.value = false }, 4000)
      resetForm()
      return
    } else {
      const payload: UserCreatePayload = {
        name: form.name,
        email: form.email,
        password: form.password,
        role: form.role,
        is_active: form.is_active,
      }
      await usersStore.create(payload)
    }

    savedOnce.value = true
    setTimeout(() => { savedOnce.value = false }, 3000)
    resetForm()
  } catch (err: any) {
    formError.value = extractProblemMessage(err, 'Não foi possível salvar o usuário.')
  }
}
</script>

<template>
  <AppShell>
    <div class="page">

      <div class="phdr">
        <div>
          <p class="eyebrow">Administração</p>
          <h2 class="page-h1">Usuários da empresa</h2>
          <p class="page-desc">Gerencie acessos e papéis dos colaboradores.</p>
        </div>
        <button type="button" class="btn-secondary btn-sm" @click="resetForm">+ Novo usuário</button>
      </div>

      <div class="filter-tabs" style="margin-bottom: 16px;">
        <button class="filter-tab" :class="{ active: tab === 'active' }" type="button" @click="switchTab('active')">
          Ativos
        </button>
        <button class="filter-tab" :class="{ active: tab === 'revoked' }" type="button" @click="switchTab('revoked')">
          Revogados
        </button>
      </div>

      <p v-if="usersStore.error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ usersStore.error }}
      </p>
      <p v-if="revokeError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ revokeError }}
      </p>
      <p v-if="reactivateError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ reactivateError }}
      </p>

      <!-- Aba Ativos -->
      <div v-if="tab === 'active'" class="users-layout">

        <!-- Formulário -->
        <div class="card card-p" style="align-self:flex-start;position:sticky;top:20px;">
          <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:16px;">
            <div>
              <p class="eyebrow">{{ isEditing ? 'Edição' : 'Criação' }}</p>
              <h3 style="font-size:16px;font-weight:700;color:var(--sa-text);margin-top:3px;">{{ title }}</h3>
            </div>
            <span class="status-chip" :class="{ 'status-chip--warn': isEditing }">
              {{ isEditing ? 'Editando' : 'Novo' }}
            </span>
          </div>

          <!-- Modo de criação: convite por email vs senha inicial (só na criação) -->
          <div v-if="!isEditing" class="filter-tabs" style="margin-bottom:14px;">
            <button
              type="button"
              class="filter-tab"
              :class="{ active: createMode === 'invite' }"
              @click="createMode = 'invite'"
            >Convidar por e-mail</button>
            <button
              type="button"
              class="filter-tab"
              :class="{ active: createMode === 'password' }"
              @click="createMode = 'password'"
            >Definir senha</button>
          </div>

          <form style="display:grid;gap:12px;" @submit.prevent="submit">
            <div class="field">
              <label class="flabel">Nome completo</label>
              <input v-model="form.name" type="text" minlength="2" maxlength="150" required />
            </div>
            <div class="field">
              <label class="flabel">E-mail</label>
              <input
                v-model="form.email"
                type="email"
                minlength="5"
                maxlength="255"
                :disabled="isEditing"
                required
              />
            </div>
            <div v-if="isEditing || createMode === 'password'" class="field">
              <label class="flabel">{{ isEditing ? 'Nova senha (opcional)' : 'Senha inicial' }}</label>
              <input
                v-model="form.password"
                type="password"
                minlength="8"
                maxlength="128"
                :required="!isEditing && createMode === 'password'"
                :placeholder="isEditing ? 'Deixe em branco para manter' : ''"
              />
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
              <div class="field">
                <label class="flabel">Papel</label>
                <select v-model="form.role">
                  <option value="OWNER">OWNER</option>
                  <option value="ADMIN">ADMIN</option>
                  <option value="MANAGER">MANAGER</option>
                  <option value="INSPECTOR">INSPECTOR</option>
                  <option value="VIEWER">VIEWER</option>
                </select>
              </div>
              <div v-if="isEditing || createMode === 'password'" class="field">
                <label class="flabel">Status</label>
                <select v-model="form.is_active">
                  <option :value="true">Ativo</option>
                  <option :value="false">Inativo</option>
                </select>
              </div>
            </div>

            <p
              v-if="!isEditing && createMode === 'invite'"
              style="font-size:12px;color:var(--sa-muted);line-height:1.5;"
            >
              O usuário receberá um e-mail com um link para definir a própria senha e acessar a plataforma.
            </p>

            <p v-if="savedOnce" style="font-size:13px;font-weight:600;color:var(--sa-ok);padding:6px 0;">
              ✓ Usuário salvo com sucesso.
            </p>
            <p v-if="invitedOnce" style="font-size:13px;font-weight:600;color:var(--sa-ok);padding:6px 0;">
              ✓ Convite enviado por e-mail.
            </p>
            <p v-if="formError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ formError }}</p>

            <div style="display:flex;flex-direction:column;gap:8px;">
              <button type="submit" class="btn-primary btn-full">{{ submitLabel }}</button>
              <button
                v-if="isEditing"
                type="button"
                class="btn-secondary btn-full"
                @click="resetForm"
              >
                Cancelar edição
              </button>
            </div>
          </form>
        </div>

        <!-- Tabela -->
        <div class="card" style="overflow-x:auto;">
          <table class="tbl">
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Papel</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in usersStore.items" :key="user.id">
                <td class="tbl-name">{{ user.name }}</td>
                <td class="tbl-muted" style="font-family:'DM Mono',monospace;font-size:12px;">{{ user.email }}</td>
                <td>
                  <span class="role-badge" :class="'role-' + user.role.toLowerCase()">
                    {{ user.role }}
                  </span>
                </td>
                <td>
                  <span class="status-chip" :class="{ 'status-chip--inactive': !user.is_active }">
                    {{ user.is_active ? 'Ativo' : 'Inativo' }}
                  </span>
                </td>
                <td>
                  <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <button class="inline-action" type="button" @click="editUser(user)">Editar</button>
                    <button
                      v-if="user.id !== currentUserId"
                      class="inline-action"
                      type="button"
                      style="color:var(--sa-danger);"
                      :disabled="usersStore.isSaving"
                      @click="confirmRevoke(user)"
                    >Revogar</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>

      <!-- Aba Revogados -->
      <div v-else-if="tab === 'revoked'" class="card" style="overflow-x:auto;">
        <p v-if="usersStore.isLoading" style="font-size:13px;color:var(--sa-muted);padding:16px;">Carregando...</p>
        <template v-else>
          <p v-if="usersStore.revokedItems.length === 0" style="font-size:13px;color:var(--sa-muted);padding:16px;">
            Nenhum usuário revogado nesta empresa.
          </p>
          <table v-else class="tbl">
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Papel</th>
                <th>Revogado em</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in usersStore.revokedItems" :key="user.id">
                <td class="tbl-name">{{ user.name }}</td>
                <td class="tbl-muted" style="font-family:'DM Mono',monospace;font-size:12px;">{{ user.email }}</td>
                <td>
                  <span class="role-badge" :class="'role-' + user.role.toLowerCase()">{{ user.role }}</span>
                </td>
                <td class="tbl-muted" style="font-size:12px;">
                  {{ new Date(user.revoked_at).toLocaleDateString('pt-BR') }}
                </td>
                <td>
                  <button
                    class="inline-action"
                    type="button"
                    style="color:var(--sa-ok);"
                    :disabled="usersStore.isSaving"
                    @click="confirmReactivate(user)"
                  >Reativar</button>
                </td>
              </tr>
            </tbody>
          </table>
        </template>
      </div>
    </div>
  </AppShell>
</template>
