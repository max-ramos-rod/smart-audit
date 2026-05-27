<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { useUsersStore } from '@/stores/users/users.store'
import type { UserCreatePayload, UserListItem, UserUpdatePayload } from '@/types/users'

const usersStore = useUsersStore()
const isEditing = ref(false)
const formError = ref<string | null>(null)
const savedOnce = ref(false)
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
    return isEditing.value ? 'Salvando...' : 'Criando...'
  }
  return isEditing.value ? 'Salvar alterações' : 'Criar usuário'
})

onMounted(() => {
  usersStore.load()
})

function resetForm() {
  form.id = ''
  form.name = ''
  form.email = ''
  form.password = ''
  form.role = 'VIEWER'
  form.is_active = true
  isEditing.value = false
  formError.value = null
  usersStore.clearSelectedUser()
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

      <p v-if="usersStore.error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ usersStore.error }}
      </p>

      <div class="users-layout">

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
            <div class="field">
              <label class="flabel">{{ isEditing ? 'Nova senha (opcional)' : 'Senha inicial' }}</label>
              <input
                v-model="form.password"
                type="password"
                minlength="8"
                maxlength="128"
                :required="!isEditing"
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
              <div class="field">
                <label class="flabel">Status</label>
                <select v-model="form.is_active">
                  <option :value="true">Ativo</option>
                  <option :value="false">Inativo</option>
                </select>
              </div>
            </div>

            <p v-if="savedOnce" style="font-size:13px;font-weight:600;color:var(--sa-ok);padding:6px 0;">
              ✓ Usuário salvo com sucesso.
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
                  <button class="inline-action" type="button" @click="editUser(user)">Editar</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

      </div>
    </div>
  </AppShell>
</template>
