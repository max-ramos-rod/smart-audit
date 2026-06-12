<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { useClientsStore } from '@/stores/clients/clients.store'
import type { Client } from '@/types/clients'

const clientsStore = useClientsStore()
const tab = ref<'active' | 'inactive'>('active')
const isEditing = ref(false)
const formError = ref<string | null>(null)
const actionError = ref<string | null>(null)
const savedOnce = ref(false)
const form = reactive({ id: '', name: '' })

const title = computed(() => (isEditing.value ? 'Editar cliente' : 'Novo cliente'))
const submitLabel = computed(() => {
  if (clientsStore.isSaving) return isEditing.value ? 'Salvando...' : 'Criando...'
  return isEditing.value ? 'Salvar alterações' : 'Criar cliente'
})

onMounted(() => clientsStore.load(1, 20, true))

function resetForm() {
  form.id = ''
  form.name = ''
  isEditing.value = false
  formError.value = null
}

async function switchTab(t: 'active' | 'inactive') {
  tab.value = t
  resetForm()
  await clientsStore.load(1, 20, t === 'active')
}

function editClient(c: Client) {
  form.id = c.id
  form.name = c.name
  isEditing.value = true
  formError.value = null
}

async function submit() {
  formError.value = null
  try {
    if (isEditing.value) {
      await clientsStore.update(form.id, { name: form.name })
    } else {
      await clientsStore.create({ name: form.name })
    }
    savedOnce.value = true
    setTimeout(() => { savedOnce.value = false }, 3000)
    resetForm()
    await clientsStore.load(1, 20, tab.value === 'active')
  } catch (err) {
    formError.value = extractProblemMessage(err, 'Não foi possível salvar o cliente.')
  }
}

async function confirmDeactivate(c: Client) {
  if (!confirm(`Desativar o cliente "${c.name}"? Ele sai da listagem ativa; o histórico permanece.`)) return
  actionError.value = null
  try {
    await clientsStore.deactivate(c.id)
    if (isEditing.value && form.id === c.id) resetForm()
  } catch (err) {
    actionError.value = extractProblemMessage(err, 'Não foi possível desativar o cliente.')
  }
}

async function reactivate(c: Client) {
  actionError.value = null
  try {
    await clientsStore.update(c.id, { is_active: true })
    await clientsStore.load(1, 20, tab.value === 'active')
  } catch (err) {
    actionError.value = extractProblemMessage(err, 'Não foi possível reativar o cliente.')
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="phdr">
        <div>
          <p class="eyebrow">Cadastros</p>
          <h2 class="page-h1">Clientes</h2>
          <p class="page-desc">Empresas atendidas cujos ativos são inspecionados.</p>
        </div>
        <button type="button" class="btn-secondary btn-sm" @click="resetForm">+ Novo cliente</button>
      </div>

      <div class="filter-tabs" style="margin-bottom: 16px;">
        <button class="filter-tab" :class="{ active: tab === 'active' }" type="button" @click="switchTab('active')">
          Ativos
        </button>
        <button class="filter-tab" :class="{ active: tab === 'inactive' }" type="button" @click="switchTab('inactive')">
          Inativos
        </button>
      </div>

      <p v-if="clientsStore.error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ clientsStore.error }}
      </p>
      <p v-if="actionError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ actionError }}
      </p>

      <div class="users-layout">
        <!-- Formulário (apenas na aba Ativos) -->
        <div v-if="tab === 'active'" class="card card-p" style="align-self:flex-start;position:sticky;top:20px;">
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
            <label class="field">
              <span class="flabel">Nome do cliente</span>
              <input v-model="form.name" type="text" minlength="2" maxlength="150" required />
            </label>

            <p v-if="savedOnce" style="font-size:13px;font-weight:600;color:var(--sa-ok);padding:6px 0;">
              ✓ Cliente salvo com sucesso.
            </p>
            <p v-if="formError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ formError }}</p>

            <div style="display:flex;flex-direction:column;gap:8px;">
              <button type="submit" class="btn-primary btn-full" :disabled="clientsStore.isSaving">{{ submitLabel }}</button>
              <button v-if="isEditing" type="button" class="btn-secondary btn-full" @click="resetForm">
                Cancelar edição
              </button>
            </div>
          </form>
        </div>

        <!-- Tabela -->
        <div class="card" style="overflow-x:auto;">
          <p v-if="clientsStore.isLoading" style="font-size:13px;color:var(--sa-muted);padding:16px;">Carregando...</p>
          <template v-else>
            <p v-if="clientsStore.items.length === 0" style="font-size:13px;color:var(--sa-muted);padding:16px;">
              Nenhum cliente {{ tab === 'active' ? 'ativo' : 'inativo' }} nesta empresa.
            </p>
            <table v-else class="tbl">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in clientsStore.items" :key="c.id">
                  <td class="tbl-name">
                    <RouterLink
                      :to="{ name: 'client-detail', params: { id: c.id } }"
                      style="color: var(--sa-primary); text-decoration: none; font-weight: 600;"
                    >
                      {{ c.name }}
                    </RouterLink>
                  </td>
                  <td>
                    <span class="status-chip" :class="{ 'status-chip--inactive': !c.is_active }">
                      {{ c.is_active ? 'Ativo' : 'Inativo' }}
                    </span>
                  </td>
                  <td>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;">
                      <button v-if="c.is_active" class="inline-action" type="button" @click="editClient(c)">Editar</button>
                      <button
                        v-if="c.is_active"
                        class="inline-action"
                        type="button"
                        style="color:var(--sa-danger);"
                        :disabled="clientsStore.isSaving"
                        @click="confirmDeactivate(c)"
                      >Desativar</button>
                      <button
                        v-else
                        class="inline-action"
                        type="button"
                        style="color:var(--sa-ok);"
                        :disabled="clientsStore.isSaving"
                        @click="reactivate(c)"
                      >Reativar</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </template>
        </div>
      </div>
    </div>
  </AppShell>
</template>
