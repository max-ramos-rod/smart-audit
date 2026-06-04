<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchForm } from '@/services/forms.service'
import { fetchSubmissions } from '@/services/submissions.service'
import { useFormsStore } from '@/stores/forms/forms.store'
import type { FormDetail, FormFieldCreatePayload } from '@/types/forms'
import type { SubmissionListItem } from '@/types/submissions'

const route  = useRoute()
const router = useRouter()
const formsStore = useFormsStore()
const formId = computed(() => route.params.formId as string)

const formDetail            = ref<FormDetail | null>(null)
const isLoading             = ref(true)
const recentSubmissions     = ref<SubmissionListItem[]>([])
const isLoadingSubmissions  = ref(false)

const showVersionComposer = ref(false)
const versionError        = ref<string | null>(null)
const versionFields       = ref<FormFieldCreatePayload[]>([])

// ── B5/B6: expand state ──
const expandedDetailIndex = ref<number | null>(null)

// ── B7: key-touched tracking ──
const keyTouchedDetail = reactive<Record<number, boolean>>({})

// ── B8: collapsed sections ──
const collapsedSectionsDetail = reactive<Set<number>>(new Set())

// ── B9: bulk selection ──
const selectModeDetail  = ref(false)
const selectedDetail    = reactive<Set<number>>(new Set())

// ── Search/filter for version composer ──
const detailSearchQuery = ref('')
const detailTypeFilter  = ref('')

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não', text: 'Texto', number: 'Número',
  date: 'Data', select: 'Seleção', section: 'Seção',
}
const TYPE_COLOR: Record<string, string> = {
  boolean: 'var(--sa-brand)', text: 'var(--sa-muted)', number: 'var(--sa-ok)',
  date: 'var(--sa-warn)', select: 'var(--sa-muted)',
}

const FIELD_TYPE_SHORT: Record<string, string> = {
  boolean: 'S/N', text: 'TXT', number: 'NUM', date: 'DAT', select: 'SEL',
}

const filteredDetailFields = computed(() => {
  const q = detailSearchQuery.value.toLowerCase().trim()
  const t = detailTypeFilter.value
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

// ── B7: watcher ──
watch(
  () => versionFields.value.map((f, i) => ({ label: f.label, key: f.key, i })),
  (curr, prev) => {
    if (!prev) return
    curr.forEach(({ label, key, i }) => {
      if (label !== prev[i]?.label && !keyTouchedDetail[i]) {
        if (versionFields.value[i]?.field_type !== 'section') {
          versionFields.value[i].key = toFieldSlug(label)
        }
      }
      if (key !== prev[i]?.key && key !== toFieldSlug(label)) {
        keyTouchedDetail[i] = true
      }
    })
  },
)

// ── B5/B6: toggle expand ──
function toggleDetailExpand(i: number) {
  expandedDetailIndex.value = expandedDetailIndex.value === i ? null : i
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
function bulkDeleteDetail() {
  const indices = [...selectedDetail].sort((a, b) => b - a)
  for (const i of indices) {
    versionFields.value.splice(i, 1)
  }
  versionFields.value.forEach((f, i) => { f.position = i + 1 })
  selectedDetail.clear()
  selectModeDetail.value = false
}

onMounted(async () => {
  try {
    formDetail.value = await fetchForm(formId.value)
  } finally {
    isLoading.value = false
  }
  isLoadingSubmissions.value = true
  try {
    const res = await fetchSubmissions(1, 5, undefined, formId.value)
    recentSubmissions.value = res.data
  } finally {
    isLoadingSubmissions.value = false
  }
})

function statusLabel(status: string) {
  const map: Record<string, string> = {
    in_progress: 'Em andamento', completed: 'Concluída',
    draft: 'Rascunho', cancelled: 'Cancelada',
  }
  return map[status] ?? status
}

function createEmptyField(position: number): FormFieldCreatePayload {
  return { key: '', label: '', field_type: 'boolean', required: false, position, config_json: {} }
}

function setDetailFieldConfig(field: FormFieldCreatePayload, patch: Record<string, unknown>) {
  field.config_json = { ...(field.config_json as Record<string, unknown>), ...patch }
}

function getDetailOptionsString(field: FormFieldCreatePayload): string {
  return Array.isArray(field.config_json.options)
    ? (field.config_json.options as string[]).join(', ')
    : ''
}

function setDetailOptionsFromString(field: FormFieldCreatePayload, event: Event) {
  const opts = (event.target as HTMLInputElement).value
    .split(',').map(o => o.trim()).filter(Boolean)
  field.config_json = opts.length ? { options: opts } : {}
}

function onDetailFieldTypeChange(field: FormFieldCreatePayload) {
  if (field.field_type === 'section') {
    field.config_json = {}
    field.required = false
  } else {
    field.config_json = {}
  }
}

function openVersionComposer() {
  if (!formDetail.value) return
  versionFields.value = formDetail.value.current_version.fields.map(f => ({
    key: f.key, label: f.label, field_type: f.field_type,
    required: f.required, position: f.position, config_json: f.config_json,
  }))
  versionError.value = null
  expandedDetailIndex.value = null
  selectedDetail.clear()
  selectModeDetail.value = false
  Object.keys(keyTouchedDetail).forEach(k => delete (keyTouchedDetail as Record<string, boolean>)[k])
  collapsedSectionsDetail.clear()
  detailSearchQuery.value = ''
  detailTypeFilter.value = ''
  showVersionComposer.value = true
}

function addVersionField(fieldType: FormFieldCreatePayload['field_type'] = 'boolean') {
  const newField = createEmptyField(versionFields.value.length + 1)
  newField.field_type = fieldType
  if (fieldType === 'section') { newField.key = `__section_${versionFields.value.length + 1}__`; newField.required = false }
  versionFields.value.push(newField)
  expandedDetailIndex.value = versionFields.value.length - 1
}

function removeVersionField(index: number) {
  if (versionFields.value.length === 1) return
  versionFields.value.splice(index, 1)
  versionFields.value.forEach((f, i) => { f.position = i + 1 })
  if (expandedDetailIndex.value === index) expandedDetailIndex.value = null
  else if (expandedDetailIndex.value !== null && expandedDetailIndex.value > index) expandedDetailIndex.value--
}

async function submitVersion() {
  versionError.value = null
  try {
    await formsStore.publishVersion(formId.value, {
      fields: versionFields.value.map((f, i) => ({
        ...f,
        position: i + 1,
        key: f.field_type === 'section' ? `__section_${i + 1}__` : f.key,
        required: f.field_type === 'section' ? false : f.required,
      })),
    })
    formDetail.value = await fetchForm(formId.value)
    showVersionComposer.value = false
    expandedDetailIndex.value = null
    selectedDetail.clear()
    selectModeDetail.value = false
    collapsedSectionsDetail.clear()
  } catch (err: any) {
    versionError.value = extractProblemMessage(err, 'Não foi possível publicar a nova versão.')
  }
}
</script>

<template>
  <AppShell>
    <div class="page">

      <div v-if="isLoading" style="font-size:13px;color:var(--sa-muted);">Carregando...</div>

      <template v-else-if="formDetail">

        <!-- Back header -->
        <div class="back-hdr">
          <button type="button" class="back-btn" @click="router.push({ name: 'forms' })">
            <SvgIcon name="back" :size="16" />
          </button>
          <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
              <h1 style="font-size:18px;font-weight:700;letter-spacing:-.01em;color:var(--sa-text);">
                {{ formDetail.name }}
              </h1>
              <span
                class="status-chip"
                :class="{ 'status-chip--neu': formDetail.current_version.status !== 'published' }"
              >
                {{ formDetail.current_version.status === 'published' ? 'Publicado' : 'Rascunho' }}
              </span>
            </div>
            <div style="font-size:12px;color:var(--sa-muted);margin-top:2px;">
              v{{ formDetail.current_version.version }}
              <template v-if="formDetail.current_version.published_at">
                · publicado {{ new Date(formDetail.current_version.published_at).toLocaleDateString('pt-BR') }}
              </template>
            </div>
          </div>
          <div style="flex-shrink:0;display:flex;gap:8px;">
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="router.push({ name: 'form-versions', params: { formId } })"
            >
              Histórico
            </button>
            <button type="button" class="btn-primary btn-sm" @click="openVersionComposer">
              Nova versão
            </button>
          </div>
        </div>

        <!-- Stats -->
        <div class="stats-grid" style="margin-bottom:20px;">
          <div class="scard">
            <div class="sc-label">Campos</div>
            <div class="sc-value">{{ formDetail.current_version.fields.length }}</div>
          </div>
          <div class="scard sc-accent">
            <div class="sc-label">Versão atual</div>
            <div class="sc-value">v{{ formDetail.current_version.version }}</div>
          </div>
          <div class="scard">
            <div class="sc-label">Status</div>
            <div class="sc-value" style="font-size:16px;">
              {{ formDetail.current_version.status === 'published' ? 'Publicado' : 'Rascunho' }}
            </div>
          </div>
          <div class="scard">
            <div class="sc-label">Publicado em</div>
            <div style="font-size:16px;font-weight:700;color:var(--sa-text);margin-top:4px;">
              {{ formDetail.current_version.published_at
                ? new Date(formDetail.current_version.published_at).toLocaleDateString('pt-BR')
                : '—' }}
            </div>
          </div>
        </div>

        <!-- Description -->
        <div v-if="formDetail.description" class="info-box" style="margin-bottom:16px;">
          {{ formDetail.description }}
        </div>

        <!-- ══ VERSION COMPOSER ══ -->
        <div v-if="showVersionComposer" class="card" style="margin-bottom:20px;overflow:hidden;">
          <div style="padding:16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--sa-line);">
            <div>
              <div class="eyebrow">Nova versão</div>
              <div style="font-size:17px;font-weight:700;color:var(--sa-text);margin-top:3px;">{{ formDetail.name }}</div>
              <div style="font-size:12px;color:var(--sa-muted);margin-top:4px;">
                Edite os campos. Uma nova versão será publicada sem alterar inspeções anteriores.
              </div>
            </div>
            <button type="button" class="btn-secondary btn-sm" @click="showVersionComposer = false">Fechar</button>
          </div>

          <form @submit.prevent="submitVersion">
            <!-- Bulk bar -->
            <div class="bulk-bar" :class="{ on: selectModeDetail && selectedDetail.size > 0 }">
              <span class="bulk-info">{{ selectedDetail.size }} campo(s) selecionado(s)</span>
              <button type="button" class="btn-danger" @click="bulkDeleteDetail">Remover</button>
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
                    :class="{ active: expandedDetailIndex === i }"
                    @click="toggleDetailExpand(i)"
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
                    <input v-model="detailSearchQuery" type="text" placeholder="Buscar campo…" style="border:none;background:none;outline:none;font-size:13px;color:var(--sa-text);font-family:inherit;flex:1;min-width:0;" />
                  </div>
                  <select v-model="detailTypeFilter" style="font-family:inherit;font-size:12px;font-weight:600;padding:6px 10px;border:1px solid var(--sa-line);border-radius:8px;background:#fff;color:var(--sa-muted);cursor:pointer;outline:none;flex-shrink:0;">
                    <option value="">Tipo: Todos</option>
                    <option value="boolean">Sim/Não</option>
                    <option value="text">Texto</option>
                    <option value="number">Número</option>
                    <option value="select">Seleção</option>
                    <option value="date">Data</option>
                  </select>
                  <button type="button" class="btn-ghost" style="flex-shrink:0;" @click="selectModeDetail = !selectModeDetail; selectedDetail.clear()">
                    {{ selectModeDetail ? 'Cancelar' : 'Selecionar' }}
                  </button>
                  <span style="font-family:var(--mono,monospace);font-size:11px;color:var(--sa-muted);margin-left:auto;white-space:nowrap;flex-shrink:0;">{{ filteredDetailFields.length }} campo(s)</span>
                </div>

                <!-- Field rows -->
                <div class="fields-inner">
                  <template v-for="field in filteredDetailFields" :key="versionFields.indexOf(field)">
                    <div
                      v-show="!isFieldHidden(versionFields, versionFields.indexOf(field), collapsedSectionsDetail)"
                      class="f-wrap"
                      :class="{ expanded: expandedDetailIndex === versionFields.indexOf(field) }"
                    >
                      <!-- Compact row -->
                      <div
                        class="f-row"
                        :class="{ expanded: expandedDetailIndex === versionFields.indexOf(field) }"
                        @click="toggleDetailExpand(versionFields.indexOf(field))"
                      >
                        <!-- Section row -->
                        <template v-if="field.field_type === 'section'">
                          <label v-if="selectModeDetail" class="f-chk" @click.stop>
                            <input
                              type="checkbox"
                              :checked="selectedDetail.has(versionFields.indexOf(field))"
                              @change="(e: Event) => {
                                const idx = versionFields.indexOf(field)
                                if ((e.target as HTMLInputElement).checked) selectedDetail.add(idx)
                                else selectedDetail.delete(idx)
                              }"
                            />
                          </label>
                          <span
                            class="sec-toggle"
                            :class="{ coll: collapsedSectionsDetail.has(versionFields.indexOf(field)) }"
                            @click.stop="toggleSectionCollapse(collapsedSectionsDetail, versionFields.indexOf(field))"
                          >▶</span>
                          <span class="f-num" style="opacity:.4;">§</span>
                          <span class="f-type section" style="font-size:9px;">SEÇÃO</span>
                          <span class="f-lbl" style="font-weight:700;">{{ field.label || 'Seção sem nome' }}</span>
                          <span class="f-arr">›</span>
                        </template>
                        <!-- Regular field row -->
                        <template v-else>
                          <label v-if="selectModeDetail" class="f-chk" @click.stop>
                            <input
                              type="checkbox"
                              :checked="selectedDetail.has(versionFields.indexOf(field))"
                              @change="(e: Event) => {
                                const idx = versionFields.indexOf(field)
                                if ((e.target as HTMLInputElement).checked) selectedDetail.add(idx)
                                else selectedDetail.delete(idx)
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
                      <div v-show="expandedDetailIndex === versionFields.indexOf(field)" class="f-cfg open">
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
                                keyTouchedDetail[idx] = true
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
                            <select v-model="field.field_type" @change="onDetailFieldTypeChange(field)">
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
                              @input="setDetailFieldConfig(field, { weight: parseFloat(($event.target as HTMLInputElement).value) || 1 })"
                            />
                          </label>
                          <!-- Permite N/A (boolean) -->
                          <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
                            <span>Permite N/A</span>
                            <select
                              :value="(field.config_json as Record<string, unknown>).allow_na ? 'true' : 'false'"
                              @change="setDetailFieldConfig(field, { allow_na: ($event.target as HTMLSelectElement).value === 'true' })"
                            >
                              <option value="false">Não</option>
                              <option value="true">Sim</option>
                            </select>
                          </label>
                          <!-- Opções (select) -->
                          <label v-if="field.field_type === 'select'" style="display:grid;gap:6px;grid-column:1/-1;">
                            <span>Opções (separadas por vírgula)</span>
                            <input
                              :value="getDetailOptionsString(field)"
                              type="text"
                              placeholder="Ex: Conforme, Não conforme, Parcial"
                              @input="setDetailOptionsFromString(field, $event)"
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

        <!-- Fields list (read-only, current version) -->
        <div class="slabel" style="margin-bottom:10px;">
          Campos da versão atual (v{{ formDetail.current_version.version }})
        </div>
        <div class="fpanel">
          <template v-for="(field, i) in formDetail.current_version.fields" :key="field.id">
            <!-- Section divider -->
            <div v-if="field.field_type === 'section'" class="section-divider">
              <span>{{ field.label }}</span>
            </div>

            <!-- Regular field row -->
            <div
              v-else
              class="frow"
              style="display:flex;align-items:flex-start;gap:12px;"
            >
              <!-- Type icon -->
              <div :style="{
                width: '22px', height: '22px', borderRadius: '6px', flexShrink: 0, marginTop: '2px',
                background: (TYPE_COLOR[field.field_type] ?? 'var(--sa-muted)') + '18',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }">
                <span :style="{
                  fontSize: '9px', fontWeight: 800,
                  color: TYPE_COLOR[field.field_type] ?? 'var(--sa-muted)',
                  letterSpacing: '.04em',
                }">
                  {{ (TYPE_LABEL[field.field_type] ?? field.field_type).slice(0, 3).toUpperCase() }}
                </span>
              </div>

              <!-- Info -->
              <div style="flex:1;min-width:0;">
                <div class="frow-type">
                  {{ TYPE_LABEL[field.field_type] ?? field.field_type }}{{ field.required ? ' · Obrigatório' : '' }}
                </div>
                <div style="font-size:13px;font-weight:600;color:var(--sa-text);margin-top:2px;">{{ field.label }}</div>
                <div style="font-size:11px;color:var(--sa-muted);font-family:'DM Mono',monospace;margin-top:2px;">{{ field.key }}</div>
              </div>

              <!-- Position badge -->
              <span :style="{
                fontSize: '10px', fontWeight: 700, padding: '2px 6px', borderRadius: '4px',
                background: (TYPE_COLOR[field.field_type] ?? 'var(--sa-muted)') + '15',
                color: TYPE_COLOR[field.field_type] ?? 'var(--sa-muted)',
                flexShrink: 0, textTransform: 'uppercase', letterSpacing: '.06em',
              }">{{ i + 1 }}</span>
            </div>
          </template>
        </div>

        <!-- Recent submissions -->
        <div style="margin-top:24px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
            <div class="slabel" style="margin-bottom:0;">Inspeções recentes</div>
            <button
              type="button"
              style="border:none;background:none;cursor:pointer;font-size:12px;font-weight:600;color:var(--sa-brand);font-family:inherit;padding:0;"
              @click="router.push({ name: 'submissions' })"
            >
              Ver todas →
            </button>
          </div>

          <div v-if="isLoadingSubmissions" style="font-size:13px;color:var(--sa-muted);padding:12px 0;">
            Carregando inspeções...
          </div>

          <div v-else-if="recentSubmissions.length" class="lstack">
            <div
              v-for="sub in recentSubmissions"
              :key="sub.id"
              class="lrow"
              @click="router.push({ name: 'submission-detail', params: { id: sub.id } })"
            >
              <div class="lrow-main">
                <div class="lrow-title">
                  {{ new Date(sub.started_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) }}
                </div>
                <div class="lrow-sub">
                  {{ sub.finished_at
                    ? 'Concluída ' + new Date(sub.finished_at).toLocaleDateString('pt-BR')
                    : 'Em andamento' }}
                </div>
              </div>
              <div class="lrow-end">
                <span
                  v-if="sub.score !== null"
                  class="score-val"
                  :class="sub.score >= 85 ? 'ok' : sub.score >= 65 ? 'warn' : 'err'"
                >
                  {{ sub.score }}%
                </span>
                <span
                  class="status-chip"
                  :class="{
                    'status-chip--warn': sub.status === 'in_progress',
                    'status-chip--inactive': sub.status === 'cancelled',
                    'status-chip--neu': sub.status === 'draft',
                  }"
                >
                  {{ statusLabel(sub.status) }}
                </span>
              </div>
            </div>
          </div>

          <div v-else class="info-box" style="font-size:12px;">
            Nenhuma inspeção realizada com este formulário ainda.
          </div>
        </div>

      </template>

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

/* ── Section header ── */
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
