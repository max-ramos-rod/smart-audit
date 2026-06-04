<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch, useTemplateRef } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchForm, importForm } from '@/services/forms.service'
import { useFormsStore } from '@/stores/forms/forms.store'
import type { FormFieldCreatePayload } from '@/types/forms'

const router = useRouter()
const formsStore = useFormsStore()

const search = ref('')

const showCreateComposer = ref(false)
const createError = ref<string | null>(null)
const createState = reactive({
  name: '',
  description: '',
  fields: [createEmptyField(1)],
})

const showVersionComposer = ref(false)
const versionFormId = ref<string | null>(null)
const versionFormName = ref('')
const versionError = ref<string | null>(null)
const versionFields = ref<FormFieldCreatePayload[]>([createEmptyField(1)])

const currentPage = ref(1)

// ── B5/B6: expand state ──
const expandedCreateIndex  = ref<number | null>(null)
const expandedVersionIndex = ref<number | null>(null)

// ── B7: key-touched tracking ──
const keyTouchedCreate  = reactive<Record<number, boolean>>({})
const keyTouchedVersion = reactive<Record<number, boolean>>({})

// ── B8: collapsed sections ──
const collapsedSectionsCreate  = reactive<Set<number>>(new Set())
const collapsedSectionsVersion = reactive<Set<number>>(new Set())

// ── B9: bulk selection ──
const selectModeCreate  = ref(false)
const selectedCreate    = reactive<Set<number>>(new Set())
const selectModeVersion = ref(false)
const selectedVersion   = reactive<Set<number>>(new Set())

// ── Search/filter for create composer ──
const createSearchQuery = ref('')
const createTypeFilter  = ref('')

// ── Search/filter for version composer ──
const versionSearchQuery = ref('')
const versionTypeFilter  = ref('')

const publishedCount = computed(
  () => formsStore.items.filter((f) => f.current_version_status === 'published').length,
)
const draftCount = computed(
  () => formsStore.items.filter((f) => f.current_version_status !== 'published').length,
)

const filteredForms = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return formsStore.items
  return formsStore.items.filter(
    (f) =>
      f.name.toLowerCase().includes(q) ||
      (f.description ?? '').toLowerCase().includes(q),
  )
})

const filteredCreateFields = computed(() => {
  const q = createSearchQuery.value.toLowerCase().trim()
  const t = createTypeFilter.value
  return createState.fields.filter((f) => {
    const matchType = !t || f.field_type === t
    const matchQ = !q || f.label.toLowerCase().includes(q) || f.key.toLowerCase().includes(q)
    return matchType && matchQ
  })
})

const filteredVersionFields = computed(() => {
  const q = versionSearchQuery.value.toLowerCase().trim()
  const t = versionTypeFilter.value
  return versionFields.value.filter((f) => {
    const matchType = !t || f.field_type === t
    const matchQ = !q || f.label.toLowerCase().includes(q) || f.key.toLowerCase().includes(q)
    return matchType && matchQ
  })
})

// ── B7: auto-key slug ──
function toFieldSlug(label: string): string {
  return label
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 80)
}

// ── B7: watchers ──
watch(
  () => createState.fields.map((f, i) => ({ label: f.label, key: f.key, i })),
  (curr, prev) => {
    if (!prev) return
    curr.forEach(({ label, key, i }) => {
      if (label !== prev[i]?.label && !keyTouchedCreate[i]) {
        if (createState.fields[i]?.field_type !== 'section') {
          createState.fields[i].key = toFieldSlug(label)
        }
      }
      if (key !== prev[i]?.key && key !== toFieldSlug(label)) {
        keyTouchedCreate[i] = true
      }
    })
  },
)

watch(
  () => versionFields.value.map((f, i) => ({ label: f.label, key: f.key, i })),
  (curr, prev) => {
    if (!prev) return
    curr.forEach(({ label, key, i }) => {
      if (label !== prev[i]?.label && !keyTouchedVersion[i]) {
        if (versionFields.value[i]?.field_type !== 'section') {
          versionFields.value[i].key = toFieldSlug(label)
        }
      }
      if (key !== prev[i]?.key && key !== toFieldSlug(label)) {
        keyTouchedVersion[i] = true
      }
    })
  },
)

// ── B5/B6: toggle expand ──
function toggleCreateExpand(i: number) {
  expandedCreateIndex.value = expandedCreateIndex.value === i ? null : i
}

function toggleVersionExpand(i: number) {
  expandedVersionIndex.value = expandedVersionIndex.value === i ? null : i
}

// ── B8: section collapse ──
function toggleSectionCollapse(collapsed: Set<number>, sectionIndex: number) {
  if (collapsed.has(sectionIndex)) collapsed.delete(sectionIndex)
  else collapsed.add(sectionIndex)
}

function isFieldHidden(fields: FormFieldCreatePayload[], fieldIndex: number, collapsed: Set<number>): boolean {
  for (let i = fieldIndex - 1; i >= 0; i--) {
    if (fields[i].field_type === 'section') {
      return collapsed.has(i)
    }
  }
  return false
}

// ── B9: bulk delete ──
function bulkDeleteCreate() {
  const indices = [...selectedCreate].sort((a, b) => b - a)
  for (const i of indices) {
    createState.fields.splice(i, 1)
  }
  createState.fields.forEach((f, i) => { f.position = i + 1 })
  selectedCreate.clear()
  selectModeCreate.value = false
}

function bulkDeleteVersion() {
  const indices = [...selectedVersion].sort((a, b) => b - a)
  for (const i of indices) {
    versionFields.value.splice(i, 1)
  }
  versionFields.value.forEach((f, i) => { f.position = i + 1 })
  selectedVersion.clear()
  selectModeVersion.value = false
}

async function loadPage(page: number) {
  currentPage.value = page
  await formsStore.load(page)
}

onMounted(() => {
  loadPage(1)
})

function createEmptyField(position: number): FormFieldCreatePayload {
  return { key: '', label: '', field_type: 'boolean', required: false, position, config_json: {} }
}

function openCreateComposer() {
  showVersionComposer.value = false
  showCreateComposer.value = true
}

function closeCreateComposer() {
  showCreateComposer.value = false
  createState.name = ''
  createState.description = ''
  createState.fields = [createEmptyField(1)]
  createError.value = null
  expandedCreateIndex.value = null
  selectedCreate.clear()
  selectModeCreate.value = false
  Object.keys(keyTouchedCreate).forEach(k => delete (keyTouchedCreate as Record<string, boolean>)[k])
  collapsedSectionsCreate.clear()
}

function addCreateField(fieldType: FormFieldCreatePayload['field_type'] = 'boolean') {
  const newField = createEmptyField(createState.fields.length + 1)
  newField.field_type = fieldType
  if (fieldType === 'section') { newField.key = `__section_${createState.fields.length + 1}__`; newField.required = false }
  createState.fields.push(newField)
  expandedCreateIndex.value = createState.fields.length - 1
}

function removeCreateField(index: number) {
  if (createState.fields.length === 1) return
  createState.fields.splice(index, 1)
  createState.fields.forEach((f, i) => { f.position = i + 1 })
  if (expandedCreateIndex.value === index) expandedCreateIndex.value = null
  else if (expandedCreateIndex.value !== null && expandedCreateIndex.value > index) expandedCreateIndex.value--
}

function setCreateFieldConfig(field: FormFieldCreatePayload, patch: Record<string, unknown>) {
  field.config_json = { ...(field.config_json as Record<string, unknown>), ...patch }
}

function getCreateOptionsString(field: FormFieldCreatePayload): string {
  return Array.isArray(field.config_json.options)
    ? (field.config_json.options as string[]).join(', ')
    : ''
}

function setCreateOptionsFromString(field: FormFieldCreatePayload, event: Event) {
  const opts = (event.target as HTMLInputElement).value
    .split(',').map((o) => o.trim()).filter(Boolean)
  field.config_json = opts.length ? { options: opts } : {}
}

function onCreateFieldTypeChange(field: FormFieldCreatePayload) {
  if (field.field_type === 'section') {
    field.config_json = {}
    field.required = false
  } else {
    field.config_json = {}
  }
}

async function submitCreate() {
  createError.value = null
  try {
    await formsStore.create({
      name: createState.name,
      description: createState.description || null,
      fields: createState.fields.map((f, i) => ({
        ...f,
        position: i + 1,
        key: f.field_type === 'section' ? `__section_${i + 1}__` : f.key,
        required: f.field_type === 'section' ? false : f.required,
      })),
    })
    closeCreateComposer()
  } catch (err: any) {
    createError.value = extractProblemMessage(err, 'Não foi possível criar o formulário.')
  }
}

async function openVersionComposer(formId: string, formName: string) {
  versionError.value = null
  versionFormId.value = formId
  versionFormName.value = formName
  try {
    const detail = await fetchForm(formId)
    versionFields.value = detail.current_version.fields.map((f) => ({
      key: f.key,
      label: f.label,
      field_type: f.field_type,
      required: f.required,
      position: f.position,
      config_json: f.config_json,
    }))
  } catch {
    versionFields.value = [createEmptyField(1)]
  }
  expandedVersionIndex.value = null
  selectedVersion.clear()
  selectModeVersion.value = false
  Object.keys(keyTouchedVersion).forEach(k => delete (keyTouchedVersion as Record<string, boolean>)[k])
  collapsedSectionsVersion.clear()
  showCreateComposer.value = false
  showVersionComposer.value = true
}

function closeVersionComposer() {
  showVersionComposer.value = false
  versionFormId.value = null
  versionFormName.value = ''
  versionFields.value = [createEmptyField(1)]
  versionError.value = null
  expandedVersionIndex.value = null
  selectedVersion.clear()
  selectModeVersion.value = false
  collapsedSectionsVersion.clear()
}

function addVersionField(fieldType: FormFieldCreatePayload['field_type'] = 'boolean') {
  const newField = createEmptyField(versionFields.value.length + 1)
  newField.field_type = fieldType
  if (fieldType === 'section') { newField.key = `__section_${versionFields.value.length + 1}__`; newField.required = false }
  versionFields.value.push(newField)
  expandedVersionIndex.value = versionFields.value.length - 1
}

function removeVersionField(index: number) {
  if (versionFields.value.length === 1) return
  versionFields.value.splice(index, 1)
  versionFields.value.forEach((f, i) => { f.position = i + 1 })
  if (expandedVersionIndex.value === index) expandedVersionIndex.value = null
  else if (expandedVersionIndex.value !== null && expandedVersionIndex.value > index) expandedVersionIndex.value--
}

function setVersionFieldConfig(field: FormFieldCreatePayload, patch: Record<string, unknown>) {
  field.config_json = { ...(field.config_json as Record<string, unknown>), ...patch }
}

function getVersionOptionsString(field: FormFieldCreatePayload): string {
  return Array.isArray(field.config_json.options)
    ? (field.config_json.options as string[]).join(', ')
    : ''
}

function setVersionOptionsFromString(field: FormFieldCreatePayload, event: Event) {
  const opts = (event.target as HTMLInputElement).value
    .split(',').map((o) => o.trim()).filter(Boolean)
  field.config_json = opts.length ? { options: opts } : {}
}

function onVersionFieldTypeChange(field: FormFieldCreatePayload) {
  if (field.field_type === 'section') {
    field.config_json = {}
    field.required = false
  } else {
    field.config_json = {}
  }
}

async function submitVersion() {
  if (!versionFormId.value) return
  versionError.value = null
  try {
    await formsStore.publishVersion(versionFormId.value, {
      fields: versionFields.value.map((f, i) => ({ ...f, position: i + 1 })),
    })
    closeVersionComposer()
  } catch (err: any) {
    versionError.value = extractProblemMessage(err, 'Não foi possível publicar a nova versão.')
  }
}

const FIELD_TYPE_SHORT: Record<string, string> = {
  boolean: 'S/N', text: 'TXT', number: 'NUM', date: 'DAT', select: 'SEL',
}

// ── Import CSV / Excel ──
const importFileInput = useTemplateRef<HTMLInputElement>('importFileInput')
const importLoading = ref(false)
const importError = ref<string | null>(null)

async function handleImportFile(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  importError.value = null
  importLoading.value = true
  try {
    const created = await importForm(file)
    await formsStore.load(1)
    router.push({ name: 'form-detail', params: { formId: created.id } })
  } catch (err: any) {
    importError.value = extractProblemMessage(err, 'Não foi possível importar o formulário.')
  } finally {
    importLoading.value = false
    if (importFileInput.value) importFileInput.value.value = ''
  }
}
</script>

<template>
  <AppShell>
    <div class="page">

      <!-- Header -->
      <div class="phdr">
        <div>
          <p class="eyebrow">Templates</p>
          <h2 class="page-h1">Formulários versionados</h2>
          <p class="page-desc">Checklists e auditorias da empresa ativa.</p>
        </div>
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
          <button
            type="button"
            class="btn-secondary btn-sm"
            :disabled="importLoading"
            @click="importFileInput?.click()"
          >
            {{ importLoading ? 'Importando…' : '↑ Importar CSV/Excel' }}
          </button>
          <button type="button" class="btn-primary btn-sm" @click="openCreateComposer">
            + Novo formulário
          </button>
        </div>
        <input
          ref="importFileInput"
          type="file"
          accept=".csv,.xlsx"
          style="display:none;"
          @change="handleImportFile"
        />
      </div>
      <p v-if="importError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">{{ importError }}</p>

      <!-- Stats -->
      <div class="stats-grid" style="margin-bottom:20px;">
        <div class="scard">
          <div class="sc-label">Total</div>
          <div class="sc-value">{{ formsStore.meta?.total ?? formsStore.items.length }}</div>
        </div>
        <div class="scard sc-ok">
          <div class="sc-label">Publicados</div>
          <div class="sc-value">{{ publishedCount }}</div>
        </div>
        <div class="scard">
          <div class="sc-label">Rascunhos</div>
          <div class="sc-value">{{ draftCount }}</div>
        </div>
        <div class="scard">
          <div class="sc-label">Campos (média)</div>
          <div class="sc-value">—</div>
          <div class="sc-desc">por formulário</div>
        </div>
      </div>

      <!-- ══ CREATE COMPOSER ══ -->
      <div v-if="showCreateComposer" class="card" style="margin-bottom:20px;overflow:hidden;">
        <div class="composer-hdr" style="padding:16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--sa-line);">
          <div>
            <div class="eyebrow">Criação</div>
            <div style="font-size:17px;font-weight:700;color:var(--sa-text);margin-top:3px;">Novo formulário</div>
          </div>
          <button type="button" class="btn-secondary btn-sm" @click="closeCreateComposer">Fechar</button>
        </div>

        <form @submit.prevent="submitCreate">
          <!-- Name / description -->
          <div style="padding:16px;display:grid;gap:12px;border-bottom:1px solid var(--sa-line);">
            <label style="display:grid;gap:6px;">
              <span>Nome do formulário</span>
              <input v-model="createState.name" type="text" required placeholder="Ex: Checklist NR-35 Trabalho em Altura" />
            </label>
            <label style="display:grid;gap:6px;">
              <span>Descrição (opcional)</span>
              <input v-model="createState.description" type="text" placeholder="Breve descrição do formulário" />
            </label>
          </div>

          <!-- Bulk bar -->
          <div class="bulk-bar" :class="{ on: selectModeCreate && selectedCreate.size > 0 }">
            <span class="bulk-info">{{ selectedCreate.size }} campo(s) selecionado(s)</span>
            <button type="button" class="btn-danger" @click="bulkDeleteCreate">Remover</button>
          </div>

          <!-- Two-panel editor -->
          <div class="editor">
            <!-- Outline (desktop) -->
            <aside class="outline">
              <div class="ol-hdr">
                <span>Campos</span>
                <span style="font-size:10px;font-weight:400;text-transform:none;letter-spacing:0;color:#94a3b8;">{{ createState.fields.length }}</span>
              </div>
              <div class="ol-list">
                <button
                  v-for="(f, i) in createState.fields"
                  :key="i"
                  type="button"
                  class="ol-item"
                  :class="{ active: expandedCreateIndex === i }"
                  @click="toggleCreateExpand(i)"
                >
                  <span v-if="f.field_type === 'section'" style="font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;">§ {{ f.label || 'Seção' }}</span>
                  <span v-else>{{ f.label || '(campo ' + (i + 1) + ')' }}</span>
                  <span class="ol-cnt">{{ FIELD_TYPE_SHORT[f.field_type] ?? f.field_type.slice(0,3).toUpperCase() }}</span>
                </button>
              </div>
              <div class="ol-add">
                <button type="button" @click="addCreateField('boolean')">+ Campo</button>
              </div>
            </aside>

            <!-- Fields pane -->
            <div class="fields-pane">
              <!-- Toolbar -->
              <div class="toolbar">
                <div class="sbar" style="flex:1;min-width:120px;">
                  <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" style="color:var(--sa-muted);flex-shrink:0;"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                  <input v-model="createSearchQuery" type="text" placeholder="Buscar campo…" style="border:none;background:none;outline:none;font-size:13px;color:var(--sa-text);font-family:inherit;flex:1;min-width:0;" />
                </div>
                <select v-model="createTypeFilter" style="font-family:inherit;font-size:12px;font-weight:600;padding:6px 10px;border:1px solid var(--sa-line);border-radius:8px;background:#fff;color:var(--sa-muted);cursor:pointer;outline:none;flex-shrink:0;">
                  <option value="">Tipo: Todos</option>
                  <option value="boolean">Sim/Não</option>
                  <option value="text">Texto</option>
                  <option value="number">Número</option>
                  <option value="select">Seleção</option>
                  <option value="date">Data</option>
                </select>
                <button type="button" class="btn-ghost" style="flex-shrink:0;" @click="selectModeCreate = !selectModeCreate; selectedCreate.clear()">
                  {{ selectModeCreate ? 'Cancelar' : 'Selecionar' }}
                </button>
                <span style="font-family:var(--mono,monospace);font-size:11px;color:var(--sa-muted);margin-left:auto;white-space:nowrap;flex-shrink:0;">{{ filteredCreateFields.length }} campo(s)</span>
              </div>

              <!-- Field rows -->
              <div class="fields-inner">
                <template v-for="field in filteredCreateFields" :key="createState.fields.indexOf(field)">
                  <div
                    v-show="!isFieldHidden(createState.fields, createState.fields.indexOf(field), collapsedSectionsCreate)"
                    class="f-wrap"
                    :class="{ expanded: expandedCreateIndex === createState.fields.indexOf(field) }"
                  >
                    <!-- Compact row -->
                    <div
                      class="f-row"
                      :class="{ expanded: expandedCreateIndex === createState.fields.indexOf(field) }"
                      @click="toggleCreateExpand(createState.fields.indexOf(field))"
                    >
                      <!-- Section row -->
                      <template v-if="field.field_type === 'section'">
                        <label v-if="selectModeCreate" class="f-chk" @click.stop>
                          <input
                            type="checkbox"
                            :checked="selectedCreate.has(createState.fields.indexOf(field))"
                            @change="(e: Event) => {
                              const idx = createState.fields.indexOf(field)
                              if ((e.target as HTMLInputElement).checked) selectedCreate.add(idx)
                              else selectedCreate.delete(idx)
                            }"
                          />
                        </label>
                        <span
                          class="sec-toggle"
                          :class="{ coll: collapsedSectionsCreate.has(createState.fields.indexOf(field)) }"
                          @click.stop="toggleSectionCollapse(collapsedSectionsCreate, createState.fields.indexOf(field))"
                        >▶</span>
                        <span class="f-num" style="opacity:.4;">§</span>
                        <span class="f-type section" style="font-size:9px;">SEÇÃO</span>
                        <span class="f-lbl" style="font-weight:700;">{{ field.label || 'Seção sem nome' }}</span>
                        <span class="f-arr">›</span>
                      </template>
                      <!-- Regular field row -->
                      <template v-else>
                        <label v-if="selectModeCreate" class="f-chk" @click.stop>
                          <input
                            type="checkbox"
                            :checked="selectedCreate.has(createState.fields.indexOf(field))"
                            @change="(e: Event) => {
                              const idx = createState.fields.indexOf(field)
                              if ((e.target as HTMLInputElement).checked) selectedCreate.add(idx)
                              else selectedCreate.delete(idx)
                            }"
                          />
                        </label>
                        <span class="f-drag" title="Arrastar">⠿</span>
                        <span class="f-num">{{ createState.fields.indexOf(field) + 1 }}</span>
                        <span class="f-type" :class="field.field_type">
                          {{ FIELD_TYPE_SHORT[field.field_type] ?? field.field_type.toUpperCase().slice(0, 3) }}
                        </span>
                        <span class="f-lbl">{{ field.label || '(sem nome)' }}</span>
                        <span class="f-key">{{ field.key || '—' }}</span>
                        <span class="f-req">
                          <span v-if="field.required" class="f-rdot" title="Obrigatório"></span>
                        </span>
                        <span class="f-wt" :title="'Peso ' + ((field.config_json?.weight as number) || 1)">
                          {{ (field.config_json?.weight as number) > 1 ? '×' + (field.config_json?.weight as number) : '' }}
                        </span>
                        <span class="f-arr">›</span>
                      </template>
                    </div>

                    <!-- Config panel -->
                    <div v-show="expandedCreateIndex === createState.fields.indexOf(field)" class="f-cfg open">
                      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-brand);">
                          {{ field.field_type === 'section' ? 'Seção' : 'Campo' }} {{ createState.fields.indexOf(field) + 1 }}
                        </span>
                        <div style="display:flex;gap:4px;">
                          <button
                            v-if="createState.fields.length > 1"
                            type="button"
                            class="btn-danger"
                            @click="removeCreateField(createState.fields.indexOf(field))"
                          >Remover</button>
                        </div>
                      </div>
                      <div style="display:grid;gap:10px;grid-template-columns:1fr 1fr;">
                        <!-- Key (non-section) -->
                        <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;">
                          <span>Chave</span>
                          <input
                            :value="field.key"
                            type="text"
                            required
                            style="font-family:var(--mono,monospace);font-size:12px;"
                            @input="(e: Event) => {
                              const idx = createState.fields.indexOf(field)
                              field.key = (e.target as HTMLInputElement).value
                              keyTouchedCreate[idx] = true
                            }"
                          />
                        </label>
                        <!-- Label -->
                        <label :style="field.field_type === 'section' ? 'display:grid;gap:6px;grid-column:1/-1;' : 'display:grid;gap:6px;'">
                          <span>{{ field.field_type === 'section' ? 'Título da seção' : 'Label' }}</span>
                          <input
                            :value="field.label"
                            type="text"
                            required
                            @input="field.label = ($event.target as HTMLInputElement).value"
                          />
                        </label>
                        <!-- Tipo -->
                        <label style="display:grid;gap:6px;">
                          <span>Tipo</span>
                          <select v-model="field.field_type" @change="onCreateFieldTypeChange(field)">
                            <option value="boolean">Sim / Não</option>
                            <option value="text">Texto</option>
                            <option value="number">Número</option>
                            <option value="select">Seleção</option>
                            <option value="date">Data</option>
                            <option value="section">── Seção ──</option>
                          </select>
                        </label>
                        <!-- Obrigatório -->
                        <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;">
                          <span>Obrigatório</span>
                          <select
                            :value="String(field.required)"
                            @change="field.required = ($event.target as HTMLSelectElement).value === 'true'"
                          >
                            <option value="true">Sim</option>
                            <option value="false">Não</option>
                          </select>
                        </label>
                        <!-- Peso (boolean) -->
                        <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
                          <span>Peso</span>
                          <input
                            :value="(field.config_json as Record<string, unknown>).weight ?? 1"
                            type="number" min="0.1" step="0.1"
                            @input="setCreateFieldConfig(field, { weight: parseFloat(($event.target as HTMLInputElement).value) || 1 })"
                          />
                        </label>
                        <!-- Permite N/A (boolean) -->
                        <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
                          <span>Permite N/A</span>
                          <select
                            :value="(field.config_json as Record<string, unknown>).allow_na ? 'true' : 'false'"
                            @change="setCreateFieldConfig(field, { allow_na: ($event.target as HTMLSelectElement).value === 'true' })"
                          >
                            <option value="false">Não</option>
                            <option value="true">Sim</option>
                          </select>
                        </label>
                        <!-- Opções (select) -->
                        <label v-if="field.field_type === 'select'" style="display:grid;gap:6px;grid-column:1/-1;">
                          <span>Opções (separadas por vírgula)</span>
                          <input
                            :value="getCreateOptionsString(field)"
                            type="text"
                            placeholder="Ex: Conforme, Não conforme, Parcial"
                            @input="setCreateOptionsFromString(field, $event)"
                          />
                        </label>
                      </div>
                    </div>
                  </div>
                </template>

                <!-- Add field row -->
                <div class="add-row">
                  <button type="button" class="add-main" @click="addCreateField('boolean')">+ Campo</button>
                  <div class="tchips">
                    <button v-for="[t, l] in Object.entries(FIELD_TYPE_SHORT)" :key="t" type="button" class="tchip" @click="addCreateField(t as FormFieldCreatePayload['field_type'])">{{ l }}</button>
                    <button type="button" class="tchip" @click="addCreateField('section')" style="color:var(--sa-muted);">§ Seção</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <p v-if="createError" style="font-size:13px;font-weight:600;color:var(--sa-danger);padding:12px 16px;">{{ createError }}</p>

          <div style="padding:12px 16px;display:flex;gap:8px;flex-wrap:wrap;border-top:1px solid var(--sa-line);">
            <button type="submit" class="btn-primary" :disabled="formsStore.isSaving">
              {{ formsStore.isSaving ? 'Criando...' : 'Criar formulário' }}
            </button>
          </div>
        </form>
      </div>

      <!-- ══ VERSION COMPOSER ══ -->
      <div v-if="showVersionComposer" class="card" style="margin-bottom:20px;overflow:hidden;">
        <div class="composer-hdr" style="padding:16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--sa-line);">
          <div>
            <div class="eyebrow">Nova versão</div>
            <div style="font-size:17px;font-weight:700;color:var(--sa-text);margin-top:3px;">{{ versionFormName }}</div>
            <div style="font-size:12px;color:var(--sa-muted);margin-top:4px;">
              Edite os campos abaixo. Uma nova versão será publicada sem alterar as inspeções anteriores.
            </div>
          </div>
          <button type="button" class="btn-secondary btn-sm" @click="closeVersionComposer">Fechar</button>
        </div>

        <form @submit.prevent="submitVersion">
          <!-- Bulk bar -->
          <div class="bulk-bar" :class="{ on: selectModeVersion && selectedVersion.size > 0 }">
            <span class="bulk-info">{{ selectedVersion.size }} campo(s) selecionado(s)</span>
            <button type="button" class="btn-danger" @click="bulkDeleteVersion">Remover</button>
          </div>

          <!-- Two-panel editor -->
          <div class="editor">
            <!-- Outline (desktop) -->
            <aside class="outline">
              <div class="ol-hdr">
                <span>Campos</span>
                <span style="font-size:10px;font-weight:400;text-transform:none;letter-spacing:0;color:#94a3b8;">{{ versionFields.length }}</span>
              </div>
              <div class="ol-list">
                <button
                  v-for="(f, i) in versionFields"
                  :key="i"
                  type="button"
                  class="ol-item"
                  :class="{ active: expandedVersionIndex === i }"
                  @click="toggleVersionExpand(i)"
                >
                  <span v-if="f.field_type === 'section'" style="font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;">§ {{ f.label || 'Seção' }}</span>
                  <span v-else>{{ f.label || '(campo ' + (i + 1) + ')' }}</span>
                  <span class="ol-cnt">{{ FIELD_TYPE_SHORT[f.field_type] ?? f.field_type.slice(0,3).toUpperCase() }}</span>
                </button>
              </div>
              <div class="ol-add">
                <button type="button" @click="addVersionField('boolean')">+ Campo</button>
              </div>
            </aside>

            <!-- Fields pane -->
            <div class="fields-pane">
              <!-- Toolbar -->
              <div class="toolbar">
                <div class="sbar" style="flex:1;min-width:120px;">
                  <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" style="color:var(--sa-muted);flex-shrink:0;"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
                  <input v-model="versionSearchQuery" type="text" placeholder="Buscar campo…" style="border:none;background:none;outline:none;font-size:13px;color:var(--sa-text);font-family:inherit;flex:1;min-width:0;" />
                </div>
                <select v-model="versionTypeFilter" style="font-family:inherit;font-size:12px;font-weight:600;padding:6px 10px;border:1px solid var(--sa-line);border-radius:8px;background:#fff;color:var(--sa-muted);cursor:pointer;outline:none;flex-shrink:0;">
                  <option value="">Tipo: Todos</option>
                  <option value="boolean">Sim/Não</option>
                  <option value="text">Texto</option>
                  <option value="number">Número</option>
                  <option value="select">Seleção</option>
                  <option value="date">Data</option>
                </select>
                <button type="button" class="btn-ghost" style="flex-shrink:0;" @click="selectModeVersion = !selectModeVersion; selectedVersion.clear()">
                  {{ selectModeVersion ? 'Cancelar' : 'Selecionar' }}
                </button>
                <span style="font-family:var(--mono,monospace);font-size:11px;color:var(--sa-muted);margin-left:auto;white-space:nowrap;flex-shrink:0;">{{ filteredVersionFields.length }} campo(s)</span>
              </div>

              <!-- Field rows -->
              <div class="fields-inner">
                <template v-for="field in filteredVersionFields" :key="versionFields.indexOf(field)">
                  <div
                    v-show="!isFieldHidden(versionFields, versionFields.indexOf(field), collapsedSectionsVersion)"
                    class="f-wrap"
                    :class="{ expanded: expandedVersionIndex === versionFields.indexOf(field) }"
                  >
                    <!-- Compact row -->
                    <div
                      class="f-row"
                      :class="{ expanded: expandedVersionIndex === versionFields.indexOf(field) }"
                      @click="toggleVersionExpand(versionFields.indexOf(field))"
                    >
                      <!-- Section row -->
                      <template v-if="field.field_type === 'section'">
                        <label v-if="selectModeVersion" class="f-chk" @click.stop>
                          <input
                            type="checkbox"
                            :checked="selectedVersion.has(versionFields.indexOf(field))"
                            @change="(e: Event) => {
                              const idx = versionFields.indexOf(field)
                              if ((e.target as HTMLInputElement).checked) selectedVersion.add(idx)
                              else selectedVersion.delete(idx)
                            }"
                          />
                        </label>
                        <span
                          class="sec-toggle"
                          :class="{ coll: collapsedSectionsVersion.has(versionFields.indexOf(field)) }"
                          @click.stop="toggleSectionCollapse(collapsedSectionsVersion, versionFields.indexOf(field))"
                        >▶</span>
                        <span class="f-num" style="opacity:.4;">§</span>
                        <span class="f-type section" style="font-size:9px;">SEÇÃO</span>
                        <span class="f-lbl" style="font-weight:700;">{{ field.label || 'Seção sem nome' }}</span>
                        <span class="f-arr">›</span>
                      </template>
                      <!-- Regular field row -->
                      <template v-else>
                        <label v-if="selectModeVersion" class="f-chk" @click.stop>
                          <input
                            type="checkbox"
                            :checked="selectedVersion.has(versionFields.indexOf(field))"
                            @change="(e: Event) => {
                              const idx = versionFields.indexOf(field)
                              if ((e.target as HTMLInputElement).checked) selectedVersion.add(idx)
                              else selectedVersion.delete(idx)
                            }"
                          />
                        </label>
                        <span class="f-drag" title="Arrastar">⠿</span>
                        <span class="f-num">{{ versionFields.indexOf(field) + 1 }}</span>
                        <span class="f-type" :class="field.field_type">
                          {{ FIELD_TYPE_SHORT[field.field_type] ?? field.field_type.toUpperCase().slice(0, 3) }}
                        </span>
                        <span class="f-lbl">{{ field.label || '(sem nome)' }}</span>
                        <span class="f-key">{{ field.key || '—' }}</span>
                        <span class="f-req">
                          <span v-if="field.required" class="f-rdot" title="Obrigatório"></span>
                        </span>
                        <span class="f-wt" :title="'Peso ' + ((field.config_json?.weight as number) || 1)">
                          {{ (field.config_json?.weight as number) > 1 ? '×' + (field.config_json?.weight as number) : '' }}
                        </span>
                        <span class="f-arr">›</span>
                      </template>
                    </div>

                    <!-- Config panel -->
                    <div v-show="expandedVersionIndex === versionFields.indexOf(field)" class="f-cfg open">
                      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                        <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-brand);">
                          {{ field.field_type === 'section' ? 'Seção' : 'Campo' }} {{ versionFields.indexOf(field) + 1 }}
                        </span>
                        <div style="display:flex;gap:4px;">
                          <button
                            v-if="versionFields.length > 1"
                            type="button"
                            class="btn-danger"
                            @click="removeVersionField(versionFields.indexOf(field))"
                          >Remover</button>
                        </div>
                      </div>
                      <div style="display:grid;gap:10px;grid-template-columns:1fr 1fr;">
                        <!-- Key (non-section) -->
                        <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;">
                          <span>Chave</span>
                          <input
                            :value="field.key"
                            type="text"
                            required
                            style="font-family:var(--mono,monospace);font-size:12px;"
                            @input="(e: Event) => {
                              const idx = versionFields.indexOf(field)
                              field.key = (e.target as HTMLInputElement).value
                              keyTouchedVersion[idx] = true
                            }"
                          />
                        </label>
                        <!-- Label -->
                        <label :style="field.field_type === 'section' ? 'display:grid;gap:6px;grid-column:1/-1;' : 'display:grid;gap:6px;'">
                          <span>{{ field.field_type === 'section' ? 'Título da seção' : 'Label' }}</span>
                          <input
                            :value="field.label"
                            type="text"
                            required
                            @input="field.label = ($event.target as HTMLInputElement).value"
                          />
                        </label>
                        <!-- Tipo -->
                        <label style="display:grid;gap:6px;">
                          <span>Tipo</span>
                          <select v-model="field.field_type" @change="onVersionFieldTypeChange(field)">
                            <option value="boolean">Sim / Não</option>
                            <option value="text">Texto</option>
                            <option value="number">Número</option>
                            <option value="select">Seleção</option>
                            <option value="date">Data</option>
                            <option value="section">── Seção ──</option>
                          </select>
                        </label>
                        <!-- Obrigatório -->
                        <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;">
                          <span>Obrigatório</span>
                          <select
                            :value="String(field.required)"
                            @change="field.required = ($event.target as HTMLSelectElement).value === 'true'"
                          >
                            <option value="true">Sim</option>
                            <option value="false">Não</option>
                          </select>
                        </label>
                        <!-- Peso (boolean) -->
                        <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
                          <span>Peso</span>
                          <input
                            :value="(field.config_json as Record<string, unknown>).weight ?? 1"
                            type="number" min="0.1" step="0.1"
                            @input="setVersionFieldConfig(field, { weight: parseFloat(($event.target as HTMLInputElement).value) || 1 })"
                          />
                        </label>
                        <!-- Permite N/A (boolean) -->
                        <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
                          <span>Permite N/A</span>
                          <select
                            :value="(field.config_json as Record<string, unknown>).allow_na ? 'true' : 'false'"
                            @change="setVersionFieldConfig(field, { allow_na: ($event.target as HTMLSelectElement).value === 'true' })"
                          >
                            <option value="false">Não</option>
                            <option value="true">Sim</option>
                          </select>
                        </label>
                        <!-- Opções (select) -->
                        <label v-if="field.field_type === 'select'" style="display:grid;gap:6px;grid-column:1/-1;">
                          <span>Opções (separadas por vírgula)</span>
                          <input
                            :value="getVersionOptionsString(field)"
                            type="text"
                            placeholder="Ex: Conforme, Não conforme, Parcial"
                            @input="setVersionOptionsFromString(field, $event)"
                          />
                        </label>
                      </div>
                    </div>
                  </div>
                </template>

                <!-- Add field row -->
                <div class="add-row">
                  <button type="button" class="add-main" @click="addVersionField('boolean')">+ Campo</button>
                  <div class="tchips">
                    <button v-for="[t, l] in Object.entries(FIELD_TYPE_SHORT)" :key="t" type="button" class="tchip" @click="addVersionField(t as FormFieldCreatePayload['field_type'])">{{ l }}</button>
                    <button type="button" class="tchip" @click="addVersionField('section')" style="color:var(--sa-muted);">§ Seção</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <p v-if="versionError" style="font-size:13px;font-weight:600;color:var(--sa-danger);padding:12px 16px;">{{ versionError }}</p>

          <div style="padding:12px 16px;display:flex;gap:8px;flex-wrap:wrap;border-top:1px solid var(--sa-line);">
            <button type="submit" class="btn-primary" :disabled="formsStore.isSaving">
              {{ formsStore.isSaving ? 'Publicando...' : 'Publicar nova versão' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Search bar -->
      <div class="sbar" style="margin-bottom:16px;">
        <SvgIcon name="search" :size="16" style="color:var(--sa-muted);flex-shrink:0;" />
        <input
          v-model="search"
          type="text"
          placeholder="Buscar formulário..."
          style="border:none;outline:none;flex:1;min-width:0;padding:0;box-shadow:none;font-size:14px;background:transparent;"
        />
        <button
          v-if="search"
          type="button"
          style="border:none;background:none;cursor:pointer;padding:0;display:flex;align-items:center;color:var(--sa-muted);"
          @click="search = ''"
        >
          <SvgIcon name="close" :size="15" />
        </button>
      </div>

      <p v-if="formsStore.error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">{{ formsStore.error }}</p>
      <p v-else-if="formsStore.isLoading" style="font-size:13px;color:var(--sa-muted);margin-bottom:12px;">Carregando formulários...</p>

      <!-- Forms list -->
      <div v-if="filteredForms.length" class="lstack">
        <div
          v-for="form in filteredForms"
          :key="form.id"
          class="lrow"
          style="align-items:flex-start;cursor:pointer;"
          @click="router.push({ name: 'form-detail', params: { formId: form.id } })"
        >
          <div class="lrow-main">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;">
              <div class="lrow-title">{{ form.name }}</div>
              <span
                class="status-chip"
                :class="{ 'status-chip--neu': form.current_version_status !== 'published' }"
              >
                {{ form.current_version_status === 'published' ? 'Publicado' : 'Rascunho' }}
              </span>
              <span class="ver-badge">v{{ form.current_version_number }}</span>
            </div>
            <div class="lrow-sub">
              {{ form.description || 'Sem descrição cadastrada.' }}
              · {{ form.published_at ? new Date(form.published_at).toLocaleDateString('pt-BR') : 'Não publicado' }}
            </div>
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0;align-items:center;" @click.stop>
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="openVersionComposer(form.id, form.name)"
            >
              Nova versão
            </button>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="!formsStore.isLoading" class="empty">
        <div class="empty-icon">
          <SvgIcon name="forms" :size="36" />
        </div>
        <div class="empty-h">
          {{ search ? 'Nenhum formulário encontrado' : 'Nenhum formulário cadastrado' }}
        </div>
        <p class="empty-p">
          {{ search ? 'Tente outro termo de busca.' : 'Use o botão acima para criar seu primeiro formulário.' }}
        </p>
      </div>

      <!-- Pagination -->
      <nav
        v-if="formsStore.meta && formsStore.meta.total_pages > 1"
        style="display:flex;align-items:center;justify-content:center;gap:12px;margin-top:16px;"
      >
        <button
          type="button"
          class="btn-secondary btn-sm"
          :disabled="currentPage <= 1 || formsStore.isLoading"
          @click="loadPage(currentPage - 1)"
        >
          ← Anterior
        </button>
        <span style="font-size:13px;color:var(--sa-muted);">
          Página {{ currentPage }} de {{ formsStore.meta.total_pages }}
        </span>
        <button
          type="button"
          class="btn-secondary btn-sm"
          :disabled="!formsStore.meta.has_next || formsStore.isLoading"
          @click="loadPage(currentPage + 1)"
        >
          Próxima →
        </button>
      </nav>

    </div>
  </AppShell>
</template>

<style scoped>
/* ── Two-panel editor ── */
.editor {
  display: flex;
  min-height: 400px;
  max-height: 600px;
  overflow: hidden;
}

/* ── Outline (desktop) ── */
.outline { display: none; }
@media (min-width: 768px) {
  .outline {
    display: flex;
    flex-direction: column;
    width: 216px;
    flex-shrink: 0;
    background: #fff;
    border-right: 1px solid var(--sa-line);
    overflow: hidden;
  }
  .ol-hdr {
    padding: 10px 14px 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: var(--sa-muted);
    border-bottom: 1px solid var(--sa-line);
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }
  .ol-list {
    flex: 1;
    overflow-y: auto;
    padding: 6px;
  }
  .ol-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 10px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    color: var(--sa-muted);
    transition: background .15s, color .15s;
    position: relative;
    border: none;
    background: none;
    font-family: inherit;
    width: 100%;
    text-align: left;
  }
  .ol-item:hover  { background: var(--sa-bg); color: var(--sa-text); }
  .ol-item.active { background: var(--sa-brand-soft, #eff6ff); color: var(--sa-brand); font-weight: 700; }
  .ol-item.active::before {
    content: '';
    position: absolute;
    left: 0; top: 4px; bottom: 4px;
    width: 3px;
    background: var(--sa-brand);
    border-radius: 0 2px 2px 0;
  }
  .ol-cnt {
    margin-left: auto;
    font-size: 10px;
    font-weight: 700;
    background: var(--sa-bg);
    padding: 1px 7px;
    border-radius: 99px;
    color: var(--sa-muted);
    flex-shrink: 0;
    font-family: var(--mono, monospace);
  }
  .ol-add {
    padding: 6px;
    flex-shrink: 0;
    border-top: 1px solid var(--sa-line);
  }
  .ol-add button {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    padding: 8px;
    border: 1px dashed var(--sa-line);
    border-radius: 8px;
    background: none;
    font-size: 12px;
    font-weight: 600;
    color: var(--sa-muted);
    cursor: pointer;
    font-family: inherit;
    transition: border-color .15s, color .15s;
  }
  .ol-add button:hover { border-color: var(--sa-brand); color: var(--sa-brand); }
}

/* ── Fields pane ── */
.fields-pane {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}
.fields-pane::-webkit-scrollbar { width: 4px; }
.fields-pane::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 99px; }
.fields-inner { }

/* ── Toolbar ── */
.toolbar {
  background: #fff;
  border-bottom: 1px solid var(--sa-line);
  padding: 8px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.toolbar::-webkit-scrollbar { display: none; }
.sbar {
  display: flex;
  align-items: center;
  gap: 7px;
  background: var(--sa-bg);
  border: 1px solid var(--sa-line);
  border-radius: 8px;
  padding: 7px 11px;
}
.sbar:focus-within { border-color: var(--sa-brand); background: #fff; box-shadow: 0 0 0 3px rgba(37,99,235,.1); }
@media (min-width: 768px) {
  .toolbar { padding: 8px 20px; overflow-x: visible; }
  .sbar { max-width: 300px; }
}

/* ── Add row ── */
.add-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-bottom: 1px solid var(--sa-line);
  background: #fff;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.add-row::-webkit-scrollbar { display: none; }
.add-main {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 12px;
  border: 1px dashed var(--sa-line);
  border-radius: 8px;
  background: none;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
  flex-shrink: 0;
  transition: border-color .15s, color .15s;
}
.add-main:hover { border-color: var(--sa-brand); color: var(--sa-brand); }
.tchips { display: flex; gap: 4px; flex-shrink: 0; }
.tchip {
  padding: 5px 10px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid var(--sa-line);
  background: #fff;
  color: var(--sa-muted);
  font-family: var(--mono, monospace);
  transition: all .15s;
  white-space: nowrap;
  flex-shrink: 0;
}
.tchip:hover { border-color: var(--sa-brand); color: var(--sa-brand); background: var(--sa-brand-soft, #eff6ff); }

/* ── Compact field rows ── */
.f-wrap { }
.f-wrap.expanded { }

.f-row {
  display: flex;
  align-items: center;
  padding: 0 12px;
  min-height: 48px;
  border-bottom: 1px solid var(--sa-line, #e2e8f0);
  cursor: pointer;
  transition: background .1s;
  user-select: none;
  gap: 0;
  background: #fff;
}
.f-row:hover    { background: #f8fafc; }
.f-row.expanded { background: #eff6ff; border-bottom-color: transparent; }

@media (max-width: 767px) { .f-row { min-height: 52px; } }

.f-drag { color: #cbd5e1; font-size: 16px; cursor: grab; flex-shrink: 0; width: 18px; display: flex; align-items: center; justify-content: center; margin-right: 6px; }
.f-num  { font-family: var(--mono, monospace); font-size: 11px; color: #94a3b8; width: 24px; text-align: right; flex-shrink: 0; margin-right: 8px; }

.f-type { font-family: var(--mono, monospace); font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; flex-shrink: 0; width: 46px; text-align: center; margin-right: 10px; }
.f-type.boolean { background: #eff6ff; color: var(--sa-brand); }
.f-type.text    { background: #f1f5f9; color: #475569; }
.f-type.number  { background: #f0fdf4; color: #15803d; }
.f-type.select  { background: #faf5ff; color: #7c3aed; }
.f-type.date    { background: #fffbeb; color: #b45309; }
.f-type.section { background: #f1f5f9; color: var(--sa-muted); width: auto; }

.f-lbl  { flex: 1; min-width: 0; font-size: 13px; font-weight: 500; color: var(--sa-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-right: 8px; }
.f-key  { font-family: var(--mono, monospace); font-size: 11px; color: var(--sa-muted); background: #f1f5f9; padding: 2px 6px; border-radius: 4px; max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0; margin-right: 6px; }
@media (max-width: 500px) { .f-key { display: none; } }

.f-req  { width: 12px; flex-shrink: 0; margin-right: 6px; display: flex; align-items: center; justify-content: center; }
.f-rdot { width: 6px; height: 6px; border-radius: 50%; background: var(--sa-danger); }
.f-wt   { font-family: var(--mono, monospace); font-size: 11px; color: #94a3b8; width: 28px; text-align: right; flex-shrink: 0; margin-right: 4px; }
.f-arr  { font-size: 13px; color: var(--sa-muted); flex-shrink: 0; transition: transform .2s; width: 18px; text-align: center; }
.f-row.expanded .f-arr { transform: rotate(90deg); }

.f-chk { width: 22px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.f-chk input[type=checkbox] { width: 16px; height: 16px; cursor: pointer; accent-color: var(--sa-brand); }

/* ── Config panel ── */
.f-cfg {
  display: none;
  background: #f8fafc;
  border-bottom: 1px solid #bfdbfe;
  padding: 14px 16px;
}
.f-cfg.open { display: block; }

@media (min-width: 768px) {
  .f-cfg { padding: 14px 16px 14px 88px; }
}

/* ── Section header (sticky) ── */
.sec-hdr {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--sa-bg, #f1f5f9);
  border-top: 1px solid var(--sa-line, #e2e8f0);
  border-bottom: 1px solid var(--sa-line, #e2e8f0);
  padding: 7px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.sec-toggle {
  font-size: 11px;
  color: var(--sa-muted);
  transition: transform .2s;
  flex-shrink: 0;
}
.sec-toggle.coll { transform: rotate(-90deg); }
.sec-name {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--sa-muted);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sec-count {
  font-size: 10px;
  font-weight: 700;
  color: var(--sa-muted);
  background: var(--sa-line, #e2e8f0);
  padding: 2px 8px;
  border-radius: 99px;
  flex-shrink: 0;
}

/* ── Bulk bar ── */
.bulk-bar {
  background: var(--sa-brand-soft, #eff6ff);
  border-bottom: 1px solid #bfdbfe;
  padding: 8px 16px;
  display: none;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  overflow-x: auto;
}
.bulk-bar.on { display: flex; }
.bulk-info { font-size: 13px; font-weight: 600; color: var(--sa-brand); white-space: nowrap; }

/* ── Buttons ── */
.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  color: var(--sa-muted);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  padding: 5px 8px;
  border-radius: 6px;
  transition: background .15s, color .15s;
}
.btn-ghost:hover { background: var(--sa-bg); color: var(--sa-text); }
.btn-danger {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  color: var(--sa-danger);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  padding: 5px 8px;
  border-radius: 6px;
}
.btn-danger:hover { background: #fef2f2; }
</style>
