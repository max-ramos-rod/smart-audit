<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { useUsersStore } from '@/stores/users/users.store'
import type { UserCreatePayload, UserListItem, UserUpdatePayload } from '@/types/users'

const usersStore = useUsersStore()
const isEditing = ref(false)
const formError = ref<string | null>(null)
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

    resetForm()
  } catch (err: any) {
    formError.value = extractProblemMessage(err, 'Não foi possível salvar o usuário.')
  }
}
</script>

<template>
  <AppShell>
    <section class="flex flex-wrap items-center justify-between gap-3 px-1">
      <div>
        <p class="eyebrow">Administração</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-sa-text">Usuários da empresa</h2>
      </div>
      <BaseButton type="button" @click="resetForm">Novo usuário</BaseButton>
    </section>

    <p v-if="usersStore.error" class="text-sm font-medium text-sa-danger">{{ usersStore.error }}</p>

    <section class="grid gap-4 xl:grid-cols-[minmax(320px,400px)_minmax(0,1fr)]">
      <article class="surface-panel p-5 sm:p-6">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="eyebrow">Operação</p>
            <h3 class="mt-2 text-xl font-semibold text-sa-text">{{ title }}</h3>
          </div>
          <span class="status-chip">{{ isEditing ? 'Edição' : 'Criação' }}</span>
        </div>

        <form class="mt-5 grid gap-4" @submit.prevent="submit">
          <label class="grid gap-2">
            <span>Nome</span>
            <input v-model="form.name" type="text" minlength="2" maxlength="150" required />
          </label>

          <label class="grid gap-2">
            <span>Email</span>
            <input
              v-model="form.email"
              type="email"
              minlength="5"
              maxlength="255"
              :disabled="isEditing"
              required
            />
          </label>

          <label class="grid gap-2">
            <span>{{ isEditing ? 'Nova senha' : 'Senha inicial' }}</span>
            <input
              v-model="form.password"
              type="password"
              minlength="8"
              maxlength="128"
              :required="!isEditing"
              :placeholder="isEditing ? 'Preencha apenas se quiser trocar' : ''"
            />
          </label>

          <div class="grid gap-4 sm:grid-cols-2">
            <label class="grid gap-2">
              <span>Papel</span>
              <select v-model="form.role">
                <option value="OWNER">OWNER</option>
                <option value="ADMIN">ADMIN</option>
                <option value="MANAGER">MANAGER</option>
                <option value="INSPECTOR">INSPECTOR</option>
                <option value="VIEWER">VIEWER</option>
              </select>
            </label>

            <label class="grid gap-2">
              <span>Status</span>
              <select v-model="form.is_active">
                <option :value="true">Ativo</option>
                <option :value="false">Inativo</option>
              </select>
            </label>
          </div>

          <p v-if="formError" class="text-sm font-medium text-sa-danger">{{ formError }}</p>

          <div class="flex flex-col gap-3">
            <BaseButton type="submit" :full-width="true">
              {{ submitLabel }}
            </BaseButton>
            <BaseButton
              v-if="isEditing"
              type="button"
              variant="ghost"
              :full-width="true"
              @click="resetForm"
            >
              Cancelar edição
            </BaseButton>
          </div>
        </form>
      </article>

      <section class="grid gap-4">
        <div class="grid gap-3 lg:hidden">
          <article v-for="user in usersStore.items" :key="user.id" class="surface-panel p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="eyebrow">{{ user.role }}</p>
                <h3 class="mt-2 text-lg font-semibold text-sa-text">{{ user.name }}</h3>
              </div>
              <span class="status-chip" :class="{ 'status-chip--inactive': !user.is_active }">
                {{ user.is_active ? 'Ativo' : 'Inativo' }}
              </span>
            </div>

            <p class="mt-3 text-sm text-sa-muted">{{ user.email }}</p>

            <div class="mt-4">
              <BaseButton type="button" variant="ghost" :full-width="true" @click="editUser(user)">
                Editar usuário
              </BaseButton>
            </div>
          </article>
        </div>

        <section class="surface-panel hidden overflow-auto p-2 lg:block">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Email</th>
                <th>Papel</th>
                <th>Status</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in usersStore.items" :key="user.id">
                <td>{{ user.name }}</td>
                <td>{{ user.email }}</td>
                <td>{{ user.role }}</td>
                <td>{{ user.is_active ? 'Ativo' : 'Inativo' }}</td>
                <td>
                  <button class="inline-action" type="button" @click="editUser(user)">Editar</button>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
      </section>
    </section>
  </AppShell>
</template>
