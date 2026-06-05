<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import FormFieldEditor from '@/components/forms/FormFieldEditor.vue'
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

const versionError = ref<string | null>(null)
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

// ── Search/filter ──
const detailSearchQuery = ref('')
const detailTypeFilter  = ref('')

// ── Outline active section ──
const activeSec = ref<string>('')

const FIELD_TYPE_SHORT: Record<string, string> = {
  boolean: 'S/N', text: 'TXT', number: 'NUM', date: 'DAT', select: 'SEL',
}

const quickTypes = [
  { type: 'boolean', label: 'S/N' },
  { type: 'text',    label: 'TXT' },
  { type: 'number',  label: 'NUM' },
  { type: 'select',  label: 'SEL' },
  { type: 'date',    label: 'DAT' },
] as const

// ── Computed: sections from versionFields ──
interface SectionGroup {
  key: string
  label: string
  sectionIndex: number   // index of the section field in versionFields
  fieldCount: number
}

const sections = computed<SectionGroup[]>(() => {
  const result: SectionGroup[] = []
  versionFields.value.forEach((f, i) => {
    if (f.field_type === 'section') {
      const count = versionFields.value.slice(i + 1).findIndex(ff => ff.field_type === 'section')
      const fieldCount = count === -1 ? versionFields.value.length - i - 1 : count
      result.push({ key: f.key || `__section_${i}__`, label: f.label || 'Seção sem nome', sectionIndex: i, fieldCount })
    }
  })
  return result
})

// Fields with no preceding section (before first section header)
const hasAnySections = computed(() => sections.value.length > 0)

// Filtered fields
const filteredDetailFields = computed(() => {
  const q = detailSearchQuery.value.toLowerCase().trim()
  const t = detailTypeFilter.value
  return versionFields.value.filter((f) => {
    const matchType = !t || f.field_type === t
    const matchQ = !q || f.label.toLowerCase().includes(q) || f.key.toLowerCase().includes(q)
    return matchType && matchQ
  })
})

// Count labels
const fieldCount = computed(() => versionFields.value.filter(f => f.field_type !== 'section').length)
const sectionCount = computed(() => versionFields.value.filter(f => f.field_type === 'section').length)

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
  const wasOpen = expandedDetailIndex.value === i
  expandedDetailIndex.value = wasOpen ? null : i
  if (!wasOpen) {
    scrollToField(i)
  }
}

// Scroll to field — NEVER use scrollIntoView
function scrollToField(index: number) {
  const el = document.getElementById(`fd-field-${index}`)
  const container = document.getElementById('fd-field-list')
  if (el && container) {
    container.scrollTo({ top: el.offsetTop - 60, behavior: 'smooth' })
  }
}

// ── B8: section collapse ──
function toggleSectionCollapse(sectionIndex: number) {
  if (collapsedSectionsDetail.has(sectionIndex)) collapsedSectionsDetail.delete(sectionIndex)
  else collapsedSectionsDetail.add(sectionIndex)
}

function isFieldHidden(fieldIndex: number): boolean {
  for (let i = fieldIndex - 1; i >= 0; i--) {
    if (versionFields.value[i].field_type === 'section') {
      return collapsedSectionsDetail.has(i)
    }
  }
  return false
}

// ── Section rename/remove ──
function renameSection(sectionIndex: number) {
  const field = versionFields.value[sectionIndex]
  if (!field) return
  const newLabel = window.prompt('Novo nome da seção:', field.label)
  if (newLabel !== null && newLabel.trim()) {
    field.label = newLabel.trim()
  }
}

function removeSection(sectionIndex: number) {
  if (!window.confirm('Remover esta seção? Os campos dentro dela também serão removidos.')) return
  // Find end of section
  let end = versionFields.value.length
  for (let i = sectionIndex + 1; i < versionFields.value.length; i++) {
    if (versionFields.value[i].field_type === 'section') { end = i; break }
  }
  versionFields.value.splice(sectionIndex, end - sectionIndex)
  versionFields.value.forEach((f, i) => { f.position = i + 1 })
  if (expandedDetailIndex.value !== null && expandedDetailIndex.value >= sectionIndex) {
    expandedDetailIndex.value = null
  }
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

// ── Jump to section (outline click) ──
function jumpToSection(sectionKey: string) {
  activeSec.value = sectionKey
  const sg = document.getElementById(`sg-${sectionKey}`)
  const container = document.getElementById('fd-field-list')
  if (sg && container) {
    container.scrollTo({ top: sg.offsetTop - 4, behavior: 'smooth' })
    // Expand section if collapsed
    const idx = versionFields.value.findIndex(f => f.field_type === 'section' && (f.key || `__section_${versionFields.value.indexOf(f)}__`) === sectionKey)
    if (idx !== -1 && collapsedSectionsDetail.has(idx)) {
      collapsedSectionsDetail.delete(idx)
    }
  }
}

// ── Outline scroll sync ──
function setupOutlineScrollSync() {
  const fieldListEl = document.getElementById('fd-field-list')
  if (fieldListEl) {
    fieldListEl.addEventListener('scroll', () => {
      const paneTop = fieldListEl.getBoundingClientRect().top
      for (const sec of sections.value) {
        const el = document.getElementById(`sg-${sec.key}`)
        if (el && el.getBoundingClientRect().top - paneTop < 60) {
          activeSec.value = sec.key
        }
      }
    })
    // Set initial active
    if (sections.value.length > 0) activeSec.value = sections.value[0].key
  }
}

onMounted(async () => {
  try {
    formDetail.value = await fetchForm(formId.value)
    // Auto-open composer with current version fields
    openVersionComposer()
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

// ── Helper: weight display (avoids `as number` cast in template) ──
function weightDisplay(field: FormFieldCreatePayload): string {
  const w = (field.config_json as Record<string, unknown>)?.weight
  return typeof w === 'number' && w > 1 ? '×' + w : ''
}

// ── Helper: toggle checkbox selection for a field index ──
function toggleFieldSelection(e: Event, fieldIdx: number) {
  if ((e.target as HTMLInputElement).checked) selectedDetail.add(fieldIdx)
  else selectedDetail.delete(fieldIdx)
}

function createEmptyField(position: number): FormFieldCreatePayload {
  return { key: '', label: '', field_type: 'boolean', required: false, position, config_json: {} }
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
  // Setup scroll sync after DOM update
  setTimeout(() => setupOutlineScrollSync(), 100)
}

// ── Add field ──
function addVersionField(fieldType: FormFieldCreatePayload['field_type'] = 'boolean', afterSectionIndex?: number) {
  const newField = createEmptyField(versionFields.value.length + 1)
  newField.field_type = fieldType
  if (fieldType === 'section') {
    newField.key = `__section_${versionFields.value.length + 1}__`
    newField.required = false
    versionFields.value.push(newField)
    expandedDetailIndex.value = versionFields.value.length - 1
    return
  }

  if (afterSectionIndex !== undefined) {
    // Insert after the last field of this section
    let insertAt = afterSectionIndex + 1
    for (let i = afterSectionIndex + 1; i < versionFields.value.length; i++) {
      if (versionFields.value[i].field_type === 'section') break
      insertAt = i + 1
    }
    versionFields.value.splice(insertAt, 0, newField)
    versionFields.value.forEach((f, i) => { f.position = i + 1 })
    expandedDetailIndex.value = insertAt
  } else {
    versionFields.value.push(newField)
    expandedDetailIndex.value = versionFields.value.length - 1
  }
}

// ── Add section ──
function addSection() {
  const newSection = createEmptyField(versionFields.value.length + 1)
  newSection.field_type = 'section'
  newSection.key = `__section_${versionFields.value.length + 1}__`
  newSection.required = false
  versionFields.value.push(newSection)
  versionFields.value.forEach((f, i) => { f.position = i + 1 })
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
    expandedDetailIndex.value = null
    selectedDetail.clear()
    selectModeDetail.value = false
    collapsedSectionsDetail.clear()
    // Reload fields after publish
    openVersionComposer()
  } catch (err: any) {
    versionError.value = extractProblemMessage(err, 'Não foi possível publicar a nova versão.')
  }
}
</script>

<template>
  <AppShell>
    <div v-if="isLoading" style="padding:24px;font-size:13px;color:var(--sa-muted);">Carregando...</div>

    <template v-else-if="formDetail">
      <!-- ══ FULL-HEIGHT EDITOR SHELL ══ -->
      <div class="fd-shell">

        <!-- ── TOP BAR ── -->
        <div class="fd-topbar">
          <button type="button" class="fd-tb-back" @click="router.push({ name: 'forms' })">
            <SvgIcon name="back" :size="16" />
          </button>
          <div class="fd-tb-name">{{ formDetail.name }}</div>
          <span class="fd-ver-badge">v{{ formDetail.current_version.version }}</span>
          <span
            class="fd-status-chip"
            :class="{ 'fd-status-chip--draft': formDetail.current_version.status !== 'published' }"
          >
            {{ formDetail.current_version.status === 'published' ? 'Publicado' : 'Rascunho' }}
          </span>
          <div class="fd-topbar-actions">
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="router.push({ name: 'form-versions', params: { formId } })"
            >
              Histórico
            </button>
            <button
              type="button"
              class="btn-primary btn-sm"
              :disabled="formsStore.isSaving"
              @click="submitVersion"
            >
              {{ formsStore.isSaving ? 'Publicando...' : 'Publicar versão' }}
            </button>
          </div>
        </div>

        <!-- ── TOOLBAR ── -->
        <div class="fd-toolbar">
          <div class="fd-sbar">
            <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24" style="color:var(--sa-muted);flex-shrink:0;"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
            <input
              v-model="detailSearchQuery"
              type="text"
              placeholder="Buscar campo…"
              style="border:none;background:none;outline:none;font-size:13px;color:var(--sa-text);font-family:inherit;flex:1;min-width:0;"
            />
          </div>
          <select
            v-model="detailTypeFilter"
            style="font-family:inherit;font-size:12px;font-weight:600;padding:6px 10px;border:1px solid var(--sa-line);border-radius:8px;background:#fff;color:var(--sa-muted);cursor:pointer;outline:none;flex-shrink:0;"
          >
            <option value="">Tipo: Todos</option>
            <option value="boolean">Sim/Não</option>
            <option value="text">Texto</option>
            <option value="number">Número</option>
            <option value="select">Seleção</option>
            <option value="date">Data</option>
          </select>
          <button
            type="button"
            class="btn-ghost"
            style="flex-shrink:0;"
            @click="selectModeDetail = !selectModeDetail; selectedDetail.clear()"
          >
            {{ selectModeDetail ? '✕ Cancelar' : '☐ Selecionar' }}
          </button>
          <span style="font-family:var(--mono,monospace);font-size:11px;color:var(--sa-muted);margin-left:auto;white-space:nowrap;flex-shrink:0;">
            {{ fieldCount }} campo{{ fieldCount !== 1 ? 's' : '' }}
            <template v-if="sectionCount > 0"> · {{ sectionCount }} seção{{ sectionCount !== 1 ? 'ões' : '' }}</template>
          </span>
          <button type="button" class="btn-secondary btn-sm" style="flex-shrink:0;" @click="addSection">
            + Seção
          </button>
        </div>

        <!-- ── SECTION CHIPS (mobile) ── -->
        <div v-if="hasAnySections" class="fd-sec-chips-bar">
          <button
            v-for="sec in sections"
            :key="sec.key"
            class="fd-sec-chip"
            :class="{ active: activeSec === sec.key }"
            @click="jumpToSection(sec.key)"
          >
            {{ sec.label }}
          </button>
        </div>

        <!-- ── BULK BAR ── -->
        <div class="fd-bulk-bar" :class="{ on: selectModeDetail && selectedDetail.size > 0 }">
          <span class="fd-bulk-info">{{ selectedDetail.size }} campo(s) selecionado(s)</span>
          <button type="button" class="btn-danger btn-sm" @click="bulkDeleteDetail">Remover</button>
          <button type="button" class="btn-ghost btn-sm" style="margin-left:auto;" @click="selectedDetail.clear(); selectModeDetail = false">✕</button>
        </div>

        <!-- ── EDITOR (outline + field list) ── -->
        <div class="fd-editor">

          <!-- Outline (desktop ≥768px) -->
          <aside class="fd-outline">
            <div class="fd-ol-hdr">
              <span>Seções</span>
              <span style="font-size:10px;font-weight:400;text-transform:none;letter-spacing:0;color:#94a3b8;">{{ sections.length }}</span>
            </div>
            <div class="fd-ol-list">
              <button
                v-for="sec in sections"
                :key="sec.key"
                type="button"
                class="fd-outline-sec"
                :class="{ active: activeSec === sec.key }"
                @click="jumpToSection(sec.key)"
              >
                <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ sec.label }}</span>
                <span class="fd-ol-cnt">{{ sec.fieldCount }}</span>
              </button>
              <div v-if="sections.length === 0" style="padding:12px;font-size:12px;color:var(--sa-muted);text-align:center;">
                Sem seções
              </div>
            </div>
            <div class="fd-ol-add">
              <button type="button" @click="addSection">+ Nova seção</button>
            </div>
          </aside>

          <!-- Field list -->
          <form id="fd-field-list" class="fd-field-list" @submit.prevent="submitVersion">

            <template v-if="versionFields.length === 0">
              <div style="padding:32px;text-align:center;font-size:13px;color:var(--sa-muted);">
                Nenhum campo ainda. Clique em <strong>+ Seção</strong> ou use o outline para começar.
              </div>
            </template>

            <template v-else>
              <!-- Render by sections if any, otherwise flat list -->
              <template v-if="hasAnySections">
                <!-- Fields before first section (orphan fields) -->
                <div
                  v-for="(field, fieldIdx) in versionFields"
                  v-show="fieldIdx < (sections[0]?.sectionIndex ?? versionFields.length) && field.field_type !== 'section' && filteredDetailFields.includes(field)"
                  :key="`orphan-${fieldIdx}`"
                  :id="`fd-field-${fieldIdx}`"
                >
                  <div
                    class="fd-field-row"
                    :class="{ expanded: expandedDetailIndex === fieldIdx }"
                    @click="toggleDetailExpand(fieldIdx)"
                  >
                    <label v-if="selectModeDetail" class="f-chk" @click.stop>
                      <input
                        type="checkbox"
                        :checked="selectedDetail.has(fieldIdx)"
                        @change="toggleFieldSelection($event, fieldIdx)"
                      />
                    </label>
                    <span class="f-drag" title="Arrastar">⠿</span>
                    <span class="f-num">{{ String(fieldIdx + 1).padStart(2, '0') }}</span>
                    <span class="f-type" :class="field.field_type">
                      {{ FIELD_TYPE_SHORT[field.field_type] ?? field.field_type.toUpperCase().slice(0, 3) }}
                    </span>
                    <span class="f-lbl">{{ field.label || '(sem nome)' }}</span>
                    <span class="f-key">{{ field.key || '—' }}</span>
                    <span class="f-req">
                      <span v-if="field.required" class="f-rdot" title="Obrigatório"></span>
                    </span>
                    <span class="f-wt">{{ weightDisplay(field) }}</span>
                    <span class="f-arr">›</span>
                  </div>
                  <div v-show="expandedDetailIndex === fieldIdx">
                    <FormFieldEditor
                      v-model="versionFields[fieldIdx]"
                      :index="fieldIdx"
                      :show-remove="versionFields.length > 1"
                      mode="inline"
                      @remove="removeVersionField(fieldIdx)"
                    />
                  </div>
                </div>

                <!-- Section groups -->
                <div
                  v-for="(sec, secIdx) in sections"
                  :key="sec.key"
                  :id="`sg-${sec.key}`"
                >
                  <!-- Section header sticky -->
                  <div class="fd-sec-hdr">
                    <button
                      type="button"
                      class="fd-sec-toggle"
                      @click="toggleSectionCollapse(sec.sectionIndex)"
                    >
                      {{ collapsedSectionsDetail.has(sec.sectionIndex) ? '›' : '▾' }}
                      {{ sec.label }}
                      <span class="fd-sec-cnt">{{ sec.fieldCount }}</span>
                    </button>
                    <div class="fd-sec-acts">
                      <button type="button" class="fd-sec-act" @click.stop="renameSection(sec.sectionIndex)">Renomear</button>
                      <button type="button" class="fd-sec-act" @click.stop="removeSection(sec.sectionIndex)">Remover</button>
                    </div>
                  </div>

                  <!-- Fields in this section -->
                  <div
                    v-for="(field, fieldIdx) in versionFields"
                    v-show="fieldIdx > sec.sectionIndex && (secIdx === sections.length - 1 || fieldIdx < sections[secIdx + 1].sectionIndex) && field.field_type !== 'section' && filteredDetailFields.includes(field) && !isFieldHidden(fieldIdx)"
                    :key="`sec-${sec.key}-field-${fieldIdx}`"
                    :id="`fd-field-${fieldIdx}`"
                  >
                    <div
                      class="fd-field-row"
                      :class="{ expanded: expandedDetailIndex === fieldIdx }"
                      @click="toggleDetailExpand(fieldIdx)"
                    >
                      <label v-if="selectModeDetail" class="f-chk" @click.stop>
                        <input
                          type="checkbox"
                          :checked="selectedDetail.has(fieldIdx)"
                          @change="toggleFieldSelection($event, fieldIdx)"
                        />
                      </label>
                      <span class="f-drag" title="Arrastar">⠿</span>
                      <span class="f-num">{{ String(fieldIdx + 1).padStart(2, '0') }}</span>
                      <span class="f-type" :class="field.field_type">
                        {{ FIELD_TYPE_SHORT[field.field_type] ?? field.field_type.toUpperCase().slice(0, 3) }}
                      </span>
                      <span class="f-lbl">{{ field.label || '(sem nome)' }}</span>
                      <span class="f-key">{{ field.key || '—' }}</span>
                      <span class="f-req">
                        <span v-if="field.required" class="f-rdot" title="Obrigatório"></span>
                      </span>
                      <span class="f-wt">{{ weightDisplay(field) }}</span>
                      <span class="f-arr">›</span>
                    </div>
                    <div v-show="expandedDetailIndex === fieldIdx">
                      <FormFieldEditor
                        v-model="versionFields[fieldIdx]"
                        :index="fieldIdx"
                        :show-remove="versionFields.length > 1"
                        mode="inline"
                        @remove="removeVersionField(fieldIdx)"
                      />
                    </div>
                  </div>

                  <!-- Add row for this section -->
                  <div v-show="!collapsedSectionsDetail.has(sec.sectionIndex)" class="fd-add-row">
                    <button type="button" class="fd-add-main" @click="addVersionField('boolean', sec.sectionIndex)">+ Campo</button>
                    <div class="fd-add-chips">
                      <button
                        v-for="t in quickTypes"
                        :key="t.type"
                        type="button"
                        class="fd-add-chip"
                        @click="addVersionField(t.type, sec.sectionIndex)"
                      >
                        {{ t.label }}
                      </button>
                    </div>
                  </div>
                </div>
              </template>

              <!-- Flat list (no sections) -->
              <template v-else>
                <div
                  v-for="(field, fieldIdx) in versionFields"
                  v-show="filteredDetailFields.includes(field)"
                  :key="fieldIdx"
                  :id="`fd-field-${fieldIdx}`"
                >
                  <div
                    class="fd-field-row"
                    :class="{ expanded: expandedDetailIndex === fieldIdx }"
                    @click="toggleDetailExpand(fieldIdx)"
                  >
                    <label v-if="selectModeDetail" class="f-chk" @click.stop>
                      <input
                        type="checkbox"
                        :checked="selectedDetail.has(fieldIdx)"
                        @change="toggleFieldSelection($event, fieldIdx)"
                      />
                    </label>
                    <span class="f-drag" title="Arrastar">⠿</span>
                    <span class="f-num">{{ String(fieldIdx + 1).padStart(2, '0') }}</span>
                    <span class="f-type" :class="field.field_type">
                      {{ FIELD_TYPE_SHORT[field.field_type] ?? field.field_type.toUpperCase().slice(0, 3) }}
                    </span>
                    <span class="f-lbl">{{ field.label || '(sem nome)' }}</span>
                    <span class="f-key">{{ field.key || '—' }}</span>
                    <span class="f-req">
                      <span v-if="field.required" class="f-rdot" title="Obrigatório"></span>
                    </span>
                    <span class="f-wt">{{ weightDisplay(field) }}</span>
                    <span class="f-arr">›</span>
                  </div>
                  <div v-show="expandedDetailIndex === fieldIdx">
                    <FormFieldEditor
                      v-model="versionFields[fieldIdx]"
                      :index="fieldIdx"
                      :show-remove="versionFields.length > 1"
                      mode="inline"
                      @remove="removeVersionField(fieldIdx)"
                    />
                  </div>
                </div>
              </template>

              <!-- Global add row (bottom) -->
              <div class="fd-add-row">
                <button type="button" class="fd-add-main" @click="addVersionField('boolean')">+ Campo</button>
                <div class="fd-add-chips">
                  <button
                    v-for="t in quickTypes"
                    :key="t.type"
                    type="button"
                    class="fd-add-chip"
                    @click="addVersionField(t.type)"
                  >
                    {{ t.label }}
                  </button>
                </div>
              </div>
            </template>

            <p v-if="versionError" style="font-size:13px;font-weight:600;color:var(--sa-danger);padding:12px 16px;">
              {{ versionError }}
            </p>
          </form>
        </div>

        <!-- ── BELOW EDITOR: Recent submissions ── -->
        <div class="fd-below">
          <!-- Description -->
          <div v-if="formDetail.description" class="info-box" style="margin-bottom:16px;">
            {{ formDetail.description }}
          </div>

          <!-- Recent submissions -->
          <div>
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
        </div>

      </div>
    </template>
  </AppShell>
</template>

<style scoped>
/* ── Full-height shell ── */
.fd-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

/* ── Top Bar ── */
.fd-topbar {
  background: #fff;
  border-bottom: 1px solid var(--sa-line);
  padding: 0 16px;
  height: 52px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.fd-tb-back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 7px;
  background: #fff;
  border: 1px solid var(--sa-line);
  cursor: pointer;
  color: var(--sa-muted);
  flex-shrink: 0;
}
.fd-tb-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--sa-text);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fd-ver-badge {
  font-family: var(--mono, monospace);
  font-size: 11px;
  color: var(--sa-muted);
  background: #f1f5f9;
  padding: 2px 7px;
  border-radius: 4px;
  border: 1px solid var(--sa-line);
  flex-shrink: 0;
}
.fd-status-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  padding: 3px 7px;
  border-radius: 99px;
  background: #dcfce7;
  color: #15803d;
  flex-shrink: 0;
}
.fd-status-chip--draft {
  background: #f1f5f9;
  color: #64748b;
}
.fd-status-chip--draft::before {
  content: '';
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #94a3b8;
}
.fd-topbar-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
@media (min-width: 768px) {
  .fd-topbar { padding: 0 20px; height: 56px; gap: 10px; }
  .fd-tb-name { font-size: 15px; }
}

/* ── Toolbar ── */
.fd-toolbar {
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
.fd-toolbar::-webkit-scrollbar { display: none; }
.fd-sbar {
  display: flex;
  align-items: center;
  gap: 7px;
  background: var(--sa-bg);
  border: 1px solid var(--sa-line);
  border-radius: 8px;
  padding: 7px 11px;
  flex: 1;
  min-width: 120px;
}
.fd-sbar:focus-within {
  border-color: var(--sa-brand);
  background: #fff;
  box-shadow: 0 0 0 3px rgba(37,99,235,.1);
}
@media (min-width: 768px) {
  .fd-toolbar { padding: 8px 20px; overflow-x: visible; }
  .fd-sbar { max-width: 300px; }
}

/* ── Section chips (mobile) ── */
.fd-sec-chips-bar {
  background: #fff;
  border-bottom: 1px solid var(--sa-line);
  padding: 8px 16px;
  display: flex;
  gap: 6px;
  overflow-x: auto;
  flex-shrink: 0;
  -webkit-overflow-scrolling: touch;
  scroll-snap-type: x mandatory;
}
.fd-sec-chips-bar::-webkit-scrollbar { display: none; }
.fd-sec-chip {
  padding: 5px 12px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid var(--sa-line);
  background: #fff;
  color: var(--sa-muted);
  font-family: inherit;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all .15s;
  scroll-snap-align: start;
}
.fd-sec-chip.active {
  border-color: var(--sa-brand);
  background: var(--sa-brand-soft, #eff6ff);
  color: var(--sa-brand);
}
@media (min-width: 768px) { .fd-sec-chips-bar { display: none; } }

/* ── Bulk bar ── */
.fd-bulk-bar {
  background: var(--sa-brand-soft, #eff6ff);
  border-bottom: 1px solid #bfdbfe;
  padding: 8px 16px;
  display: none;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  overflow-x: auto;
}
.fd-bulk-bar.on { display: flex; }
.fd-bulk-info {
  font-size: 13px;
  font-weight: 600;
  color: var(--sa-brand);
  white-space: nowrap;
}

/* ── Editor layout ── */
.fd-editor {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
@media (min-width: 768px) { .fd-editor { flex-direction: row; } }

/* ── Outline (desktop) ── */
.fd-outline { display: none; }
@media (min-width: 768px) {
  .fd-outline {
    display: flex;
    flex-direction: column;
    width: 216px;
    flex-shrink: 0;
    border-right: 1px solid var(--sa-line);
    overflow-y: auto;
    background: var(--sa-bg);
  }
}
.fd-ol-hdr {
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
.fd-ol-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}
.fd-ol-list::-webkit-scrollbar { width: 4px; }
.fd-ol-list::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 99px; }
.fd-outline-sec {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
  border: none;
  background: none;
  font-family: inherit;
  width: 100%;
  text-align: left;
  border-radius: 7px;
  transition: color .12s, background .12s;
  position: relative;
}
.fd-outline-sec:hover { background: #f1f5f9; color: var(--sa-text); }
.fd-outline-sec.active {
  color: var(--sa-brand);
  background: var(--sa-brand-soft, #eff6ff);
  font-weight: 700;
}
.fd-outline-sec.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 4px;
  bottom: 4px;
  width: 3px;
  background: var(--sa-brand);
  border-radius: 0 2px 2px 0;
}
.fd-ol-cnt {
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
.fd-outline-sec.active .fd-ol-cnt {
  background: rgba(37,99,235,.1);
  color: var(--sa-brand);
}
.fd-ol-add {
  padding: 6px;
  flex-shrink: 0;
  border-top: 1px solid var(--sa-line);
}
.fd-ol-add button {
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
.fd-ol-add button:hover { border-color: var(--sa-brand); color: var(--sa-brand); }

/* ── Field list ── */
.fd-field-list {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  background: #fff;
}
.fd-field-list::-webkit-scrollbar { width: 4px; }
.fd-field-list::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 99px; }

/* ── Section header sticky ── */
.fd-sec-hdr {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--sa-bg);
  border-top: 1px solid var(--sa-line);
  border-bottom: 1px solid var(--sa-line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-right: 10px;
}
.fd-sec-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--sa-muted);
  border: none;
  background: none;
  font-family: inherit;
  cursor: pointer;
  flex: 1;
  text-align: left;
}
.fd-sec-cnt {
  font-size: 10px;
  font-weight: 700;
  color: var(--sa-muted);
  background: var(--sa-bg);
  border: 1px solid var(--sa-line);
  border-radius: 99px;
  padding: 1px 6px;
  margin-left: 4px;
}
.fd-sec-acts { display: none; gap: 4px; }
.fd-sec-hdr:hover .fd-sec-acts { display: flex; }
.fd-sec-act {
  font-size: 11px;
  font-weight: 600;
  color: var(--sa-muted);
  border: 1px solid var(--sa-line);
  border-radius: 5px;
  background: #fff;
  padding: 3px 8px;
  cursor: pointer;
  font-family: inherit;
}
.fd-sec-act:hover { color: var(--sa-danger); border-color: var(--sa-danger); }

/* ── Field row ── */
.fd-field-row {
  display: flex;
  align-items: center;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid var(--sa-line);
  padding: 0 12px 0 0;
  gap: 0;
  cursor: pointer;
  user-select: none;
  transition: background .1s;
}
.fd-field-row:hover { background: #fafafa; }
.fd-field-row.expanded { background: #eff6ff; border-bottom-color: transparent; }
@media (min-width: 768px) { .fd-field-row { height: 44px; } }

/* ── Add row ── */
.fd-add-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #fff;
  border-bottom: 1px solid var(--sa-line);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.fd-add-row::-webkit-scrollbar { display: none; }
.fd-add-main {
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-brand);
  border: 1px dashed var(--sa-brand);
  border-radius: 6px;
  background: none;
  padding: 4px 10px;
  cursor: pointer;
  font-family: inherit;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background .12s;
}
.fd-add-main:hover { background: var(--sa-brand-soft, #eff6ff); }
.fd-add-chips { display: flex; gap: 5px; flex-shrink: 0; }
.fd-add-chip {
  font-size: 10px;
  font-weight: 700;
  font-family: 'DM Mono', monospace;
  padding: 3px 7px;
  border-radius: 4px;
  border: 1px solid var(--sa-line);
  background: #fff;
  color: var(--sa-muted);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
}
.fd-add-chip:hover {
  border-color: var(--sa-brand);
  color: var(--sa-brand);
  background: var(--sa-brand-soft, #eff6ff);
}

/* ── Below editor (recent submissions) ── */
.fd-below {
  padding: 20px 16px;
  overflow-y: auto;
  flex-shrink: 0;
  border-top: 1px solid var(--sa-line);
  background: var(--sa-bg);
  max-height: 40vh;
}
@media (min-width: 768px) {
  .fd-below { padding: 20px; max-height: 35vh; }
}

/* ── Reused field row atoms ── */
.f-drag { color: #cbd5e1; font-size: 16px; cursor: grab; flex-shrink: 0; width: 18px; display: flex; align-items: center; justify-content: center; margin: 0 6px 0 12px; }
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
.fd-field-row.expanded .f-arr { transform: rotate(90deg); }
.f-chk { width: 22px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-left: 12px; }
.f-chk input[type=checkbox] { width: 16px; height: 16px; cursor: pointer; accent-color: var(--sa-brand); }

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
