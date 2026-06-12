<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import AttributeSchemaBuilder from '@/components/ui/AttributeSchemaBuilder.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { useAssetTypesStore } from '@/stores/asset-types/asset-types.store'
import type { AssetType } from '@/types/asset-types'

const assetTypesStore = useAssetTypesStore()
const tab = ref<'active' | 'inactive'>('active')
const isEditing = ref(false)
const formError = ref<string | null>(null)
const actionError = ref<string | null>(null)
const savedOnce = ref(false)
// `schema` substitui o antigo `schemaText` (JSON manual). O contrato do store
// permanece `attributes_schema: Record<string, unknown> | null` (Sprint 1 — Zero JSON).
const form = reactive<{
  id: string
  name: string
  description: string
  schema: Record<string, unknown> | null
}>({ id: '', name: '', description: '', schema: null })

const title = computed(() => (isEditing.value ? 'Editar tipo' : 'Novo tipo'))
const submitLabel = computed(() => {
  if (assetTypesStore.isSaving) return isEditing.value ? 'Salvando...' : 'Criando...'
  return isEditing.value ? 'Salvar alterações' : 'Criar tipo'
})

onMounted(() => assetTypesStore.load(1, 20, true))

function resetForm() {
  form.id = ''
  form.name = ''
  form.description = ''
  form.schema = null
  isEditing.value = false
  formError.value = null
}

async function switchTab(t: 'active' | 'inactive') {
  tab.value = t
  resetForm()
  await assetTypesStore.load(1, 20, t === 'active')
}

function editType(t: AssetType) {
  form.id = t.id
  form.name = t.name
  form.description = t.description ?? ''
  // O AttributeSchemaBuilder lê o objeto direto (e normaliza formato antigo M1 internamente).
  form.schema = t.attributes_schema ?? null
  isEditing.value = true
  formError.value = null
}

async function submit() {
  formError.value = null
  // O schema já é um objeto estruturado produzido pelo AttributeSchemaBuilder — sem parse de JSON.
  const attributes_schema: Record<string, unknown> | null = form.schema

  const description = form.description.trim() || null
  try {
    if (isEditing.value) {
      await assetTypesStore.update(form.id, { name: form.name, description, attributes_schema })
    } else {
      await assetTypesStore.create({ name: form.name, description, attributes_schema })
    }
    savedOnce.value = true
    setTimeout(() => {
      savedOnce.value = false
    }, 3000)
    resetForm()
    await assetTypesStore.load(1, 20, tab.value === 'active')
  } catch (err) {
    formError.value = extractProblemMessage(err, 'Não foi possível salvar o tipo de ativo.')
  }
}

async function confirmDeactivate(t: AssetType) {
  if (!confirm(`Desativar o tipo "${t.name}"? Ele sai da listagem ativa; o histórico permanece.`))
    return
  actionError.value = null
  try {
    await assetTypesStore.deactivate(t.id)
    if (isEditing.value && form.id === t.id) resetForm()
  } catch (err) {
    actionError.value = extractProblemMessage(err, 'Não foi possível desativar o tipo de ativo.')
  }
}

async function reactivate(t: AssetType) {
  actionError.value = null
  try {
    await assetTypesStore.update(t.id, { is_active: true })
    await assetTypesStore.load(1, 20, tab.value === 'active')
  } catch (err) {
    actionError.value = extractProblemMessage(err, 'Não foi possível reativar o tipo de ativo.')
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="phdr">
        <div>
          <p class="eyebrow">Cadastros</p>
          <h2 class="page-h1">Tipos de ativo</h2>
          <p class="page-desc">Categorias de ativos inspecionáveis (veículos, prédios, equipamentos…).</p>
        </div>
        <button type="button" class="btn-secondary btn-sm" @click="resetForm">+ Novo tipo</button>
      </div>

      <div class="filter-tabs" style="margin-bottom: 16px;">
        <button class="filter-tab" :class="{ active: tab === 'active' }" type="button" @click="switchTab('active')">
          Ativos
        </button>
        <button class="filter-tab" :class="{ active: tab === 'inactive' }" type="button" @click="switchTab('inactive')">
          Inativos
        </button>
      </div>

      <p v-if="assetTypesStore.error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ assetTypesStore.error }}
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
              <span class="flabel">Nome do tipo</span>
              <input v-model="form.name" type="text" minlength="2" maxlength="150" required />
            </label>

            <label class="field">
              <span class="flabel">Descrição (opcional)</span>
              <textarea v-model="form.description" rows="2" maxlength="2000"></textarea>
            </label>

            <div class="field">
              <span class="flabel">Atributos do tipo (opcional)</span>
              <AttributeSchemaBuilder :key="form.id || 'new'" v-model="form.schema" />
              <span style="font-size:11px;color:var(--sa-muted);">
                Defina os atributos que cada ativo deste tipo poderá preencher.
              </span>
            </div>

            <p v-if="savedOnce" style="font-size:13px;font-weight:600;color:var(--sa-ok);padding:6px 0;">
              ✓ Tipo salvo com sucesso.
            </p>
            <p v-if="formError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ formError }}</p>

            <div style="display:flex;flex-direction:column;gap:8px;">
              <button type="submit" class="btn-primary btn-full" :disabled="assetTypesStore.isSaving">{{ submitLabel }}</button>
              <button v-if="isEditing" type="button" class="btn-secondary btn-full" @click="resetForm">
                Cancelar edição
              </button>
            </div>
          </form>
        </div>

        <!-- Tabela -->
        <div class="card" style="overflow-x:auto;">
          <p v-if="assetTypesStore.isLoading" style="font-size:13px;color:var(--sa-muted);padding:16px;">Carregando...</p>
          <template v-else>
            <p v-if="assetTypesStore.items.length === 0" style="font-size:13px;color:var(--sa-muted);padding:16px;">
              Nenhum tipo de ativo {{ tab === 'active' ? 'ativo' : 'inativo' }} nesta empresa.
            </p>
            <table v-else class="tbl">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Descrição</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in assetTypesStore.items" :key="t.id">
                  <td class="tbl-name">{{ t.name }}</td>
                  <td style="color:var(--sa-muted);">{{ t.description || '—' }}</td>
                  <td>
                    <span class="status-chip" :class="{ 'status-chip--inactive': !t.is_active }">
                      {{ t.is_active ? 'Ativo' : 'Inativo' }}
                    </span>
                  </td>
                  <td>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;">
                      <button v-if="t.is_active" class="inline-action" type="button" @click="editType(t)">Editar</button>
                      <button
                        v-if="t.is_active"
                        class="inline-action"
                        type="button"
                        style="color:var(--sa-danger);"
                        :disabled="assetTypesStore.isSaving"
                        @click="confirmDeactivate(t)"
                      >Desativar</button>
                      <button
                        v-else
                        class="inline-action"
                        type="button"
                        style="color:var(--sa-ok);"
                        :disabled="assetTypesStore.isSaving"
                        @click="reactivate(t)"
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
