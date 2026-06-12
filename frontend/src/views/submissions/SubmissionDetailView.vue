<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import InspectionFieldRow from '@/components/submissions/InspectionFieldRow.vue'
import InspectionListRow from '@/components/submissions/InspectionListRow.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { useConformity } from '@/composables/useConformity'
import { useEvidence } from '@/composables/useEvidence'
import { useInspectionProgress } from '@/composables/useInspectionProgress'
import { useInspectionSwipe } from '@/composables/useInspectionSwipe'
import { scoreColorVar } from '@/utils/score'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchFormVersion } from '@/services/forms.service'
import { saveConformity } from '@/services/submissions.service'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
import { buildRenderRows, instanceKey } from '@/utils/inspectionInstances'
import type { FieldInstance, RenderRow } from '@/utils/inspectionInstances'
import type { FormVersion } from '@/types/forms'

const route  = useRoute()
const router = useRouter()
const submissionsStore = useSubmissionsStore()

// ── Core state ───────────────────────────────────────────────────────────────

const formVersion  = ref<FormVersion | null>(null)
const draftAnswers = reactive<Record<string, string>>({})
const saveError    = ref<string | null>(null)
const finishError  = ref<string | null>(null)
const savedOnce    = ref(false)

const inspectionMode  = ref(false)
const inspectionIndex = ref(0)
const viewMode        = ref<'card' | 'list'>('card')

const pendingRequiredFields = ref<string[]>([])

const LIST_PAGE     = 50
const listViewLimit = ref(LIST_PAGE)

// ── Core computed ────────────────────────────────────────────────────────────

const submissionId = computed(() => route.params.id as string)
const submission   = computed(() => submissionsStore.current)
const isCompleted  = computed(() => submission.value?.status === 'completed')

const fields = computed(() =>
  [...(formVersion.value?.fields ?? [])].sort((a, b) => a.position - b.position),
)

const renderRows = computed(() =>
  buildRenderRows(fields.value, submission.value?.checklist ?? null),
)

const answerableInstances = computed<FieldInstance[]>(() =>
  renderRows.value.flatMap((r) => (r.kind === 'instance' ? [r.instance] : [])),
)

// ── Navigation ───────────────────────────────────────────────────────────────

// NOTA: inspectionNext é declarado ANTES dos composables pois é passado
// como callback para useConformity e useInspectionSwipe.
// Usa swipeExiting que vem de useInspectionSwipe — referência tardia OK
// porque a função só é chamada em runtime, não em setup.

function inspectionNext() {
  if (inspectionIndex.value < answerableInstances.value.length - 1) {
    swipeExiting.value = 'right'
    setTimeout(() => { swipeExiting.value = null; inspectionIndex.value++ }, 220)
  }
}

function inspectionPrev() {
  if (inspectionIndex.value > 0) {
    swipeExiting.value = 'left'
    setTimeout(() => { swipeExiting.value = null; inspectionIndex.value-- }, 220)
  }
}

function jumpToSection(sectionKey: string) {
  const sectionField = fields.value.find((f) => f.key === sectionKey && f.field_type === 'section')
  if (!sectionField) return
  const idx = answerableInstances.value.findIndex((i) => i.field.position > sectionField.position)
  if (idx !== -1) inspectionIndex.value = idx
}

// ── Composables ──────────────────────────────────────────────────────────────

const {
  conformityStatus,
  conformityJustification,
  showJustificationSheet,
  justificationFieldKey,
  justificationError,
  setConformity,
  setNaoConformeCard,
  openJustificationSheet,
  closeJustificationSheet,
  confirmJustification,
  buildConformityItems,
  triggerConformitySave,
} = useConformity(submissionId, answerableInstances, inspectionNext)

const {
  evidenceAttachments,
  evidenceUploading,
  evidenceErrors,
  evidenceLoaded,
  showEvidenceSheet,
  evidenceSheetKey,
  evidenceSheetLabel,
  totalEvidenceCount,
  loadEvidenceAttachments,
  handleEvidenceUpload,
  handleEvidenceDelete,
  openEvidenceSheet,
  closeEvidenceSheet,
  uploadEvidenceFromSheet,
} = useEvidence(submissionId, answerableInstances)

const {
  progressStats,
  liveScore,
  scoreRingStyle,
  allAnswered,
  formSections,
  nearbyDots,
} = useInspectionProgress(answerableInstances, conformityStatus, fields, inspectionIndex)

// swipeExiting necessário em inspectionNext — declarado aqui, usado acima
const {
  swipeExiting,
  cardSwipeStyle,
  rightIndicatorOpacity,
  leftIndicatorOpacity,
  onTouchStart,
  onTouchMove,
  onTouchEnd,
} = useInspectionSwipe({
  getCurrentInstanceKey: () => inspKey.value,
  onConformeSwipe:       (key) => setConformityCard(key, 'conforme'),
  onNaoConformeSwipe:    (key) => setNaoConformeCard(key),
})

// ── Card inspection helpers ───────────────────────────────────────────────────

const inspectionInstance = computed(() => answerableInstances.value[inspectionIndex.value] ?? null)
const inspectionField    = computed(() => inspectionInstance.value?.field ?? null)
const inspKey            = computed(() => inspectionInstance.value?.key ?? '')

const inspectionSectionLabel = computed(() => {
  const inst = inspectionInstance.value
  if (!inst) return ''
  const idx = fields.value.findIndex((f) => f.key === inst.field.key)
  for (let i = idx - 1; i >= 0; i--) {
    if (fields.value[i].field_type === 'section') return fields.value[i].label
  }
  return ''
})

const currentFieldStatus = computed(() => {
  if (!inspectionInstance.value) return 'pending'
  const s = conformityStatus[inspectionInstance.value.key]
  if (s === 'conforme') return 'conformes'
  if (s === 'nao_conforme') return 'nao_conformes'
  return 'pending'
})

const currentFieldEvidenceCount = computed(() =>
  inspectionInstance.value
    ? (evidenceAttachments[inspectionInstance.value.key]?.length ?? 0)
    : 0,
)

function setConformityCard(fieldKey: string, status: 'conforme' | 'nao_conforme') {
  setConformity(fieldKey, status)
  if (status === 'conforme') setTimeout(() => inspectionNext(), 300)
}

// ── Auto-save ─────────────────────────────────────────────────────────────────

let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

function triggerAutoSave() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(async () => {
    try {
      await submissionsStore.updateAnswers(submissionId.value, { answers: buildPayload() })
      savedOnce.value = true
    } catch { /* silent */ }
  }, 1200)
}

function answerBoolean(fieldKey: string, value: 'true' | 'false' | 'na') {
  draftAnswers[fieldKey] = value
  triggerAutoSave()
}

// ── List mode ─────────────────────────────────────────────────────────────────

const FILTERS = [
  { id: 'all',   label: 'Todos',       cls: ''     },
  { id: 'pend',  label: '⚡ Pendentes', cls: 'warn' },
  { id: 'conf',  label: '✓ Conformes', cls: 'ok'   },
  { id: 'nconf', label: '✕ Não conf.', cls: 'err'  },
  { id: 'bool',  label: 'S/N',         cls: ''     },
  { id: 'sel',   label: 'Seleção',     cls: ''     },
] as const

type ListFilter = typeof FILTERS[number]['id']
const listFilter      = ref<ListFilter>('all')
const expandedListKey = ref<string | null>(null)

const filteredRows = computed<RenderRow[]>(() =>
  renderRows.value.filter((r) => {
    if (r.kind === 'section') return true
    const inst = r.instance
    if (listFilter.value === 'pend')  return !conformityStatus[inst.key]
    if (listFilter.value === 'conf')  return conformityStatus[inst.key] === 'conforme'
    if (listFilter.value === 'nconf') return conformityStatus[inst.key] === 'nao_conforme'
    if (listFilter.value === 'bool')  return inst.field.field_type === 'boolean'
    if (listFilter.value === 'sel')   return inst.field.field_type === 'select'
    return true
  }),
)

const visibleSectionKeys = computed(() => {
  const keys = new Set<string>()
  let currentSec: string | null = null
  for (const r of filteredRows.value) {
    if (r.kind === 'section') { currentSec = r.field.key; continue }
    if (currentSec) keys.add(currentSec)
  }
  return keys
})

const displayedListRows = computed(() => renderRows.value.slice(0, listViewLimit.value))
const hasMoreFields      = computed(() => listViewLimit.value < renderRows.value.length)
function loadMoreFields() { listViewLimit.value += LIST_PAGE }
function doSkip()         { inspectionNext() }

function filterCount(filterId: ListFilter): number {
  const ai = answerableInstances.value
  if (filterId === 'all')   return ai.length
  if (filterId === 'pend')  return ai.filter(i => !conformityStatus[i.key]).length
  if (filterId === 'conf')  return ai.filter(i => conformityStatus[i.key] === 'conforme').length
  if (filterId === 'nconf') return ai.filter(i => conformityStatus[i.key] === 'nao_conforme').length
  if (filterId === 'bool')  return ai.filter(i => i.field.field_type === 'boolean').length
  if (filterId === 'sel')   return ai.filter(i => i.field.field_type === 'select').length
  return 0
}

function sectionInstances(sectionKey: string): FieldInstance[] {
  const all    = filteredRows.value
  const secIdx = all.findIndex(r => r.kind === 'section' && r.field.key === sectionKey)
  if (secIdx === -1) return []
  const result: FieldInstance[] = []
  for (let i = secIdx + 1; i < all.length; i++) {
    const r = all[i]
    if (r.kind === 'section') break
    result.push(r.instance)
  }
  return result
}

function sectionPct(sectionKey: string): number {
  const sf = sectionInstances(sectionKey)
  if (sf.length === 0) return 0
  return Math.round((sf.filter(i => !!conformityStatus[i.key]).length / sf.length) * 100)
}

function sectionProgress(sectionKey: string): string {
  const sf   = sectionInstances(sectionKey)
  const done = sf.filter(i => !!conformityStatus[i.key]).length
  return `${done}/${sf.length}`
}

function sectionRingStyle(sectionKey: string): Record<string, string> {
  const pct = sectionPct(sectionKey)
  const col = pct === 100 ? 'var(--sa-ok)' : pct > 0 ? 'var(--sa-brand)' : 'var(--sa-line)'
  return { background: `conic-gradient(${col} ${pct}%, var(--sa-line) 0)` }
}

function toggleListRow(key: string) {
  expandedListKey.value = expandedListKey.value === key ? null : key
  if (expandedListKey.value === key) {
    nextTick(() => {
      const el        = document.getElementById(`list-row-${key}`)
      const container = document.getElementById('list-scroll-container')
      if (el && container) container.scrollTo({ top: el.offsetTop - 64, behavior: 'smooth' })
    })
  }
}

function jumpNextPending(afterKey: string) {
  const keys = answerableInstances.value.map(i => i.key)
  const idx  = keys.indexOf(afterKey)
  for (let i = idx + 1; i < keys.length; i++) {
    if (!conformityStatus[keys[i]]) {
      const el        = document.getElementById(`list-row-${keys[i]}`)
      const container = document.getElementById('list-scroll-container')
      if (el && container) container.scrollTo({ top: el.offsetTop - 64, behavior: 'smooth' })
      return
    }
  }
}

function setConformityList(key: string, status: 'conforme' | 'nao_conforme') {
  setConformity(key, status)
  if (status === 'conforme') {
    expandedListKey.value = null
    nextTick(() => setTimeout(() => jumpNextPending(key), 400))
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não', text: 'Texto', number: 'Número', date: 'Data', select: 'Seleção',
}

function selectOptions(configJson: Record<string, unknown>): string[] {
  return Array.isArray(configJson.options) ? (configJson.options as string[]) : []
}

function fieldWeight(configJson: Record<string, unknown>): number {
  return Number(configJson?.weight) || 0
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    in_progress: 'Em andamento', completed: 'Concluída',
    draft: 'Rascunho', cancelled: 'Cancelada',
  }
  return map[status] ?? status
}

function pendingLabel(key: string): string {
  const inst = answerableInstances.value.find((i) => i.key === key)
  if (!inst) return key
  return inst.componentLabel ? `${inst.field.label} (${inst.componentLabel})` : inst.field.label
}

function instancePosition(inst: FieldInstance): number {
  return answerableInstances.value.findIndex((i) => i.key === inst.key) + 1
}

// ── Data init ─────────────────────────────────────────────────────────────────

function populateDraft() {
  if (!submission.value) return
  // Respostas
  for (const ans of submission.value.answers) {
    const key = instanceKey(ans.field_key, ans.asset_id ?? null)
    if (ans.value === null || ans.value === undefined) {
      draftAnswers[key] = ''
    } else if (ans.field_type === 'boolean') {
      draftAnswers[key] = ans.value === 'na' ? 'na' : ans.value ? 'true' : 'false'
    } else if (ans.field_type === 'select') {
      draftAnswers[key] = typeof ans.value === 'string' ? ans.value : ''
    } else {
      draftAnswers[key] = String(ans.value)
    }
  }
  // Conformidade — mutação direta no reactive do useConformity
  for (const c of submission.value.conformity ?? []) {
    const key = instanceKey(c.field_key, c.asset_id ?? null)
    conformityStatus[key] = c.status
    if (c.justification) conformityJustification[key] = c.justification
  }
}

onMounted(async () => {
  await submissionsStore.loadOne(submissionId.value)
  if (submission.value) {
    formVersion.value = await fetchFormVersion(
      submission.value.form_id,
      submission.value.form_version_id,
    )
    populateDraft()
    await loadEvidenceAttachments()
    if (submission.value.status === 'in_progress') {
      inspectionMode.value = true
      viewMode.value = 'list'
    }
  }
})

watch(() => submissionsStore.current?.id, (newId) => {
  if (newId === submissionId.value) populateDraft()
})

watch(fields, () => { listViewLimit.value = LIST_PAGE })

// ── Payload builder ───────────────────────────────────────────────────────────

function buildPayload() {
  return answerableInstances.value
    .map((inst) => {
      const raw = draftAnswers[inst.key] ?? ''
      if (raw === '') return null
      let value: boolean | number | string | null = null
      if (inst.field.field_type === 'boolean') {
        value = raw === 'na' ? 'na' : raw === 'true'
      } else if (inst.field.field_type === 'number') {
        const n = parseFloat(raw)
        value = isNaN(n) ? null : n
      } else {
        value = raw
      }
      if (value === null) return null
      return { field_key: inst.field.key, value, ...(inst.asset_id ? { asset_id: inst.asset_id } : {}) }
    })
    .filter((ans): ans is NonNullable<typeof ans> => ans !== null)
}

function validateRequiredFields(): boolean {
  const missing = new Set<string>()
  for (const inst of answerableInstances.value) {
    if (inst.field.required) {
      const val = draftAnswers[inst.key]
      if (!val || val === '') missing.add(inst.key)
      if (!conformityStatus[inst.key]) missing.add(inst.key)
    }
    const s = conformityStatus[inst.key]
    if (s === 'nao_conforme' && !(conformityJustification[inst.key] || '').trim()) {
      missing.add(inst.key)
    }
  }
  pendingRequiredFields.value = [...missing]
  return missing.size === 0
}

// ── Save / Finish ─────────────────────────────────────────────────────────────

async function handleSave() {
  saveError.value = null; finishError.value = null
  try {
    await submissionsStore.updateAnswers(submissionId.value, { answers: buildPayload() })
    savedOnce.value = true
    pendingRequiredFields.value = []
  } catch (err) {
    saveError.value = extractProblemMessage(err, 'Não foi possível salvar as respostas.')
  }
}

async function handleFinish() {
  finishError.value = null; saveError.value = null; savedOnce.value = false
  pendingRequiredFields.value = []
  if (!validateRequiredFields()) {
    finishError.value = `Campos com pendências: ${pendingRequiredFields.value.map(pendingLabel).join(', ')}`
    return
  }
  try {
    await submissionsStore.updateAnswers(submissionId.value, { answers: buildPayload() })
    const items = buildConformityItems()
    if (items.length > 0) await saveConformity(submissionId.value, { items })
    await submissionsStore.finish(submissionId.value)
    inspectionMode.value = false
  } catch (err) {
    finishError.value = extractProblemMessage(err, 'Não foi possível finalizar a inspeção.')
  }
}
</script>

<template>
  <AppShell>
    <div class="page">

      <!-- Loading -->
      <div v-if="submissionsStore.isLoading" style="font-size:13px;color:var(--sa-muted);">
        Carregando inspeção...
      </div>

      <template v-else-if="submission">

        <!-- ── Header (compacto em inspection mode, completo em concluído) ── -->
        <div class="back-hdr">
          <button type="button" class="back-btn" @click="router.push({ name: 'submissions' })">
            <SvgIcon name="back" :size="16" />
          </button>
          <div style="flex:1;min-width:0;">
            <div v-if="!inspectionMode" class="eyebrow">Inspeção</div>
            <h1 style="font-size:16px;font-weight:700;letter-spacing:-.01em;color:var(--sa-text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              {{ submission.form_name }}
            </h1>
            <div v-if="!inspectionMode" style="font-size:12px;color:var(--sa-muted);margin-top:2px;">
              <span v-if="submission.asset_identifier">🏷 {{ submission.asset_identifier }} · </span>
              Iniciada {{ new Date(submission.started_at).toLocaleString('pt-BR', { day:'2-digit', month:'2-digit', year:'2-digit', hour:'2-digit', minute:'2-digit' }) }}
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
            <div v-if="inspectionMode && liveScore !== null" class="score-ring" :style="scoreRingStyle">
              <div class="score-ring-inner">{{ liveScore }}%</div>
            </div>
            <span class="status-chip" style="flex-shrink:0;"
              :class="{
                'status-chip--warn': submission.status === 'in_progress',
                'status-chip--inactive': submission.status === 'cancelled',
                'status-chip--neu': submission.status === 'draft',
              }">
              {{ statusLabel(submission.status) }}
            </span>
          </div>
        </div>

        <!-- ── Score final (completed) ── -->
        <div v-if="isCompleted && submission.score !== null" class="card card-p" style="margin-bottom:20px;">
          <div class="eyebrow" style="margin-bottom:4px;">Score final</div>
          <div :style="{
            fontSize:'36px', fontWeight:800, fontVariantNumeric:'tabular-nums',
            color: scoreColorVar(submission.score ?? 0),
          }">{{ submission.score }}%</div>

          <div v-if="submission.score_breakdown" class="score-breakdown-grid">
            <div class="sbd-card ok">
              <div class="sbd-label">Conformes</div>
              <div class="sbd-val">{{ submission.score_breakdown.conformes }}</div>
            </div>
            <div class="sbd-card err">
              <div class="sbd-label">Não conformes</div>
              <div class="sbd-val">{{ submission.score_breakdown.nao_conformes }}</div>
            </div>
            <div class="sbd-card neu">
              <div class="sbd-label">Sem resposta</div>
              <div class="sbd-val">{{ submission.score_breakdown.sem_resposta }}</div>
            </div>
            <div v-if="submission.score_breakdown.na_count > 0" class="sbd-card neu">
              <div class="sbd-label">N/A</div>
              <div class="sbd-val">{{ submission.score_breakdown.na_count }}</div>
            </div>
          </div>
        </div>

        <!-- ── Fields area ── -->
        <div v-if="fields.length">

          <!-- Progress bar (compact; legend inline apenas fora do modo inspeção) -->
          <div class="insp-progress-bar" style="margin-bottom:4px;height:6px;">
            <div style="display:flex;height:100%;border-radius:99px;overflow:hidden;background:var(--sa-line);">
              <div
                style="background:var(--sa-ok);transition:width .35s ease;"
                :style="{ width: progressStats.total ? (progressStats.conformes / progressStats.total * 100) + '%' : '0%' }"
              />
              <div
                style="background:var(--sa-danger);transition:width .35s ease;"
                :style="{ width: progressStats.total ? (progressStats.naoConformes / progressStats.total * 100) + '%' : '0%' }"
              />
            </div>
          </div>

          <!-- Legend compacta (só para inspeções concluídas / vista read-only) -->
          <div v-if="!inspectionMode" style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
            <span style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--sa-muted);">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-ok);flex-shrink:0;"></span>
              {{ progressStats.conformes }} Conforme
            </span>
            <span style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--sa-muted);">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-danger);flex-shrink:0;"></span>
              {{ progressStats.naoConformes }} Não conforme
            </span>
            <span v-if="progressStats.pending > 0" style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--sa-muted);">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-line);flex-shrink:0;"></span>
              {{ progressStats.pending }} Pendente
            </span>
          </div>

          <!-- ═══════════════════════════════════════════════════════════════ -->
          <!--  INSPECTION MODE                                                -->
          <!-- ═══════════════════════════════════════════════════════════════ -->
          <template v-if="inspectionMode">

            <!-- Card mode: handled by fullscreen Teleport overlay above -->
            <template v-if="viewMode === 'card'">
              <!-- placeholder: overlay covers this area -->
            </template>

            <!-- ── LIST VIEW: handled by Teleport shell below ── -->
            <template v-else>
              <!-- placeholder — insp-list-shell Teleport covers this -->
            </template>
          </template>

          <!-- ═══════════════════════════════════════════════════════════════ -->
          <!--  LIST MODE (outside inspection)                                 -->
          <!-- ═══════════════════════════════════════════════════════════════ -->
          <template v-else>
            <!-- Section jump chips -->
            <div v-if="formSections.length" class="section-jump-bar" style="margin-bottom:12px;">
              <a v-for="sec in formSections" :key="sec.key" :href="`#sec-${sec.key}`" class="section-jump-chip">
                {{ sec.label }}
                <span style="opacity:.7;font-size:10px;margin-left:2px;">{{ sec.pct }}%</span>
              </a>
            </div>

            <!-- Evidence summary for completed inspections -->
            <div v-if="isCompleted && evidenceLoaded" style="display:flex;align-items:center;gap:6px;margin-bottom:12px;font-size:12px;color:var(--sa-muted);">
              <span>📎</span>
              <span v-if="totalEvidenceCount > 0" style="font-weight:600;color:var(--sa-brand);">{{ totalEvidenceCount }} evidência(s) registrada(s)</span>
              <span v-else>Sem evidências registradas nesta inspeção</span>
            </div>

            <!-- Avisos não-bloqueantes da expansão por componente (Q2/Q3, DR-0002 T8) -->
            <div v-if="submission.warnings?.length" class="insp-warn-box">
              <div v-for="(w, wi) in submission.warnings" :key="wi" class="insp-warn-line">⚠ {{ w }}</div>
            </div>

            <div class="fpanel" style="margin-bottom:16px;">
              <template v-for="row in displayedListRows">
                <div v-if="row.kind === 'section'" :key="`sec-${row.field.id}`" :id="`sec-${row.field.key}`" class="section-divider">
                  <span>{{ row.field.label }}</span>
                </div>
                <InspectionFieldRow
                  v-else
                  :key="row.instance.key"
                  :field="row.field"
                  :component-label="row.instance.componentLabel"
                  :answer="draftAnswers[row.instance.key] ?? ''"
                  :conformity-status="conformityStatus[row.instance.key]"
                  :conformity-justification="conformityJustification[row.instance.key] ?? ''"
                  :is-completed="isCompleted"
                  :is-pending-required="pendingRequiredFields.includes(row.instance.key)"
                  :evidence-attachments="evidenceAttachments[row.instance.key] ?? []"
                  :evidence-uploading="evidenceUploading[row.instance.key] ?? false"
                  :evidence-error="evidenceErrors[row.instance.key]"
                  @update-answer="v => { draftAnswers[row.instance.key] = v; triggerAutoSave() }"
                  @set-conformity="s => setConformity(row.instance.key, s)"
                  @update-justification="v => { conformityJustification[row.instance.key] = v; triggerConformitySave() }"
                  @upload-evidence="e => handleEvidenceUpload(row.field.key, row.instance.asset_id, {}, e)"
                  @delete-evidence="id => handleEvidenceDelete(row.instance.key, id)"
                />
              </template>
            </div>

            <div v-if="hasMoreFields" style="display:flex;justify-content:center;margin-bottom:12px;">
              <button type="button" class="btn-secondary btn-sm" @click="loadMoreFields">
                Carregar mais campos ({{ renderRows.length - listViewLimit }} restantes)
              </button>
            </div>
            <div style="margin-bottom:68px;"></div>
          </template>

          <!-- Errors -->
          <p v-if="saveError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:8px;">{{ saveError }}</p>
          <p v-if="finishError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:8px;">{{ finishError }}</p>
        </div>

        <!-- ── Sticky actions (hidden in card inspection mode) ── -->
        <div v-if="!(inspectionMode && !isCompleted)" class="sticky-act">
          <template v-if="!isCompleted">
            <button type="button" class="btn-secondary" :disabled="submissionsStore.isSaving" @click="handleSave">
              {{ submissionsStore.isSaving ? 'Salvando…' : savedOnce ? '✓ Salvo' : 'Salvar rascunho' }}
            </button>
            <button type="button" class="btn-primary" :disabled="submissionsStore.isSaving" @click="handleFinish">
              {{ submissionsStore.isSaving ? 'Finalizando…' : 'Finalizar inspeção' }}
            </button>
          </template>
          <button v-else type="button" class="btn-primary" @click="router.push({ name: 'submission-report', params: { id: submissionId } })">
            Ver relatório completo →
          </button>
        </div>

      </template>

      <!-- Not found -->
      <div v-else-if="!submissionsStore.isLoading" class="empty">
        <div class="empty-h">Inspeção não encontrada</div>
      </div>

    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!--  FULLSCREEN CARD INSPECTION OVERLAY                                   -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <Teleport to="body">
      <div
        v-if="submission && inspectionMode && viewMode === 'card' && !isCompleted"
        class="insp-fullscreen"
      >
        <!-- ── 1. HEADER ── -->
        <div class="insp-fhdr">
          <button type="button" class="insp-fback" @click="viewMode = 'list'">
            <SvgIcon name="back" :size="16" />
          </button>
          <div class="insp-fhdr-info">
            <div class="insp-fhdr-name">{{ submission.form_name }}</div>
            <div class="insp-fhdr-sub"><span v-if="submission.asset_identifier">🏷 {{ submission.asset_identifier }} · </span>Em andamento</div>
          </div>
          <div class="insp-fhdr-vt">
            <button class="insp-fhdr-vt-btn" :class="String(viewMode) === 'list' ? 'active' : ''" @click="viewMode = 'list'">
              <span style="font-size: 11px;">☰</span> Lista
            </button>
            <button class="insp-fhdr-vt-btn" :class="String(viewMode) === 'card' ? 'active' : ''">
              <span style="font-size: 11px;">▦</span> Cartão
            </button>
          </div>
          <div class="score-ring" :style="scoreRingStyle">
            <div class="score-ring-inner">{{ liveScore !== null ? liveScore + '%' : '—' }}</div>
          </div>
        </div>

        <!-- ── 2. PROGRESS AREA ── -->
        <div class="insp-fprog">
          <div class="insp-fprog-row">
            <div class="insp-fprog-bar">
              <div :style="{
                height: '100%',
                background: 'var(--sa-ok)',
                width: progressStats.total ? (progressStats.conformes / progressStats.total * 100) + '%' : '0%',
                transition: 'width .35s ease',
              }" />
              <div :style="{
                height: '100%',
                background: 'var(--sa-danger)',
                width: progressStats.total ? (progressStats.naoConformes / progressStats.total * 100) + '%' : '0%',
                transition: 'width .35s ease',
              }" />
            </div>
            <div class="insp-fprog-lbl">{{ progressStats.evaluated }}/{{ progressStats.total }}</div>
          </div>
          <!-- Legenda de cores -->
          <div style="display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:var(--sa-muted);padding:8px 0;">
            <span style="display:flex;align-items:center;gap:4px;">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-ok);flex-shrink:0;"></span>
              {{ progressStats.conformes }} Conforme
            </span>
            <span style="display:flex;align-items:center;gap:4px;">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-danger);flex-shrink:0;"></span>
              {{ progressStats.naoConformes }} Não conforme
            </span>
            <span v-if="progressStats.pending > 0" style="display:flex;align-items:center;gap:4px;">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-line);flex-shrink:0;"></span>
              {{ progressStats.pending }} Pendente
            </span>
          </div>
          <!-- Separador entre legenda e buttons -->
          <div style="height:1px;background:var(--sa-line);margin:0 -14px;"></div>
          <div v-if="formSections.length" class="insp-sec-chips">
            <button
              v-for="sec in formSections"
              :key="sec.key"
              type="button"
              class="insp-sec-chip"
              :class="{
                'insp-sec-chip--done':   sec.pct === 100,
                'insp-sec-chip--active': sec.label === inspectionSectionLabel,
              }"
              @click="jumpToSection(sec.key)"
            >
              {{ sec.label.length > 15 ? sec.label.slice(0, 15) + '…' : sec.label }}
              <span class="insp-sec-pct">{{ sec.pct }}%</span>
            </button>
          </div>
        </div>

        <!-- ── 3. SWIPE ZONE ── -->
        <div class="insp-fswipe">

          <!-- All done -->
          <div v-if="allAnswered" class="insp-fdone">
            <div class="done-ring">✓</div>
            <div v-if="liveScore !== null" class="done-score" :style="{ color: scoreColorVar(liveScore) }">
              {{ liveScore }}%
            </div>
            <div class="done-sub">Todos os campos respondidos</div>
            <button type="button" class="done-btn" @click="viewMode = 'list'">
              Ver lista completa
            </button>
          </div>

          <!-- Swipe card -->
          <template v-else-if="inspectionInstance && inspectionField">

            <!-- Side indicators -->
            <div class="insp-find insp-find--left" :style="{ opacity: leftIndicatorOpacity }">
              <div class="ind-icon ind-err">✕</div>
              <div class="ind-lbl ind-lbl--err">Não conforme</div>
            </div>
            <div class="insp-find insp-find--right" :style="{ opacity: rightIndicatorOpacity }">
              <div class="ind-icon ind-ok">✓</div>
              <div class="ind-lbl ind-lbl--ok">Conforme</div>
            </div>

            <!-- Card wrapper (max-width + centered) -->
            <div class="insp-card-outer">
              <div
                class="insp-card"
                :style="cardSwipeStyle"
                style="will-change:transform;touch-action:pan-y;"
                @touchstart.passive="onTouchStart"
                @touchmove.passive="onTouchMove"
                @touchend="onTouchEnd"
              >
                <!-- Stamps -->
                <div class="stamp stamp-conf"  :style="{ opacity: Math.min(1, rightIndicatorOpacity * 2) }">Conforme</div>
                <div class="stamp stamp-nconf" :style="{ opacity: Math.min(1, leftIndicatorOpacity  * 2) }">Não conforme</div>

                <!-- Card header: seção | peso + contador + status -->
                <div class="card-hdr" :style="{
                  background:
                    currentFieldStatus === 'conformes'     ? 'var(--sa-ok-bg)'  :
                    currentFieldStatus === 'nao_conformes' ? 'var(--sa-err-bg)' :
                    '#f8fafc',
                }">
                  <span class="card-sec">{{ inspectionSectionLabel || 'Geral' }}</span>
                  <div class="card-meta">
                    <span
                      v-if="fieldWeight(inspectionField.config_json) > 1"
                      class="card-weight"
                    >Peso {{ inspectionField.config_json.weight }}x</span>
                    <span class="card-counter">{{ inspectionIndex + 1 }} / {{ answerableInstances.length }}</span>
                    <span class="card-status" :class="{
                      'card-status--ok':   currentFieldStatus === 'conformes',
                      'card-status--err':  currentFieldStatus === 'nao_conformes',
                      'card-status--pend': currentFieldStatus === 'pending',
                    }">{{
                      currentFieldStatus === 'conformes'     ? 'Conforme'     :
                      currentFieldStatus === 'nao_conformes' ? 'Não conforme' :
                      'Pendente'
                    }}</span>
                  </div>
                </div>

                <!-- Card body -->
                <div class="card-body">

                  <!-- Type label + field label + required + instruction -->
                  <div class="card-type-lbl">{{ TYPE_LABEL[inspectionField.field_type] ?? 'Campo' }}</div>
                  <div class="card-label">{{ inspectionField.label }}</div>
                  <!-- Componente (campo escopado, DR-0002 T8) -->
                  <div v-if="inspectionInstance?.componentLabel" class="card-comp-chip" :title="inspectionInstance.componentPath ?? ''">
                    🧩 {{ inspectionInstance.componentLabel }}
                  </div>
                  <div v-if="inspectionField.required" class="card-req">Obrigatório</div>
                  <div v-if="inspectionField.instruction" class="card-instr">
                    {{ inspectionField.instruction }}
                  </div>

                  <!-- ── RESPOSTA ── -->
                  <div class="card-sep"><span class="card-sep-lbl">Resposta</span></div>

                  <!-- Boolean -->
                  <div v-if="inspectionField.field_type === 'boolean'" style="display:grid;gap:8px;">
                    <div class="bool-grid">
                      <button type="button" class="bool-btn bool-sim"
                        :class="{ 'bool-btn--active': draftAnswers[inspKey] === 'true' }"
                        @click="answerBoolean(inspKey, 'true')">
                        <span class="b-icon">✓</span><span class="b-lbl">Sim</span>
                      </button>
                      <button type="button" class="bool-btn bool-nao"
                        :class="{ 'bool-btn--active': draftAnswers[inspKey] === 'false' }"
                        @click="answerBoolean(inspKey, 'false')">
                        <span class="b-icon">✕</span><span class="b-lbl">Não</span>
                      </button>
                    </div>
                    <button v-if="inspectionField.config_json?.allow_na"
                      type="button" class="na-btn"
                      :class="{ 'na-btn--active': draftAnswers[inspKey] === 'na' }"
                      @click="answerBoolean(inspKey, 'na')">
                      N/A — Não aplicável
                    </button>
                  </div>

                  <!-- Number -->
                  <input v-else-if="inspectionField.field_type === 'number'"
                    v-model="draftAnswers[inspKey]"
                    class="field-input" type="number" step="any" placeholder="Informe um número"
                    @change="triggerAutoSave()" />

                  <!-- Date -->
                  <input v-else-if="inspectionField.field_type === 'date'"
                    v-model="draftAnswers[inspKey]"
                    class="field-input" type="date"
                    @change="triggerAutoSave()" />

                  <!-- Select -->
                  <select v-else-if="inspectionField.field_type === 'select'"
                    v-model="draftAnswers[inspKey]"
                    class="field-input"
                    @change="triggerAutoSave()">
                    <option value="">— Selecione —</option>
                    <option
                      v-for="opt in selectOptions(inspectionField.config_json ?? {})"
                      :key="opt" :value="opt">{{ opt }}</option>
                  </select>

                  <!-- Text -->
                  <input v-else-if="inspectionField.field_type === 'text'"
                    v-model="draftAnswers[inspKey]"
                    class="field-input" type="text" placeholder="Informe o valor"
                    @change="triggerAutoSave()" />

                  <!-- ── CONFORMIDADE ── -->
                  <div class="card-sep"><span class="card-sep-lbl">Conformidade</span></div>
                  <div class="conf-grid">
                    <button type="button" class="conf-btn conf-ok"
                      :class="{ active: conformityStatus[inspKey] === 'conforme' }"
                      @click="setConformityCard(inspKey, 'conforme')">
                      ✓ Conforme
                    </button>
                    <button type="button" class="conf-btn conf-err"
                      :class="{ active: conformityStatus[inspKey] === 'nao_conforme' }"
                      @click="setNaoConformeCard(inspKey)">
                      ✕ Não conforme
                    </button>
                  </div>
                  <!-- Justification preview (read-only) -->
                  <div
                    v-if="conformityStatus[inspKey] === 'nao_conforme' && conformityJustification[inspKey]"
                    class="conf-just-preview"
                    @click="setNaoConformeCard(inspKey)"
                  >
                    ✎ {{ conformityJustification[inspKey] }}
                  </div>
                  <p
                    v-if="inspectionField.field_type === 'boolean'"
                    class="swipe-hint"
                  >← Não conforme · Conforme →</p>

                  <!-- ── EVIDÊNCIAS DESTA INSTÂNCIA ── -->
                  <div class="card-sep"><span class="card-sep-lbl">Evidências{{ inspectionInstance?.componentLabel ? ' · ' + inspectionInstance.componentLabel : '' }}</span></div>
                  <div class="evid-row">
                    <button
                      type="button"
                      class="evid-btn"
                      :disabled="!!evidenceUploading[inspKey]"
                      @click="openEvidenceSheet(inspKey)"
                    >
                      <span>📎</span>
                      <span
                        v-if="currentFieldEvidenceCount > 0"
                        class="evid-badge"
                      >{{ currentFieldEvidenceCount }}</span>
                      <span>{{ evidenceUploading[inspKey] ? 'Enviando…' : 'Adicionar evidência' }}</span>
                    </button>
                    <div class="evid-thumbs">
                      <div
                        v-for="att in (evidenceAttachments[inspKey] ?? []).slice(0, 3)"
                        :key="att.id"
                        class="evid-thumb"
                      >
                        <img
                          v-if="att.mime_type.startsWith('image/')"
                          :src="att.file_url"
                          style="width:100%;height:100%;object-fit:cover;border-radius:4px;"
                        />
                        <span v-else style="font-size:16px;">📄</span>
                      </div>
                    </div>
                  </div>
                  <p v-if="evidenceErrors[inspKey]" style="font-size:11px;color:var(--sa-danger);margin-top:4px;">
                    {{ evidenceErrors[inspKey] }}
                  </p>

                </div><!-- /card-body -->
              </div><!-- /insp-card -->
            </div><!-- /insp-card-outer -->

            <!-- Dots -->
            <div class="card-dots">
              <div
                v-for="dot in nearbyDots"
                :key="dot.key"
                class="card-dot"
                :class="{
                  'card-dot--active': dot.isCurrent,
                  'card-dot--ok':  !dot.isCurrent && dot.status === 'conforme',
                  'card-dot--err': !dot.isCurrent && dot.status === 'nao_conforme',
                }"
              />
            </div>

          </template>
        </div><!-- /insp-fswipe -->

        <!-- ── 4. NAV ROW (fora do card) ── -->
        <div class="insp-fnav">
          <button
            type="button"
            class="btn-nav"
            :disabled="inspectionIndex === 0"
            @click="inspectionPrev"
          >← Anterior</button>
          <button type="button" class="btn-skip" @click="doSkip">Pular</button>
          <button
            type="button"
            class="btn-nav"
            :disabled="allAnswered"
            @click="inspectionNext"
          >Próximo →</button>
        </div>

      </div><!-- /insp-fullscreen -->
    </Teleport>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!--  FULLSCREEN LIST INSPECTION SHELL                                     -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <Teleport to="body">
      <div
        v-if="submission && inspectionMode && viewMode === 'list' && !isCompleted"
        class="insp-listshell"
      >
        <!-- ── HEADER LINHA 1 (idêntica ao card mode) ── -->
        <div class="insp-fhdr">
          <button type="button" class="insp-fback" @click="router.push({ name: 'submissions' })">
            <SvgIcon name="back" :size="16" />
          </button>
          <div class="insp-fhdr-info">
            <div class="insp-fhdr-name">{{ submission.form_name }}</div>
            <div class="insp-fhdr-sub"><span v-if="submission.asset_identifier">🏷 {{ submission.asset_identifier }} · </span>Em andamento</div>
          </div>
          <div class="insp-fhdr-vt">
            <button class="insp-fhdr-vt-btn" :class="String(viewMode) === 'list' ? 'active' : ''" @click="viewMode = 'list'">
              <span style="font-size:11px;">☰</span> Lista
            </button>
            <button class="insp-fhdr-vt-btn" :class="String(viewMode) === 'card' ? 'active' : ''" @click="viewMode = 'card'">
              <span style="font-size:11px;">▦</span> Cartão
            </button>
          </div>
          <div class="score-ring" :style="scoreRingStyle">
            <div class="score-ring-inner">{{ liveScore !== null ? liveScore + '%' : '—' }}</div>
          </div>
        </div>

        <!-- ── HEADER LINHA 2 (idêntica ao card mode) ── -->
        <div class="insp-fprog">
          <div class="insp-fprog-row">
            <div class="insp-fprog-bar">
              <div :style="{
                height: '100%',
                background: 'var(--sa-ok)',
                width: progressStats.total ? (progressStats.conformes / progressStats.total * 100) + '%' : '0%',
                transition: 'width .35s ease',
              }" />
              <div :style="{
                height: '100%',
                background: 'var(--sa-danger)',
                width: progressStats.total ? (progressStats.naoConformes / progressStats.total * 100) + '%' : '0%',
                transition: 'width .35s ease',
              }" />
            </div>
            <div class="insp-fprog-lbl">{{ progressStats.evaluated }}/{{ progressStats.total }}</div>
          </div>
          <!-- Legenda de cores -->
          <div style="display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:var(--sa-muted);padding:8px 0;">
            <span style="display:flex;align-items:center;gap:4px;">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-ok);flex-shrink:0;"></span>
              {{ progressStats.conformes }} Conforme
            </span>
            <span style="display:flex;align-items:center;gap:4px;">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-danger);flex-shrink:0;"></span>
              {{ progressStats.naoConformes }} Não conforme
            </span>
            <span v-if="progressStats.pending > 0" style="display:flex;align-items:center;gap:4px;">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-line);flex-shrink:0;"></span>
              {{ progressStats.pending }} Pendente
            </span>
          </div>
          <!-- Separador (idêntico ao card) -->
          <div style="height:1px;background:var(--sa-line);margin:0 -14px;"></div>
          <!-- Filtros dentro do fprog (mesmo comportamento dos section chips no card) -->
          <div class="insp-filter-bar">
            <button
              v-for="f in FILTERS"
              :key="f.id"
              class="insp-fchip"
              :class="[f.cls, { active: listFilter === f.id }]"
              @click="listFilter = f.id"
            >
              {{ f.label }}
              <span class="insp-fchip-n">{{ filterCount(f.id) }}</span>
            </button>
          </div>
        </div>

        <!-- Avisos não-bloqueantes da expansão por componente (Q2/Q3, DR-0002 T8) -->
        <div v-if="submission.warnings?.length" class="insp-warn-box insp-warn-box--shell">
          <div v-for="(w, wi) in submission.warnings" :key="wi" class="insp-warn-line">⚠ {{ w }}</div>
        </div>

        <!-- ── LISTA scrollável (fundo cinza) ── -->
        <div id="list-scroll-container" class="insp-list-container">
          <template v-for="row in filteredRows">

            <!-- Section header sticky -->
            <div
              v-if="row.kind === 'section'"
              :key="`sec-${row.field.key}`"
              v-show="visibleSectionKeys.has(row.field.key)"
              :id="`sec-${row.field.key}`"
              class="insp-list-sec-hdr"
            >
              <div class="insp-list-sec-ring" :style="sectionRingStyle(row.field.key)">
                <div class="insp-list-sec-ring-inner">
                  {{ sectionPct(row.field.key) === 100 ? '✓' : sectionPct(row.field.key) + '%' }}
                </div>
              </div>
              <span class="insp-list-sec-name">{{ row.field.label }}</span>
              <span class="insp-list-sec-cnt">{{ sectionProgress(row.field.key) }}</span>
            </div>

            <!-- Field row (uma por instância de componente) -->
            <div v-else :key="`row-${row.instance.key}`" :id="`list-row-${row.instance.key}`">
              <InspectionListRow
                :field="row.field"
                :component-label="row.instance.componentLabel"
                :position="instancePosition(row.instance)"
                :answer="draftAnswers[row.instance.key] ?? ''"
                :conformity-status="conformityStatus[row.instance.key]"
                :conformity-justification="conformityJustification[row.instance.key] ?? ''"
                :is-completed="isCompleted"
                :is-pending-required="pendingRequiredFields.includes(row.instance.key)"
                :evidence-count="evidenceAttachments[row.instance.key]?.length ?? 0"
                :is-expanded="expandedListKey === row.instance.key"
                @toggle="toggleListRow(row.instance.key)"
                @update-answer="v => { draftAnswers[row.instance.key] = v; triggerAutoSave() }"
                @set-conformity="s => setConformityList(row.instance.key, s)"
                @update-justification="v => { conformityJustification[row.instance.key] = v; triggerConformitySave() }"
                @request-evidence="openEvidenceSheet(row.instance.key)"
                @request-justification="() => { setConformity(row.instance.key, 'nao_conforme'); openJustificationSheet(row.instance.key) }"
              />
            </div>

          </template>
        </div>

        <!-- ── FOOTER fixo (Salvar / Finalizar) ── -->
        <div class="insp-lsfooter">
          <button type="button" class="btn-secondary" :disabled="submissionsStore.isSaving" @click="handleSave">
            {{ submissionsStore.isSaving ? 'Salvando…' : savedOnce ? '✓ Salvo' : 'Salvar rascunho' }}
          </button>
          <button type="button" class="btn-primary insp-lsfooter-finish" :disabled="submissionsStore.isSaving" @click="handleFinish">
            {{ submissionsStore.isSaving ? 'Finalizando…' : 'Finalizar inspeção' }}
          </button>
        </div>

        <p v-if="finishError" class="insp-lsfooter-err">{{ finishError }}</p>
      </div><!-- /insp-listshell -->
    </Teleport>

    <!-- ── Justification bottom sheet ── -->
    <Teleport to="body">
      <div
        class="sheet-overlay"
        :class="{ open: showJustificationSheet }"
        @click="closeJustificationSheet()"
      >
        <div class="sheet" @click.stop>
          <div class="sheet-handle"></div>
          <div class="sheet-hdr">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:3px;">
              <div style="width:28px;height:28px;border-radius:50%;background:var(--sa-err-bg);border:2px solid var(--sa-err-bd);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:var(--sa-danger);">✕</div>
              <div class="sheet-title">Não conforme</div>
            </div>
            <div class="sheet-sub">Descreva o problema encontrado</div>
          </div>
          <div class="sheet-body">
            <div v-if="justificationFieldKey" class="sheet-field-ctx">
              {{ fields.find(f => f.key === justificationFieldKey)?.label ?? justificationFieldKey }}
            </div>
            <textarea
              v-if="justificationFieldKey"
              v-model="conformityJustification[justificationFieldKey]"
              class="sheet-textarea"
              placeholder="Descreva o motivo da não conformidade..."
              rows="4"
              @input="triggerConformitySave(); justificationError = null"
            />
            <p v-if="justificationError" style="font-size:12px;color:var(--sa-danger);margin-top:8px;font-weight:600;">
              {{ justificationError }}
            </p>
          </div>
          <div class="sheet-acts">
            <button type="button" class="sheet-cancel" @click="showJustificationSheet = false; justificationError = null">Cancelar</button>
            <button
              type="button"
              class="sheet-confirm"
              :disabled="!justificationFieldKey || !(conformityJustification[justificationFieldKey] || '').trim()"
              @click="confirmJustification()"
            >Confirmar</button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── Evidence bottom sheet ── -->
    <Teleport to="body">
      <div
        class="sheet-overlay"
        :class="{ open: showEvidenceSheet }"
        @click="closeEvidenceSheet()"
      >
        <div class="sheet" @click.stop>
          <div class="sheet-handle"></div>
          <div class="sheet-hdr">
            <div class="sheet-title">Evidências</div>
            <div v-if="evidenceSheetKey" class="sheet-sub">
              {{ evidenceSheetLabel }}
            </div>
          </div>
          <div class="sheet-body">
            <div v-if="evidenceSheetKey">
              <div
                v-for="att in (evidenceAttachments[evidenceSheetKey] ?? [])"
                :key="att.id"
                class="evid-sheet-item"
              >
                <div class="evid-sheet-thumb">
                  {{ att.mime_type.startsWith('image/') ? '🖼' : att.mime_type === 'application/pdf' ? '📄' : '📎' }}
                </div>
                <a :href="att.file_url" target="_blank" rel="noopener" class="evid-sheet-name">
                  {{ att.file_url.split('/').pop() }}
                </a>
                <button
                  type="button"
                  class="evid-sheet-del"
                  @click="evidenceSheetKey && handleEvidenceDelete(evidenceSheetKey, att.id)"
                >×</button>
              </div>
              <label class="add-evid-btn">
                {{ evidenceUploading[evidenceSheetKey] ? 'Enviando…' : '📎 Adicionar evidência' }}
                <input
                  type="file"
                  style="display:none;"
                  accept="image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo,audio/mpeg,audio/wav,audio/ogg,audio/mp4,application/pdf"
                  :disabled="!!evidenceUploading[evidenceSheetKey]"
                  @change="uploadEvidenceFromSheet"
                />
              </label>
              <p v-if="evidenceErrors[evidenceSheetKey]" style="color:var(--sa-danger);font-size:12px;margin-top:8px;">
                {{ evidenceErrors[evidenceSheetKey] }}
              </p>
            </div>
          </div>
          <div class="sheet-acts">
            <button type="button" class="sheet-confirm" @click="closeEvidenceSheet()">Fechar</button>
          </div>
        </div>
      </div>
    </Teleport>

  </AppShell>
</template>

<style scoped>
/* ── Score ring (A9) ── */
.score-ring {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.score-ring-inner {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  color: var(--sa-muted);
}

/* ── Section chips inspection (A10) ── */
.insp-sec-chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 4px;
  padding-top: 12px;
  scrollbar-width: none;
}
.insp-sec-chips::-webkit-scrollbar { display: none; }

.insp-sec-chip {
  padding: 4px 11px;
  border-radius: 99px;
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  border: 1px solid var(--sa-line);
  background: #fff;
  color: var(--sa-muted);
  white-space: nowrap;
  flex-shrink: 0;
  font-family: inherit;
  transition: all .15s;
}
.insp-sec-chip--done   { background: var(--sa-ok);   border-color: var(--sa-ok);   color: #fff; }
.insp-sec-chip--active { background: var(--sa-brand-soft); border-color: var(--sa-brand); color: var(--sa-brand); }
.insp-sec-chip--done.insp-sec-chip--active { background: var(--sa-ok); border-color: var(--sa-ok); color: #fff; opacity: .85; }

.insp-sec-pct { opacity: .75; font-size: 10px; margin-left: 3px; }

/* ── Boolean buttons ── */
.bool-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 16px 12px;
  border-radius: 12px;
  border: 2px solid var(--sa-line);
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  color: var(--sa-muted);
  cursor: pointer;
  transition: border-color .15s, background .15s, color .15s, transform .1s;
}
.bool-btn:active { transform: scale(.96); }
.bool-btn:disabled { opacity: .45; cursor: not-allowed; }

.bool-sim:hover:not(:disabled) { border-color: var(--sa-ok); color: var(--sa-ok); background: var(--sa-ok-bg); }
.bool-sim.bool-btn--active { border-color: var(--sa-ok); color: var(--sa-ok); background: var(--sa-ok-bg); }

.bool-nao:hover:not(:disabled) { border-color: var(--sa-danger); color: var(--sa-danger); background: var(--sa-err-bg); }
.bool-nao.bool-btn--active { border-color: var(--sa-danger); color: var(--sa-danger); background: var(--sa-err-bg); }

.bool-na { grid-column: 1 / -1; flex-direction: row; padding: 10px 16px; font-size: 12px; }
.bool-na:hover:not(:disabled) { border-color: var(--sa-warn); color: var(--sa-warn); background: var(--sa-warn-bg); }
.bool-na.bool-btn--active { border-color: var(--sa-warn); color: var(--sa-warn); background: var(--sa-warn-bg); }

/* Small bool buttons (list view) */
.bool-btn-sm {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--sa-line);
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  color: var(--sa-muted);
  cursor: pointer;
  transition: border-color .15s, background .15s, color .15s;
}
.bool-btn-sm:disabled { opacity: .45; cursor: not-allowed; }
.bool-btn-sm.bool-sim.bool-btn--active { border-color: var(--sa-ok); color: var(--sa-ok); background: var(--sa-ok-bg); }
.bool-btn-sm.bool-nao.bool-btn--active { border-color: var(--sa-danger); color: var(--sa-danger); background: var(--sa-err-bg); }
.bool-btn-sm.bool-na.bool-btn--active  { border-color: var(--sa-warn); color: var(--sa-warn); background: var(--sa-warn-bg); }

/* Active view toggle */
.btn-view-active {
  background: var(--sa-brand-soft);
  border-color: var(--sa-brand);
  color: var(--sa-brand);
}

/* ── Bottom sheets ── */
.sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.5);
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  opacity: 0;
  pointer-events: none;
  transition: opacity .25s;
  backdrop-filter: blur(2px);
}
.sheet-overlay.open { opacity: 1; pointer-events: all; }

.sheet {
  width: 100%;
  background: #fff;
  border-radius: 20px 20px 0 0;
  transform: translateY(100%);
  transition: transform .28s cubic-bezier(.32,1,.4,1);
  max-height: 85dvh;
  overflow-y: auto;
}
.sheet-overlay.open .sheet { transform: translateY(0); }

.sheet-handle {
  width: 36px;
  height: 4px;
  background: var(--sa-line);
  border-radius: 99px;
  margin: 12px auto 0;
}
.sheet-hdr {
  padding: 14px 20px 12px;
  border-bottom: 1px solid var(--sa-line);
}
.sheet-title { font-size: 16px; font-weight: 700; color: var(--sa-text); }
.sheet-sub   { font-size: 12px; color: var(--sa-muted); margin-top: 2px; }
.sheet-body  { padding: 14px 20px; }

.sheet-field-ctx {
  font-size: 13px;
  font-weight: 600;
  color: var(--sa-text);
  background: var(--sa-err-bg);
  border: 1px solid var(--sa-err-bd);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 12px;
}
.sheet-textarea {
  width: 100%;
  border: 1px solid var(--sa-line);
  border-radius: 10px;
  padding: 11px;
  font-size: 14px;
  font-family: inherit;
  color: var(--sa-text);
  outline: none;
  resize: vertical;
  min-height: 80px;
}
.sheet-textarea:focus { border-color: var(--sa-danger); box-shadow: 0 0 0 3px rgba(220,38,38,.1); }

.sheet-acts {
  display: flex;
  gap: 10px;
  padding: 12px 20px 20px;
}
.sheet-cancel {
  flex: 1;
  padding: 12px;
  border: 1px solid var(--sa-line);
  border-radius: 10px;
  background: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
}
.sheet-confirm {
  flex: 2;
  padding: 12px;
  border: none;
  border-radius: 10px;
  background: var(--sa-danger);
  color: #fff;
  font-family: inherit;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

/* Evidence sheet items */
.evid-sheet-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--sa-line);
}
.evid-sheet-thumb {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: var(--sa-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}
.evid-sheet-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--sa-text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-decoration: none;
}
.evid-sheet-del {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--sa-danger);
  font-size: 20px;
  flex-shrink: 0;
  line-height: 1;
  padding: 4px;
}
.add-evid-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  border: 1px dashed var(--sa-brand);
  border-radius: 10px;
  background: none;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  color: var(--sa-brand);
  cursor: pointer;
  margin-top: 12px;
}

/* ══════════════════════════════════════════════════════════════════════════════
   FULLSCREEN CARD INSPECTION OVERLAY
   ══════════════════════════════════════════════════════════════════════════════ */

/* Outer container: preenche área de conteúdo (ao lado do sidebar no desktop) */
.insp-fullscreen {
  position: fixed;
  inset: 0;
  z-index: 200; /* mobile: cobre tudo (sem sidebar) */
  background: var(--sa-bg, #f1f5f9);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

@media (min-width: 768px) {
  .insp-fullscreen {
    left: 248px; /* sidebar width — fica à direita do menu */
    z-index: 50; /* abaixo do sidebar (z-index: 100) no desktop */
  }
}

/* ══════════════════════════════════════════════════════════════════════════════
   FULLSCREEN LIST INSPECTION SHELL
   ══════════════════════════════════════════════════════════════════════════════ */
.insp-listshell {
  position: fixed;
  inset: 0;
  z-index: 200; /* mobile: cobre tudo */
  background: var(--sa-bg, #f1f5f9);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
@media (min-width: 768px) {
  .insp-listshell {
    left: 248px;
    z-index: 50; /* abaixo do sidebar no desktop */
  }
}

/* Filter bar dentro do fprog (lista): mesmo espaçamento dos sec-chips no card */
.insp-fprog .insp-filter-bar {
  padding-top: 12px;
  padding-bottom: 4px;
  margin-bottom: 0;
}

/* Lista scrollável (fundo cinza, separada do header branco) */
.insp-listshell .insp-list-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 14px 14px;
  background: var(--sa-bg);
}

/* Footer fixo */
.insp-lsfooter {
  display: flex;
  gap: 10px;
  padding: 10px 14px;
  background: #fff;
  border-top: 1px solid var(--sa-line);
  flex-shrink: 0;
}
.insp-lsfooter .btn-secondary { flex: 1; }
.insp-lsfooter-finish { flex: 2; }
.insp-lsfooter-err {
  position: absolute;
  bottom: 60px;
  left: 14px;
  right: 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-danger);
  background: var(--sa-err-bg);
  border: 1px solid var(--sa-err-bd);
  border-radius: 8px;
  padding: 8px 12px;
}

/* ── Header ── */
.insp-fhdr {
  background: #fff;
  border-bottom: 1px solid var(--sa-line);
  padding: 0 14px;
  height: 52px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}
.insp-fback {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--sa-line);
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--sa-muted);
  cursor: pointer;
  flex-shrink: 0;
}
.insp-fhdr-info { flex: 1; min-width: 0; }
.insp-fhdr-vt {
  display: flex;
  background: var(--sa-bg);
  border-radius: 8px;
  padding: 3px;
  gap: 2px;
  flex-shrink: 0;
}
.insp-fhdr-vt-btn {
  padding: 4px 10px;
  border-radius: 5px;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 11px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}
.insp-fhdr-vt-btn.active {
  background: #fff;
  color: var(--sa-brand);
  box-shadow: 0 1px 3px rgba(0,0,0,.1);
  pointer-events: none;
}
.insp-fhdr-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--sa-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.insp-fhdr-sub { font-size: 10px; color: var(--sa-muted); }

/* ── Progress area ── */
.insp-fprog {
  background: #fff;
  border-top: 1px solid var(--sa-line);
  border-bottom: 1px solid var(--sa-line);
  padding: 10px 14px;
  flex-shrink: 0;
}
.insp-fprog-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.insp-fprog-bar {
  flex: 1;
  height: 8px;
  background: var(--sa-line);
  border-radius: 99px;
  overflow: hidden;
  display: flex;
}
.insp-fprog-lbl {
  font-size: 11px;
  font-weight: 700;
  color: var(--sa-muted);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

/* ── Swipe zone ── */
.insp-fswipe {
  flex: 1;
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 10px 12px;
  gap: 10px;
}

/* ── Card wrapper: max-width centered ── */
.insp-card-outer {
  width: 100%;
  max-width: 520px;
  position: relative;
}

/* ── Card overrides for fullscreen mode ── */
.insp-fullscreen .insp-card {
  border-radius: 20px;
  border: none;
  box-shadow: 0 8px 32px rgba(0,0,0,.12), 0 2px 8px rgba(0,0,0,.06);
  padding: 0;
  overflow: hidden;
  cursor: grab;
  max-height: calc(100dvh - 52px - 80px - 72px - 48px); /* viewport minus header/prog/nav/dots */
  overflow-y: auto;
}
.insp-fullscreen .insp-card:active { cursor: grabbing; }

/* ── Card header (title bar) ── */
.card-hdr {
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--sa-line);
  transition: background .2s;
  flex-shrink: 0;
}
.card-sec {
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--sa-brand);
}
.card-meta { display: flex; align-items: center; gap: 6px; }
.card-weight {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--sa-brand-soft);
  color: var(--sa-brand);
}
.card-counter {
  font-size: 10px;
  font-weight: 700;
  color: var(--sa-muted);
  font-variant-numeric: tabular-nums;
}
.card-status {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 99px;
}
.card-status--ok   { background: var(--sa-ok-bg);  color: var(--sa-ok); }
.card-status--err  { background: var(--sa-err-bg); color: var(--sa-danger); }
.card-status--pend { background: #f1f5f9;           color: var(--sa-muted); }

/* ── Card body ── */
.card-body { padding: 14px; display: flex; flex-direction: column; gap: 0; }
.card-type-lbl {
  font-size: 9px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--sa-muted);
  margin-bottom: 5px;
}
.card-label {
  font-size: 16px;
  font-weight: 700;
  color: var(--sa-text);
  line-height: 1.3;
}
.card-req {
  font-size: 9px;
  font-weight: 700;
  color: var(--sa-danger);
  text-transform: uppercase;
  letter-spacing: .06em;
  margin-top: 4px;
}
.card-instr {
  font-size: 12px;
  color: var(--sa-muted);
  background: var(--sa-bg);
  border-left: 3px solid var(--sa-brand);
  padding: 6px 9px;
  border-radius: 0 6px 6px 0;
  margin-top: 8px;
  line-height: 1.5;
}

/* ── Component chip (campo escopado, DR-0002 T8) ── */
.card-comp-chip {
  display: inline-block;
  margin-top: 6px;
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 99px;
  background: #f5f3ff;
  color: #7c3aed;
}

/* ── Avisos não-bloqueantes da expansão (Q2/Q3) ── */
.insp-warn-box {
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: var(--sa-warn-bg);
  border: 1px solid var(--sa-warn);
}
.insp-warn-box--shell {
  margin: 8px 12px 0 12px;
}
.insp-warn-line {
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-warn);
  line-height: 1.5;
}

/* ── Section separator ── */
.card-sep {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 8px;
}
.card-sep::before,
.card-sep::after { content: ''; flex: 1; height: 1px; background: var(--sa-line); }
.card-sep-lbl {
  font-size: 9px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--sa-muted);
  white-space: nowrap;
}

/* ── Boolean buttons (fullscreen card) ── */
.bool-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.b-icon { font-size: 22px; line-height: 1; }
.b-lbl  { font-size: 14px; font-weight: 700; color: var(--sa-text); }
.na-btn {
  width: 100%;
  margin-top: 6px;
  padding: 9px 14px;
  border-radius: 10px;
  border: 1px solid var(--sa-line);
  background: #fff;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
  transition: all .12s;
}
.na-btn--active { border-color: var(--sa-warn); background: var(--sa-warn-bg); color: var(--sa-warn); }

/* ── Field inputs inside card ── */
.field-input {
  width: 100%;
  padding: 11px 13px;
  border: 1px solid var(--sa-line);
  border-radius: 10px;
  font-size: 15px;
  font-family: inherit;
  outline: none;
  color: var(--sa-text);
  background: #fff;
  box-sizing: border-box;
}
.field-input:focus { border-color: var(--sa-brand); box-shadow: 0 0 0 3px rgba(37,99,235,.1); }

/* ── Conformity buttons ── */
.conf-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.conf-btn {
  padding: 10px;
  border-radius: 10px;
  border: 1px solid var(--sa-line);
  background: #fff;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  color: var(--sa-muted);
  cursor: pointer;
  transition: all .12s;
  text-align: center;
}
.conf-btn:active { transform: scale(.96); }
.conf-ok.active  { border-color: var(--sa-ok);     background: var(--sa-ok-bg);  color: var(--sa-ok); }
.conf-err.active { border-color: var(--sa-danger);  background: var(--sa-err-bg); color: var(--sa-danger); }
.conf-just-preview {
  margin-top: 6px;
  font-size: 11px;
  color: var(--sa-danger);
  background: var(--sa-err-bg);
  border: 1px solid var(--sa-err-bd);
  border-radius: 6px;
  padding: 5px 9px;
  cursor: pointer;
  line-height: 1.4;
}
.swipe-hint {
  font-size: 10px;
  color: var(--sa-muted);
  text-align: center;
  margin-top: 6px;
  opacity: .55;
}

/* ── Evidence row ── */
.evid-row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.evid-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1px solid var(--sa-line);
  border-radius: 8px;
  background: #fff;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
  transition: all .12s;
}
.evid-btn:hover:not(:disabled) { border-color: var(--sa-brand); color: var(--sa-brand); background: var(--sa-brand-soft); }
.evid-badge {
  background: var(--sa-brand);
  color: #fff;
  border-radius: 99px;
  padding: 1px 6px;
  font-size: 10px;
  font-weight: 800;
  min-width: 18px;
  text-align: center;
}
.evid-thumbs { display: flex; gap: 4px; }
.evid-thumb {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  background: var(--sa-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--sa-line);
  overflow: hidden;
}

/* ── Stamps ── */
.stamp {
  position: absolute;
  top: 18px;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: .08em;
  border: 3px solid;
  pointer-events: none;
  z-index: 10;
  text-transform: uppercase;
}
.stamp-conf  { left: 14px;  transform: rotate(15deg);  color: var(--sa-ok);     border-color: var(--sa-ok);     }
.stamp-nconf { right: 14px; transform: rotate(-15deg); color: var(--sa-danger); border-color: var(--sa-danger); }

/* ── Swipe side indicators ── */
.insp-find {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  pointer-events: none;
  z-index: 5;
  transition: opacity .05s;
}
.insp-find--left  { left: 4px; }
.insp-find--right { right: 4px; }
.ind-icon {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  color: #fff;
}
.ind-ok  { background: var(--sa-ok);     box-shadow: 0 4px 14px rgba(22,163,74,.4); }
.ind-err { background: var(--sa-danger); box-shadow: 0 4px 14px rgba(220,38,38,.4); }
.ind-lbl { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em; }
.ind-lbl--ok  { color: var(--sa-ok); }
.ind-lbl--err { color: var(--sa-danger); }

/* ── Dots ── */
.card-dots {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex-shrink: 0;
}
.card-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--sa-line);
  transition: all .2s;
  flex-shrink: 0;
}
.card-dot--active { width: 20px; border-radius: 3px; background: var(--sa-brand); }
.card-dot--ok     { background: var(--sa-ok); }
.card-dot--err    { background: var(--sa-danger); }
.card-dot--na     { background: var(--sa-warn); }

/* ── Done state ── */
.insp-fdone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  text-align: center;
}
.done-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--sa-ok-bg);
  border: 3px solid var(--sa-ok);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 36px;
  margin-bottom: 16px;
}
.done-score {
  font-size: 44px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  margin-bottom: 6px;
}
.done-sub   { font-size: 13px; color: var(--sa-muted); margin-bottom: 20px; }
.done-btn {
  padding: 13px 28px;
  border: none;
  border-radius: 12px;
  background: var(--sa-brand);
  color: #fff;
  font-family: inherit;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}

/* ── Nav row (outside card) ── */
.insp-fnav {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #fff;
  border-top: 1px solid var(--sa-line);
  flex-shrink: 0;
}
.btn-nav {
  flex: 1;
  padding: 10px;
  border: 1px solid var(--sa-line);
  border-radius: 10px;
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  color: var(--sa-text);
  cursor: pointer;
  transition: background .15s;
}
.btn-nav:hover:not(:disabled) { background: var(--sa-bg); }
.btn-nav:disabled { opacity: .35; cursor: not-allowed; }
.btn-skip {
  padding: 10px 14px;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
  border-radius: 8px;
  flex-shrink: 0;
}
.btn-skip:hover { color: var(--sa-text); background: var(--sa-bg); }

/* View toggle bar */
.insp-view-toggle-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 0; margin-bottom: 8px; flex-shrink: 0;
}
.insp-vt-seg {
  display: flex; background: var(--sa-bg); border-radius: 8px; padding: 3px; gap: 2px;
}
.insp-vt-btn {
  padding: 5px 14px; border-radius: 6px; border: none; background: none;
  font-family: inherit; font-size: 12px; font-weight: 600; color: var(--sa-muted); cursor: pointer;
  display: flex; align-items: center; gap: 5px;
}
.insp-vt-icon {
  font-size: 11px; display: inline-flex; align-items: center;
}
.insp-vt-btn.active {
  background: #fff; color: var(--sa-brand); box-shadow: 0 1px 3px rgba(0,0,0,.1);
}
.insp-jump-pend {
  display: flex; align-items: center; gap: 6px; margin-left: auto;
  padding: 5px 11px; border: 1px solid var(--sa-line); border-radius: 8px;
  background: #fff; font-family: inherit; font-size: 11px; font-weight: 700;
  color: var(--sa-warn); cursor: pointer; white-space: nowrap;
}
.insp-jump-pend:disabled { opacity: .4; pointer-events: none; }
.insp-jump-pend:hover:not(:disabled) { border-color: var(--sa-warn); background: var(--sa-warn-bg); }
.insp-jump-pend-cnt {
  background: var(--sa-warn); color: #fff; border-radius: 99px;
  padding: 0 6px; font-size: 10px; min-width: 18px; text-align: center;
}

/* Filter bar */
.insp-filter-bar {
  display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; margin-bottom: 4px;
  -webkit-overflow-scrolling: touch; scrollbar-width: none; flex-shrink: 0;
}
.insp-filter-bar--with-sep {
  padding-top: 8px;
  border-top: 1px solid var(--sa-line);
}
.insp-filter-bar::-webkit-scrollbar { display: none; }
.insp-fchip {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: 99px; font-size: 11px; font-weight: 700;
  border: 1px solid var(--sa-line); background: #fff; color: var(--sa-muted);
  white-space: nowrap; flex-shrink: 0; cursor: pointer; font-family: inherit;
  transition: all .15s;
}
.insp-fchip.active { border-color: var(--sa-brand); background: var(--sa-brand-soft); color: var(--sa-brand); }
.insp-fchip.warn   { border-color: var(--sa-warn-bd, #fde68a); }
.insp-fchip.ok     { border-color: var(--sa-ok-bd); }
.insp-fchip.err    { border-color: var(--sa-err-bd); }
.insp-fchip.warn.active { border-color: var(--sa-warn); background: var(--sa-warn-bg); color: var(--sa-warn); }
.insp-fchip.ok.active   { border-color: var(--sa-ok);  background: var(--sa-ok-bg);  color: var(--sa-ok); }
.insp-fchip.err.active  { border-color: var(--sa-danger); background: var(--sa-err-bg); color: var(--sa-danger); }
.insp-fchip-n {
  background: rgba(0,0,0,.08); border-radius: 99px; padding: 0 5px;
  font-size: 10px; min-width: 16px; text-align: center;
}

/* List container */
.insp-list-container {
  overflow-y: auto; flex: 1; -webkit-overflow-scrolling: touch;
}
.insp-list-container::-webkit-scrollbar { width: 3px; }
.insp-list-container::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 99px; }

/* Section header */
.insp-list-sec-hdr {
  position: sticky; top: 0; z-index: 10;
  background: var(--sa-bg);
  border-top: 1px solid var(--sa-line); border-bottom: 1px solid var(--sa-line);
  padding: 5px 12px; display: flex; align-items: center; gap: 8px;
}
.insp-list-sec-ring {
  width: 28px; height: 28px; border-radius: 50%; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.insp-list-sec-ring-inner {
  width: 20px; height: 20px; border-radius: 50%; background: var(--sa-bg);
  display: flex; align-items: center; justify-content: center;
  font-size: 8px; font-weight: 800; font-family: var(--mono, 'DM Mono', monospace); color: var(--sa-muted);
}
.insp-list-sec-name {
  font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .1em;
  color: var(--sa-muted); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.insp-list-sec-cnt {
  font-size: 10px; font-weight: 700; color: var(--sa-muted);
  font-family: 'DM Mono', monospace; white-space: nowrap; flex-shrink: 0;
}
</style>
