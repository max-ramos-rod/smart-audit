<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import AppShell from '@/components/layout/AppShell.vue'
import AttributeValueEditor from '@/components/ui/AttributeValueEditor.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchAssetTypes } from '@/services/asset-types.service'
import { fetchClients } from '@/services/clients.service'
import { useAssetsStore } from '@/stores/assets/assets.store'
import type { AssetType } from '@/types/asset-types'
import type { Asset } from '@/types/assets'
import type { Client } from '@/types/clients'

const assetsStore = useAssetsStore()

const assetTypes = ref<AssetType[]>([])
const clients = ref<Client[]>([])

const tab = ref<'active' | 'inactive'>('active')
const filterTypeId = ref('')
const filterClientId = ref('')

const isEditing = ref(false)
const formError = ref<string | null>(null)
const actionError = ref<string | null>(null)
const savedOnce = ref(false)

// kind=root → client_id opcional; kind=component → parent obrigatório, sem client (V3/M6).
// `attributesJson` substitui o antigo `schemaText` (JSON manual). Contrato do store mantido:
// `attributes_json: Record<string, unknown> | null` (Sprint 1 — Zero JSON).
const form = reactive<{
  id: string
  kind: 'root' | 'component'
  asset_type_id: string
  identifier: string
  parent_asset_id: string
  client_id: string
  attributesJson: Record<string, unknown>
}>({
  id: '',
  kind: 'root',
  asset_type_id: '',
  identifier: '',
  parent_asset_id: '',
  client_id: '',
  attributesJson: {},
})

// Schema do tipo selecionado — alimenta o AttributeValueEditor (campos dinâmicos por tipo).
const selectedTypeSchema = computed<Record<string, unknown> | null>(() => {
  const t = assetTypes.value.find((x) => x.id === form.asset_type_id)
  return (t?.attributes_schema as Record<string, unknown> | null) ?? null
})

// Ao trocar o tipo de ativo, os atributos antigos não fazem mais sentido — limpa-os (V/Q).
function onTypeChange() {
  form.attributesJson = {}
}

const typeName = computed(() => {
  const map = new Map(assetTypes.value.map((t) => [t.id, t.name]))
  return (id: string) => map.get(id) ?? '—'
})
const clientName = computed(() => {
  const map = new Map(clients.value.map((c) => [c.id, c.name]))
  return (id: string | null) => (id ? (map.get(id) ?? '—') : '—')
})
// Pais possíveis: ativos que já existem (a árvore é montada na criação, M5).
const parentOptions = computed(() => assetsStore.items.filter((a) => a.id !== form.id))

const title = computed(() => (isEditing.value ? 'Editar ativo' : 'Novo ativo'))
const submitLabel = computed(() => {
  if (assetsStore.isSaving) return isEditing.value ? 'Salvando...' : 'Criando...'
  return isEditing.value ? 'Salvar alterações' : 'Criar ativo'
})

onMounted(async () => {
  const [typesResp, clientsResp] = await Promise.all([
    fetchAssetTypes(1, 100, true),
    fetchClients(1, 100, true),
  ])
  assetTypes.value = typesResp.data
  clients.value = clientsResp.data
  await applyFilters()
})

function currentFilters() {
  return {
    status: tab.value,
    asset_type_id: filterTypeId.value || undefined,
    client_id: filterClientId.value || undefined,
  }
}

async function applyFilters() {
  await assetsStore.load(1, 20, currentFilters())
}

async function switchTab(t: 'active' | 'inactive') {
  tab.value = t
  resetForm()
  assetsStore.clearDetail()
  await applyFilters()
}

function resetForm() {
  form.id = ''
  form.kind = 'root'
  form.asset_type_id = ''
  form.identifier = ''
  form.parent_asset_id = ''
  form.client_id = ''
  form.attributesJson = {}
  isEditing.value = false
  formError.value = null
}

function startComponentUnder(parent: Asset) {
  resetForm()
  form.kind = 'component'
  form.parent_asset_id = parent.id
  formError.value = null
}

function editAsset(a: Asset) {
  form.id = a.id
  form.kind = a.parent_asset_id ? 'component' : 'root'
  form.asset_type_id = a.asset_type_id
  form.identifier = a.identifier
  form.parent_asset_id = a.parent_asset_id ?? ''
  form.client_id = a.client_id ?? ''
  form.attributesJson = { ...a.attributes_json }
  isEditing.value = true
  formError.value = null
}

async function submit() {
  formError.value = null
  // Os atributos já vêm estruturados do AttributeValueEditor — sem parse de JSON.
  const attributes_json: Record<string, unknown> | null = Object.keys(form.attributesJson).length
    ? form.attributesJson
    : null

  try {
    if (isEditing.value) {
      // parent é imutável (M5): não enviado. client só faz sentido em raiz.
      await assetsStore.update(form.id, {
        identifier: form.identifier,
        client_id: form.kind === 'root' ? form.client_id || null : undefined,
        attributes_json,
      })
    } else {
      await assetsStore.create({
        asset_type_id: form.asset_type_id,
        identifier: form.identifier,
        parent_asset_id: form.kind === 'component' ? form.parent_asset_id : null,
        client_id: form.kind === 'root' ? form.client_id || null : null,
        attributes_json,
      })
    }
    savedOnce.value = true
    setTimeout(() => {
      savedOnce.value = false
    }, 3000)
    resetForm()
  } catch (err) {
    formError.value = extractProblemMessage(err, 'Não foi possível salvar o ativo.')
  }
}

async function viewChildren(a: Asset) {
  actionError.value = null
  try {
    await assetsStore.loadDetail(a.id)
  } catch (err) {
    actionError.value = extractProblemMessage(err, 'Não foi possível carregar os filhos.')
  }
}

async function confirmDeactivate(a: Asset) {
  if (
    !confirm(
      `Desativar o ativo "${a.identifier}"? Toda a subárvore também é desativada (em cascata).`,
    )
  )
    return
  actionError.value = null
  try {
    await assetsStore.deactivate(a.id)
    if (isEditing.value && form.id === a.id) resetForm()
    if (assetsStore.detail?.id === a.id) assetsStore.clearDetail()
  } catch (err) {
    actionError.value = extractProblemMessage(err, 'Não foi possível desativar o ativo.')
  }
}

async function reactivate(a: Asset) {
  actionError.value = null
  try {
    // Reativação é top-down (V7): se o pai estiver inativo, o backend retorna 400.
    await assetsStore.update(a.id, { status: 'active' })
    await applyFilters()
  } catch (err) {
    actionError.value = extractProblemMessage(err, 'Não foi possível reativar o ativo.')
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="phdr">
        <div>
          <p class="eyebrow">Cadastros</p>
          <h2 class="page-h1">Ativos</h2>
          <p class="page-desc">Ativos inspecionáveis e seus componentes (raiz → componentes).</p>
        </div>
        <button type="button" class="btn-secondary btn-sm" @click="resetForm">+ Novo ativo</button>
      </div>

      <div class="filter-tabs" style="margin-bottom: 16px;">
        <button class="filter-tab" :class="{ active: tab === 'active' }" type="button" @click="switchTab('active')">
          Ativos
        </button>
        <button class="filter-tab" :class="{ active: tab === 'inactive' }" type="button" @click="switchTab('inactive')">
          Inativos
        </button>
      </div>

      <!-- Filtros -->
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px;">
        <label class="field" style="min-width:200px;">
          <span class="flabel">Filtrar por tipo</span>
          <select v-model="filterTypeId" @change="applyFilters">
            <option value="">Todos os tipos</option>
            <option v-for="t in assetTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
        </label>
        <label class="field" style="min-width:200px;">
          <span class="flabel">Filtrar por cliente</span>
          <select v-model="filterClientId" @change="applyFilters">
            <option value="">Todos os clientes</option>
            <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
        </label>
      </div>

      <p v-if="assetsStore.error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">
        {{ assetsStore.error }}
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
            <!-- Tipo de cadastro: raiz ou componente (parent imutável após criar, M5) -->
            <div v-if="!isEditing" class="filter-tabs">
              <button class="filter-tab" :class="{ active: form.kind === 'root' }" type="button" @click="form.kind = 'root'">
                Raiz
              </button>
              <button class="filter-tab" :class="{ active: form.kind === 'component' }" type="button" @click="form.kind = 'component'">
                Componente
              </button>
            </div>

            <label v-if="!isEditing && form.kind === 'component'" class="field">
              <span class="flabel">Ativo pai</span>
              <select v-model="form.parent_asset_id" required>
                <option value="" disabled>Selecione o pai</option>
                <option v-for="p in parentOptions" :key="p.id" :value="p.id">{{ p.identifier }}</option>
              </select>
            </label>

            <label class="field">
              <span class="flabel">Tipo de ativo</span>
              <select v-model="form.asset_type_id" :disabled="isEditing" required @change="onTypeChange">
                <option value="" disabled>Selecione o tipo</option>
                <option v-for="t in assetTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </label>

            <label class="field">
              <span class="flabel">Identificador</span>
              <input v-model="form.identifier" type="text" minlength="2" maxlength="180" required />
            </label>

            <!-- client_id só em raiz (M6/V3) -->
            <label v-if="form.kind === 'root'" class="field">
              <span class="flabel">Cliente (opcional)</span>
              <select v-model="form.client_id">
                <option value="">Sem cliente</option>
                <option v-for="c in clients" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </label>

            <div v-if="form.asset_type_id" class="field">
              <span class="flabel">Atributos do ativo</span>
              <AttributeValueEditor v-model="form.attributesJson" :schema="selectedTypeSchema" />
            </div>

            <p v-if="savedOnce" style="font-size:13px;font-weight:600;color:var(--sa-ok);padding:6px 0;">
              ✓ Ativo salvo com sucesso.
            </p>
            <p v-if="formError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ formError }}</p>

            <div style="display:flex;flex-direction:column;gap:8px;">
              <button type="submit" class="btn-primary btn-full" :disabled="assetsStore.isSaving">{{ submitLabel }}</button>
              <button v-if="isEditing || form.kind === 'component'" type="button" class="btn-secondary btn-full" @click="resetForm">
                Cancelar
              </button>
            </div>
          </form>
        </div>

        <!-- Tabela + painel de filhos -->
        <div style="display:grid;gap:16px;">
          <div class="card" style="overflow-x:auto;">
            <p v-if="assetsStore.isLoading" style="font-size:13px;color:var(--sa-muted);padding:16px;">Carregando...</p>
            <template v-else>
              <p v-if="assetsStore.items.length === 0" style="font-size:13px;color:var(--sa-muted);padding:16px;">
                Nenhum ativo {{ tab === 'active' ? 'ativo' : 'inativo' }} com os filtros atuais.
              </p>
              <table v-else class="tbl">
                <thead>
                  <tr>
                    <th>Identificador</th>
                    <th>Tipo</th>
                    <th>Cliente</th>
                    <th>Nível</th>
                    <th>Status</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="a in assetsStore.items" :key="a.id">
                    <td class="tbl-name">{{ a.identifier }}</td>
                    <td style="color:var(--sa-muted);">{{ typeName(a.asset_type_id) }}</td>
                    <td style="color:var(--sa-muted);">{{ a.parent_asset_id ? '(herda da raiz)' : clientName(a.client_id) }}</td>
                    <td>
                      <span class="status-chip" :class="{ 'status-chip--warn': a.parent_asset_id }">
                        {{ a.parent_asset_id ? 'Componente' : 'Raiz' }}
                      </span>
                    </td>
                    <td>
                      <span class="status-chip" :class="{ 'status-chip--inactive': a.status !== 'active' }">
                        {{ a.status === 'active' ? 'Ativo' : a.status === 'inactive' ? 'Inativo' : 'Baixado' }}
                      </span>
                    </td>
                    <td>
                      <div style="display:flex;gap:8px;flex-wrap:wrap;">
                        <button class="inline-action" type="button" @click="viewChildren(a)">Filhos</button>
                        <button v-if="a.status === 'active'" class="inline-action" type="button" @click="editAsset(a)">Editar</button>
                        <button
                          v-if="a.status === 'active'"
                          class="inline-action"
                          type="button"
                          style="color:var(--sa-danger);"
                          :disabled="assetsStore.isSaving"
                          @click="confirmDeactivate(a)"
                        >Desativar</button>
                        <button
                          v-else-if="a.status === 'inactive'"
                          class="inline-action"
                          type="button"
                          style="color:var(--sa-ok);"
                          :disabled="assetsStore.isSaving"
                          @click="reactivate(a)"
                        >Reativar</button>
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </template>
          </div>

          <!-- Painel de filhos diretos -->
          <div v-if="assetsStore.detail" class="card card-p">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;">
              <div>
                <p class="eyebrow">Filhos diretos</p>
                <h3 style="font-size:16px;font-weight:700;color:var(--sa-text);margin-top:3px;">{{ assetsStore.detail.identifier }}</h3>
              </div>
              <div style="display:flex;gap:8px;">
                <button
                  v-if="tab === 'active' && assetsStore.detail.status === 'active'"
                  class="btn-secondary btn-sm"
                  type="button"
                  @click="startComponentUnder(assetsStore.detail)"
                >+ Componente</button>
                <button class="inline-action" type="button" @click="assetsStore.clearDetail()">Fechar</button>
              </div>
            </div>
            <p v-if="assetsStore.detail.components.length === 0" style="font-size:13px;color:var(--sa-muted);">
              Este ativo não possui componentes diretos.
            </p>
            <ul v-else style="display:grid;gap:8px;list-style:none;padding:0;margin:0;">
              <li
                v-for="c in assetsStore.detail.components"
                :key="c.id"
                style="display:flex;justify-content:space-between;gap:12px;border:1px solid var(--sa-border);border-radius:8px;padding:8px 12px;"
              >
                <span class="tbl-name">{{ c.identifier }}</span>
                <span style="color:var(--sa-muted);font-size:13px;">{{ typeName(c.asset_type_id) }}</span>
                <button class="inline-action" type="button" @click="viewChildren(c)">Ver filhos</button>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>
