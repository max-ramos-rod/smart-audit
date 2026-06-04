<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import InspectionFieldRow from '@/components/submissions/InspectionFieldRow.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { scoreColorVar } from '@/utils/score'
import { createAttachment, deleteAttachment, listAttachments } from '@/services/attachments.service'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchFormVersion } from '@/services/forms.service'
import { saveConformity } from '@/services/submissions.service'
import { uploadFile } from '@/services/uploads.service'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
import type { AttachmentItem } from '@/types/attachments'
import type { FormVersion } from '@/types/forms'

const route = useRoute()
const router = useRouter()
const submissionsStore = useSubmissionsStore()

// ── State ─────────────────────────────────────────────────────────────────────

const formVersion    = ref<FormVersion | null>(null)
const draftAnswers   = reactive<Record<string, string>>({})
const saveError      = ref<string | null>(null)
const finishError    = ref<string | null>(null)
const savedOnce      = ref(false)

// Inspection mode
const inspectionMode  = ref(false)
const inspectionIndex = ref(0)

// View mode inside inspection: 'card' | 'list'
const viewMode = ref<'card' | 'list'>('card')

// Swipe state
const swipeDeltaX  = ref(0)
const swipeStartX  = ref(0)
const isSwiping    = ref(false)
const swipeExiting = ref<'left' | 'right' | null>(null)

// Progressive list loading
const LIST_PAGE    = 50
const listViewLimit = ref(LIST_PAGE)

// Evidence per field
const evidenceAttachments = reactive<Record<string, AttachmentItem[]>>({})
const evidenceUploading   = reactive<Record<string, boolean>>({})
const evidenceErrors      = reactive<Record<string, string>>({})
const evidenceLoaded      = ref(false)

// Conformity per field
const conformityStatus        = reactive<Record<string, 'conforme' | 'nao_conforme'>>({})
const conformityJustification = reactive<Record<string, string>>({})

// Justification bottom sheet
const showJustificationSheet = ref(false)
const justificationFieldKey  = ref<string | null>(null)

// Evidence bottom sheet
const showEvidenceSheet = ref(false)
const evidenceSheetKey  = ref<string | null>(null)

const pendingRequiredFields = ref<string[]>([])

// ── Derived ───────────────────────────────────────────────────────────────────

const submissionId = computed(() => route.params.id as string)
const submission   = computed(() => submissionsStore.current)
const isCompleted  = computed(() => submission.value?.status === 'completed')

const fields = computed(() =>
  [...(formVersion.value?.fields ?? [])].sort((a, b) => a.position - b.position),
)

// Fields that accept answers (skip section dividers)
const answerableFields = computed(() =>
  fields.value.filter((f) => f.field_type !== 'section'),
)

// ── Progress counters ─────────────────────────────────────────────────────────

const progressStats = computed(() => {
  let conformes    = 0
  let naoConformes = 0

  for (const field of answerableFields.value) {
    const s = conformityStatus[field.key]
    if (s === 'conforme') conformes++
    else if (s === 'nao_conforme') naoConformes++
  }

  const total      = answerableFields.value.length
  const evaluated  = conformes + naoConformes
  const pending    = total - evaluated
  const percentage = total === 0 ? 0 : Math.round((evaluated / total) * 100)

  return { conformes, naoConformes, evaluated, pending, total, percentage }
})

// Real-time weighted score based on conformity status (mirrors backend calculate_score logic)
const liveScore = computed((): number | null => {
  let wConformes = 0
  let wTotal     = 0
  for (const field of answerableFields.value) {
    const s      = conformityStatus[field.key]
    if (!s) continue
    const weight = (field.config_json?.weight as number | undefined) ?? 1
    wTotal += weight
    if (s === 'conforme') wConformes += weight
  }
  return wTotal === 0 ? null : Math.round((wConformes / wTotal) * 100)
})

// All answerable fields have a conformity status
const allAnswered = computed(() => progressStats.value.pending === 0 && progressStats.value.total > 0)

// Score ring style (conic-gradient based on liveScore)
const scoreRingStyle = computed(() => {
  if (liveScore.value === null) return { background: 'conic-gradient(#e2e8f0 100%, #e2e8f0 0)' }
  const pct   = liveScore.value
  const color = pct >= 85 ? '#16a34a' : pct >= 65 ? '#d97706' : '#dc2626'
  return { background: `conic-gradient(${color} ${pct}%, #e2e8f0 0)`, transition: 'background .5s' }
})

// Total evidence files across all fields
const totalEvidenceCount = computed(() =>
  Object.values(evidenceAttachments).reduce((sum, arr) => sum + arr.length, 0),
)

// ── Sections ──────────────────────────────────────────────────────────────────

const formSections = computed(() =>
  fields.value
    .filter((f) => f.field_type === 'section')
    .map((section, idx, arr) => {
      const nextSectionPos = arr[idx + 1]?.position ?? Infinity
      const sectionItems   = answerableFields.value.filter(
        (f) => f.position > section.position && f.position < nextSectionPos,
      )
      const evaluated = sectionItems.filter((f) => conformityStatus[f.key]).length
      const pct = sectionItems.length === 0 ? 100 : Math.round((evaluated / sectionItems.length) * 100)
      return { key: section.key, label: section.label, pct }
    }),
)

// ── Inspection card (current field) ───────────────────────────────────────────

const inspectionField = computed(() => answerableFields.value[inspectionIndex.value] ?? null)

const inspectionSectionLabel = computed(() => {
  const field = inspectionField.value
  if (!field) return ''
  const allVisible = fields.value
  const idx = allVisible.findIndex((f) => f.key === field.key)
  for (let i = idx - 1; i >= 0; i--) {
    if (allVisible[i].field_type === 'section') return allVisible[i].label
  }
  return ''
})

function fieldConformityStatus(fieldKey: string): 'pending' | 'conformes' | 'nao_conformes' {
  const s = conformityStatus[fieldKey]
  if (s === 'conforme') return 'conformes'
  if (s === 'nao_conforme') return 'nao_conformes'
  return 'pending'
}

const currentFieldStatus = computed(() => {
  if (!inspectionField.value) return 'pending'
  return fieldConformityStatus(inspectionField.value.key)
})

// ── Navigation ────────────────────────────────────────────────────────────────

function enterInspectionMode() {
  inspectionIndex.value = 0
  viewMode.value = 'card'
  inspectionMode.value = true
}

function inspectionNext() {
  if (inspectionIndex.value < answerableFields.value.length - 1) {
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
  const firstInSection = answerableFields.value.find((f) => f.position > sectionField.position)
  if (firstInSection) {
    inspectionIndex.value = answerableFields.value.indexOf(firstInSection)
  }
}

// ── Touch / swipe ─────────────────────────────────────────────────────────────

function onTouchStart(e: TouchEvent) {
  swipeStartX.value = e.touches[0].clientX
  isSwiping.value   = true
  swipeDeltaX.value = 0
}

function onTouchMove(e: TouchEvent) {
  if (!isSwiping.value) return
  swipeDeltaX.value = e.touches[0].clientX - swipeStartX.value
}

function onTouchEnd() {
  if (!isSwiping.value) return
  isSwiping.value = false

  const field = inspectionField.value
  const delta = swipeDeltaX.value
  swipeDeltaX.value = 0

  if (!field || Math.abs(delta) < 80) return

  if (delta > 0) {
    setConformity(field.key, 'conforme')
  } else {
    setConformity(field.key, 'nao_conforme')
    openJustificationSheet(field.key)
  }
}

// Card transform style driven by swipe delta
const cardSwipeStyle = computed(() => {
  if (!isSwiping.value && swipeDeltaX.value === 0) {
    if (swipeExiting.value === 'right') return { transform: 'translateX(120%) rotate(12deg)', opacity: '0', transition: 'transform .22s ease, opacity .22s ease' }
    if (swipeExiting.value === 'left')  return { transform: 'translateX(-120%) rotate(-12deg)', opacity: '0', transition: 'transform .22s ease, opacity .22s ease' }
    return {}
  }
  const rotate  = (swipeDeltaX.value / 400) * 12
  const opacity = Math.max(0.5, 1 - Math.abs(swipeDeltaX.value) / 400)
  return {
    transform: `translateX(${swipeDeltaX.value}px) rotate(${rotate}deg)`,
    opacity: String(opacity),
    transition: isSwiping.value ? 'none' : 'transform .22s ease, opacity .22s ease',
  }
})

// Swipe indicator opacity (right = Conforme, left = Não conforme)
const rightIndicatorOpacity = computed(() => Math.min(1, Math.max(0, swipeDeltaX.value / 100)))
const leftIndicatorOpacity  = computed(() => Math.min(1, Math.max(0, -swipeDeltaX.value / 100)))

// ── Boolean quick-answer buttons ──────────────────────────────────────────────

function answerBoolean(fieldKey: string, value: 'true' | 'false' | 'na') {
  draftAnswers[fieldKey] = value
  triggerAutoSave()
}

// Used only in card view: sets conformity and advances for 'conforme', stays for 'nao_conforme'
function setConformityCard(fieldKey: string, status: 'conforme' | 'nao_conforme') {
  setConformity(fieldKey, status)
  if (status === 'conforme') {
    setTimeout(() => inspectionNext(), 300)
  }
}

// ── Sheet helpers ─────────────────────────────────────────────────────────────

function openJustificationSheet(fieldKey: string) {
  justificationFieldKey.value = fieldKey
  showJustificationSheet.value = true
}
function closeJustificationSheet() {
  showJustificationSheet.value = false
}

function openEvidenceSheet(fieldKey: string) {
  evidenceSheetKey.value = fieldKey
  showEvidenceSheet.value = true
}
function closeEvidenceSheet() {
  showEvidenceSheet.value = false
}

// ── Conformity ────────────────────────────────────────────────────────────────

let conformitySaveTimer: ReturnType<typeof setTimeout> | null = null

function setConformity(fieldKey: string, status: 'conforme' | 'nao_conforme') {
  conformityStatus[fieldKey] = status
  triggerConformitySave()
}

function triggerConformitySave() {
  if (conformitySaveTimer) clearTimeout(conformitySaveTimer)
  conformitySaveTimer = setTimeout(async () => {
    const items = Object.entries(conformityStatus).map(([field_key, status]) => ({
      field_key,
      status,
      justification: conformityJustification[field_key] || null,
    }))
    if (items.length === 0) return
    try {
      await saveConformity(submissionId.value, { items })
    } catch { /* silent */ }
  }, 800)
}

// ── Auto-save (debounced) ─────────────────────────────────────────────────────

let autoSaveTimer: ReturnType<typeof setTimeout> | null = null
function triggerAutoSave() {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(async () => {
    try {
      await submissionsStore.updateAnswers(submissionId.value, { answers: buildPayload() })
      savedOnce.value = true
    } catch { /* silent — user can manually save */ }
  }, 1200)
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não', text: 'Texto', number: 'Número', date: 'Data', select: 'Seleção',
}

const ALLOWED_MIMES = 'image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo,audio/mpeg,audio/wav,audio/ogg,audio/mp4,application/pdf'

function evidenceMaxFiles(configJson: Record<string, unknown>): number {
  const v = configJson.max_files
  return typeof v === 'number' ? v : 20
}

function evidenceCanAddMore(fieldKey: string, configJson: Record<string, unknown>): boolean {
  return (evidenceAttachments[fieldKey]?.length ?? 0) < evidenceMaxFiles(configJson)
}

function selectOptions(configJson: Record<string, unknown>): string[] {
  return Array.isArray(configJson.options) ? (configJson.options as string[]) : []
}

function mimeCategory(mimeType: string): 'image' | 'pdf' | 'file' {
  if (mimeType.startsWith('image/')) return 'image'
  if (mimeType === 'application/pdf') return 'pdf'
  return 'file'
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

// ── Data init ─────────────────────────────────────────────────────────────────

function populateDraft() {
  if (!submission.value) return
  for (const ans of submission.value.answers) {
    if (ans.value === null || ans.value === undefined) {
      draftAnswers[ans.field_key] = ''
    } else if (ans.field_type === 'boolean') {
      draftAnswers[ans.field_key] = ans.value === 'na' ? 'na' : ans.value ? 'true' : 'false'
    } else if (ans.field_type === 'select') {
      draftAnswers[ans.field_key] = typeof ans.value === 'string' ? ans.value : ''
    } else {
      draftAnswers[ans.field_key] = String(ans.value)
    }
  }
  for (const c of submission.value.conformity ?? []) {
    conformityStatus[c.field_key] = c.status
    if (c.justification) conformityJustification[c.field_key] = c.justification
  }
}

async function loadEvidenceAttachments() {
  if (!submission.value) return
  try {
    const all = await listAttachments(submissionId.value)
    for (const att of all) {
      if (!evidenceAttachments[att.field_key]) evidenceAttachments[att.field_key] = []
      evidenceAttachments[att.field_key].push(att)
    }
  } catch (err) {
    console.error('[SubmissionDetail] loadEvidenceAttachments failed:', err)
  } finally {
    evidenceLoaded.value = true
  }
}

onMounted(async () => {
  await submissionsStore.loadOne(submissionId.value)
  if (submission.value) {
    formVersion.value = await fetchFormVersion(submission.value.form_id, submission.value.form_version_id)
    populateDraft()
    await loadEvidenceAttachments()
  }
})

watch(() => submissionsStore.current?.id, (newId) => {
  if (newId === submissionId.value) populateDraft()
})

watch(fields, () => { listViewLimit.value = LIST_PAGE })

// ── Upload handlers ───────────────────────────────────────────────────────────

async function handleEvidenceUpload(fieldKey: string, configJson: Record<string, unknown>, event: Event) {
  const input = event.target as HTMLInputElement
  const file  = input.files?.[0]
  if (!file) return
  if (!evidenceCanAddMore(fieldKey, configJson)) {
    evidenceErrors[fieldKey] = `Limite de ${evidenceMaxFiles(configJson)} evidências atingido.`
    input.value = ''
    return
  }
  evidenceUploading[fieldKey] = true
  delete evidenceErrors[fieldKey]
  try {
    const result = await uploadFile(file)
    const att    = await createAttachment(submissionId.value, { field_key: fieldKey, file_url: result.url, mime_type: result.mime_type, file_size: result.file_size })
    if (!evidenceAttachments[fieldKey]) evidenceAttachments[fieldKey] = []
    evidenceAttachments[fieldKey].push(att)
  } catch (err: any) {
    evidenceErrors[fieldKey] = extractProblemMessage(err, 'Erro ao enviar evidência.')
  } finally {
    evidenceUploading[fieldKey] = false
    input.value = ''
  }
}

async function handleEvidenceDelete(fieldKey: string, attachmentId: string) {
  try {
    await deleteAttachment(submissionId.value, attachmentId)
    if (evidenceAttachments[fieldKey]) {
      evidenceAttachments[fieldKey] = evidenceAttachments[fieldKey].filter((a) => a.id !== attachmentId)
    }
  } catch (err: any) {
    evidenceErrors[fieldKey] = extractProblemMessage(err, 'Erro ao remover evidência.')
  }
}

// ── Save / finish ─────────────────────────────────────────────────────────────

function buildPayload() {
  return fields.value
    .map((field) => {
      if (field.field_type === 'section') return null
      const raw = draftAnswers[field.key] ?? ''
      if (raw === '') return null
      let value: boolean | number | string | null = null
      if (field.field_type === 'boolean') {
        value = raw === 'na' ? 'na' : raw === 'true'
      } else if (field.field_type === 'number') {
        const n = parseFloat(raw)
        value = isNaN(n) ? null : n
      } else {
        value = raw
      }
      if (value === null) return null
      return { field_key: field.key, value }
    })
    .filter((ans): ans is NonNullable<typeof ans> => ans !== null)
}

function validateRequiredFields(): boolean {
  const missing = new Set<string>()

  for (const f of fields.value) {
    if (f.field_type === 'section') continue
    if (f.required) {
      const val = draftAnswers[f.key]
      if (!val || val === '') missing.add(f.key)
      if (!conformityStatus[f.key]) missing.add(f.key)
    }
  }

  for (const [key, s] of Object.entries(conformityStatus)) {
    if (s === 'nao_conforme' && !(conformityJustification[key] || '').trim()) {
      missing.add(key)
    }
  }

  pendingRequiredFields.value = [...missing]
  return missing.size === 0
}

async function handleSave() {
  saveError.value = null
  finishError.value = null
  try {
    await submissionsStore.updateAnswers(submissionId.value, { answers: buildPayload() })
    savedOnce.value = true
    pendingRequiredFields.value = []
  } catch (err: any) {
    saveError.value = extractProblemMessage(err, 'Não foi possível salvar as respostas.')
  }
}

async function handleFinish() {
  finishError.value = null
  saveError.value   = null
  savedOnce.value   = false
  pendingRequiredFields.value = []
  if (!validateRequiredFields()) {
    finishError.value = `Campos com pendências: ${pendingRequiredFields.value.join(', ')}`
    return
  }
  try {
    await submissionsStore.updateAnswers(submissionId.value, { answers: buildPayload() })
    const items = Object.entries(conformityStatus).map(([field_key, status]) => ({
      field_key,
      status,
      justification: conformityJustification[field_key] || null,
    }))
    if (items.length > 0) {
      await saveConformity(submissionId.value, { items })
    }
    await submissionsStore.finish(submissionId.value)
    inspectionMode.value = false
  } catch (err: any) {
    finishError.value = extractProblemMessage(err, 'Não foi possível finalizar a inspeção.')
  }
}

// ── List progressive loading ──────────────────────────────────────────────────

const displayedListFields = computed(() => fields.value.slice(0, listViewLimit.value))
const hasMoreFields        = computed(() => listViewLimit.value < fields.value.length)
function loadMoreFields() { listViewLimit.value += LIST_PAGE }
</script>

<template>
  <AppShell>
    <div class="page">

      <!-- Loading -->
      <div v-if="submissionsStore.isLoading" style="font-size:13px;color:var(--sa-muted);">
        Carregando inspeção...
      </div>

      <template v-else-if="submission">

        <!-- ── Header ── -->
        <div class="back-hdr">
          <button type="button" class="back-btn" @click="router.push({ name: 'submissions' })">
            <SvgIcon name="back" :size="16" />
          </button>
          <div style="flex:1;min-width:0;">
            <div class="eyebrow">Inspeção</div>
            <h1 style="font-size:18px;font-weight:700;letter-spacing:-.01em;color:var(--sa-text);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              {{ submission.form_name }}
            </h1>
            <div style="font-size:12px;color:var(--sa-muted);margin-top:2px;">
              Iniciada {{ new Date(submission.started_at).toLocaleString('pt-BR', { day:'2-digit', month:'2-digit', year:'2-digit', hour:'2-digit', minute:'2-digit' }) }}
            </div>
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

          <!-- Progress + mode toggle -->
          <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px;">
            <div class="slabel" style="margin-bottom:0;">
              {{ progressStats.evaluated }}/{{ progressStats.total }} avaliados
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
              <!-- Score ring (A9) -->
              <div v-if="inspectionMode" class="score-ring" :style="scoreRingStyle">
                <div class="score-ring-inner">
                  {{ liveScore !== null ? liveScore + '%' : '—' }}
                </div>
              </div>
              <button
                v-if="!isCompleted"
                type="button"
                class="btn-secondary btn-sm"
                @click="inspectionMode ? (inspectionMode = false) : enterInspectionMode()"
              >
                {{ inspectionMode ? 'Ver lista' : 'Modo inspeção' }}
              </button>
            </div>
          </div>

          <!-- Segmented progress bar -->
          <div class="insp-progress-bar" style="margin-bottom:6px;height:8px;">
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

          <!-- Progress legend -->
          <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
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

            <!-- View toggle (card / list) -->
            <div style="display:flex;gap:4px;margin-bottom:12px;">
              <button type="button"
                :class="['btn-secondary btn-sm', viewMode === 'card' ? 'btn-view-active' : '']"
                style="flex:1;"
                @click="viewMode = 'card'"
              >Cartão</button>
              <button type="button"
                :class="['btn-secondary btn-sm', viewMode === 'list' ? 'btn-view-active' : '']"
                style="flex:1;"
                @click="viewMode = 'list'"
              >Lista</button>
            </div>

            <!-- Section jump chips (A10) -->
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
                {{ sec.label.length > 18 ? sec.label.slice(0, 18) + '…' : sec.label }}
                <span class="insp-sec-pct">{{ sec.pct }}%</span>
              </button>
            </div>

            <!-- ── CARD VIEW ── -->
            <template v-if="viewMode === 'card'">

              <!-- All done state -->
              <div v-if="allAnswered" style="text-align:center;padding:40px 20px;">
                <div style="width:64px;height:64px;border-radius:50%;background:var(--sa-ok-bg);border:2px solid var(--sa-ok-bd);display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:28px;">✓</div>
                <div style="font-size:18px;font-weight:700;color:var(--sa-text);margin-bottom:6px;">Todos os campos respondidos!</div>
                <div v-if="liveScore !== null" style="margin-bottom:16px;">
                  <span :style="{
                    display:'inline-block', fontSize:'28px', fontWeight:800, fontVariantNumeric:'tabular-nums',
                    color: scoreColorVar(liveScore ?? 0),
                  }">{{ liveScore }}%</span>
                  <div style="font-size:12px;color:var(--sa-muted);margin-top:2px;">Score parcial</div>
                </div>
                <button type="button" class="btn-primary" @click="inspectionMode = false">Ver resumo completo</button>
              </div>

              <!-- Swipe card -->
              <div v-else-if="inspectionField" style="position:relative;min-height:320px;margin-bottom:80px;">

                <!-- Swipe indicators: left = não conforme, right = conforme -->
                <div :style="{
                  position:'absolute', left:'16px', top:'50%', transform:'translateY(-50%)',
                  display:'flex', flexDirection:'column', alignItems:'center', gap:'6px',
                  opacity: leftIndicatorOpacity, pointerEvents:'none', transition:'opacity .1s',
                }">
                  <div style="width:48px;height:48px;border-radius:50%;background:var(--sa-danger);display:flex;align-items:center;justify-content:center;color:#fff;font-size:22px;box-shadow:0 4px 12px rgba(220,38,38,.35);">✕</div>
                  <span style="font-size:10px;font-weight:700;color:var(--sa-danger);">Não conforme</span>
                </div>
                <div :style="{
                  position:'absolute', right:'16px', top:'50%', transform:'translateY(-50%)',
                  display:'flex', flexDirection:'column', alignItems:'center', gap:'6px',
                  opacity: rightIndicatorOpacity, pointerEvents:'none', transition:'opacity .1s',
                }">
                  <div style="width:48px;height:48px;border-radius:50%;background:var(--sa-ok);display:flex;align-items:center;justify-content:center;color:#fff;font-size:22px;box-shadow:0 4px 12px rgba(22,163,74,.35);">✓</div>
                  <span style="font-size:10px;font-weight:700;color:var(--sa-ok);">Conforme</span>
                </div>

                <!-- Card -->
                <div
                  class="insp-card"
                  :style="cardSwipeStyle"
                  style="will-change:transform;touch-action:pan-y;"
                  @touchstart.passive="onTouchStart"
                  @touchmove.passive="onTouchMove"
                  @touchend="onTouchEnd"
                >
                  <!-- Card status header -->
                  <div :style="{
                    margin:'-24px -20px 16px', padding:'10px 16px',
                    borderRadius:'14px 14px 0 0',
                    background:
                      currentFieldStatus === 'conformes'     ? 'var(--sa-ok-bg)'  :
                      currentFieldStatus === 'nao_conformes' ? 'var(--sa-err-bg)' :
                      'var(--sa-panel-strong)',
                    display:'flex', alignItems:'center', justifyContent:'space-between',
                  }">
                    <div style="display:flex;align-items:center;gap:8px;">
                      <span v-if="inspectionSectionLabel" class="insp-section">{{ inspectionSectionLabel }}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:6px;">
                      <!-- Weight badge -->
                      <span v-if="fieldWeight(inspectionField.config_json) > 1"
                        style="font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;background:var(--sa-brand-soft);color:var(--sa-brand);">
                        Peso {{ inspectionField.config_json.weight }}x
                      </span>
                      <!-- Status chip -->
                      <span :style="{
                        fontSize:'10px', fontWeight:700, padding:'2px 8px', borderRadius:'99px',
                        background:
                          currentFieldStatus === 'conformes'     ? 'var(--sa-ok-bg)'  :
                          currentFieldStatus === 'nao_conformes' ? 'var(--sa-err-bg)' :
                          '#f1f5f9',
                        color:
                          currentFieldStatus === 'conformes'     ? 'var(--sa-ok)'     :
                          currentFieldStatus === 'nao_conformes' ? 'var(--sa-danger)' :
                          'var(--sa-muted)',
                      }">
                        {{
                          currentFieldStatus === 'conformes'     ? 'Conforme' :
                          currentFieldStatus === 'nao_conformes' ? 'Não conforme' :
                          'Pendente'
                        }}
                      </span>
                    </div>
                  </div>

                  <!-- Counter -->
                  <div class="insp-meta" style="margin-bottom:8px;">
                    <span style="font-size:10px;font-weight:700;color:var(--sa-muted);">{{ TYPE_LABEL[inspectionField.field_type] ?? inspectionField.field_type }}</span>
                    <span class="insp-counter">{{ inspectionIndex + 1 }} / {{ answerableFields.length }}</span>
                  </div>

                  <!-- Label -->
                  <div style="font-size:17px;font-weight:700;color:var(--sa-text);line-height:1.35;margin-bottom:6px;">
                    {{ inspectionField.label }}
                  </div>
                  <span v-if="inspectionField.required" style="display:inline-block;font-size:9px;font-weight:700;color:var(--sa-danger);text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">
                    Obrigatório
                  </span>
                  <!-- Instrução -->
                  <div v-if="inspectionField.instruction"
                    style="font-size:12px;color:var(--sa-muted);background:var(--sa-bg);border-left:3px solid var(--sa-brand);padding:7px 10px;border-radius:0 6px 6px 0;margin-bottom:12px;line-height:1.5;">
                    {{ inspectionField.instruction }}
                  </div>

                  <div v-if="pendingRequiredFields.includes(inspectionField.key)" class="frow-error-label" style="margin-bottom:8px;">
                    Campo obrigatório não preenchido
                  </div>

                  <!-- Evidence count badge -->
                  <div v-if="(evidenceAttachments[inspectionField.key]?.length ?? 0) > 0"
                    style="display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:600;color:var(--sa-brand);background:var(--sa-brand-soft);padding:3px 9px;border-radius:99px;margin-bottom:12px;">
                    📎 {{ evidenceAttachments[inspectionField.key].length }} evidência(s)
                  </div>

                  <!-- ── BOOLEAN: big Sim/Não/N/A buttons ── -->
                  <div v-if="inspectionField.field_type === 'boolean'" style="display:grid;gap:8px;margin-top:4px;">
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
                      <button type="button" class="bool-btn bool-sim"
                        :class="{ 'bool-btn--active': draftAnswers[inspectionField.key] === 'true' }"
                        :disabled="isCompleted"
                        @click="answerBoolean(inspectionField.key, 'true')">
                        <span style="font-size:20px;">✓</span>
                        <span>Sim</span>
                      </button>
                      <button type="button" class="bool-btn bool-nao"
                        :class="{ 'bool-btn--active': draftAnswers[inspectionField.key] === 'false' }"
                        :disabled="isCompleted"
                        @click="answerBoolean(inspectionField.key, 'false')">
                        <span style="font-size:20px;">✕</span>
                        <span>Não</span>
                      </button>
                    </div>
                    <button v-if="inspectionField.config_json?.allow_na"
                      type="button" class="bool-btn bool-na"
                      :class="{ 'bool-btn--active': draftAnswers[inspectionField.key] === 'na' }"
                      :disabled="isCompleted"
                      @click="answerBoolean(inspectionField.key, 'na')">
                      <span>N/A — Não aplicável</span>
                    </button>
                  </div>

                  <!-- ── NUMBER ── -->
                  <input v-else-if="inspectionField.field_type === 'number'"
                    v-model="draftAnswers[inspectionField.key]"
                    type="number" step="any" placeholder="Informe um número"
                    :disabled="isCompleted" @change="triggerAutoSave()" />

                  <!-- ── DATE ── -->
                  <input v-else-if="inspectionField.field_type === 'date'"
                    v-model="draftAnswers[inspectionField.key]"
                    type="date" :disabled="isCompleted" @change="triggerAutoSave()" />

                  <!-- ── SELECT ── -->
                  <template v-else-if="inspectionField.field_type === 'select'">
                    <select v-if="selectOptions(inspectionField.config_json ?? {}).length"
                      v-model="draftAnswers[inspectionField.key]"
                      :disabled="isCompleted" @change="triggerAutoSave()">
                      <option value="">— Selecione —</option>
                      <option v-for="opt in selectOptions(inspectionField.config_json ?? {})" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                    <input v-else v-model="draftAnswers[inspectionField.key]" type="text" :disabled="isCompleted" @change="triggerAutoSave()" />
                  </template>

                  <!-- ── TEXT ── -->
                  <input v-else-if="inspectionField.field_type === 'text'"
                    v-model="draftAnswers[inspectionField.key]"
                    type="text" placeholder="Informe o valor"
                    :disabled="isCompleted" @change="triggerAutoSave()" />

                  <!-- ── Conformidade ── -->
                  <div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--sa-line);">
                    <div style="font-size:10px;font-weight:700;color:var(--sa-muted);text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px;">Conformidade</div>
                    <div style="display:flex;gap:6px;flex-wrap:wrap;">
                      <button type="button" class="bool-btn-sm bool-sim"
                        :class="{ 'bool-btn--active': conformityStatus[inspectionField.key] === 'conforme' }"
                        :disabled="isCompleted"
                        @click="setConformityCard(inspectionField.key, 'conforme')">✓ Conforme</button>
                      <button type="button" class="bool-btn-sm bool-nao"
                        :class="{ 'bool-btn--active': conformityStatus[inspectionField.key] === 'nao_conforme' }"
                        :disabled="isCompleted"
                        @click="setConformityCard(inspectionField.key, 'nao_conforme')">✕ Não conforme</button>
                    </div>
                    <textarea v-if="conformityStatus[inspectionField.key] === 'nao_conforme'"
                      v-model="conformityJustification[inspectionField.key]"
                      placeholder="Justificativa obrigatória"
                      rows="2"
                      :disabled="isCompleted"
                      style="width:100%;margin-top:8px;font-size:12px;padding:6px 8px;border-radius:6px;border:1px solid var(--sa-danger);resize:vertical;box-sizing:border-box;"
                      @input="triggerConformitySave()"
                    ></textarea>
                  </div>

                  <!-- ── Evidências (todos os tipos de campo) ── -->
                  <div v-if="!isCompleted || (evidenceAttachments[inspectionField.key]?.length ?? 0) > 0"
                    style="margin-top:12px;padding-top:10px;border-top:1px solid var(--sa-line);">
                    <div v-if="evidenceAttachments[inspectionField.key]?.length" style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px;">
                      <div v-for="att in evidenceAttachments[inspectionField.key]" :key="att.id"
                        style="display:inline-flex;align-items:center;gap:5px;padding:4px 8px;background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:6px;font-size:11px;max-width:180px;">
                        <a :href="att.file_url" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:5px;text-decoration:none;min-width:0;">
                          <img v-if="mimeCategory(att.mime_type) === 'image'" :src="att.file_url" style="width:18px;height:18px;object-fit:cover;border-radius:2px;flex-shrink:0;" />
                          <span v-else style="font-size:12px;flex-shrink:0;">📄</span>
                          <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--sa-text);">{{ att.file_url.split('/').pop() }}</span>
                        </a>
                        <button v-if="!isCompleted" type="button" @click="handleEvidenceDelete(inspectionField.key, att.id)"
                          style="border:none;background:none;cursor:pointer;color:var(--sa-danger);font-size:14px;padding:0 2px;line-height:1;flex-shrink:0;">×</button>
                      </div>
                    </div>
                    <label v-if="!isCompleted" style="display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:600;color:var(--sa-brand);cursor:pointer;padding:4px 10px;border:1px dashed var(--sa-brand);border-radius:6px;">
                      {{ evidenceUploading[inspectionField.key] ? 'Enviando…' : '📎 Adicionar evidência' }}
                      <input type="file" :accept="ALLOWED_MIMES" style="display:none;" :disabled="evidenceUploading[inspectionField.key]" @change="handleEvidenceUpload(inspectionField.key, {}, $event)" />
                    </label>
                    <p v-if="evidenceErrors[inspectionField.key]" style="font-size:11px;color:var(--sa-danger);margin-top:4px;">{{ evidenceErrors[inspectionField.key] }}</p>
                  </div>

                  <!-- Swipe hint (boolean only) -->
                  <p v-if="inspectionField.field_type === 'boolean'" style="font-size:11px;color:var(--sa-muted);text-align:center;margin-top:16px;opacity:.6;">
                    ← Não conforme · Conforme →
                  </p>

                  <!-- Card navigation -->
                  <div class="insp-nav">
                    <button type="button" class="btn-secondary" :disabled="inspectionIndex === 0" @click="inspectionPrev">← Anterior</button>
                    <button v-if="inspectionIndex < answerableFields.length - 1" type="button" class="btn-primary" @click="inspectionNext">Próximo →</button>
                    <button v-else type="button" class="btn-primary" @click="inspectionMode = false">Ver resumo</button>
                  </div>
                </div>
              </div>
            </template>

            <!-- ── LIST VIEW (inside inspection mode) ── -->
            <template v-else>
              <div class="fpanel" style="margin-bottom:16px;">
                <template v-for="field in displayedListFields">
                  <div v-if="field.field_type === 'section'" :key="`sec-${field.id}`" :id="`sec-${field.key}`" class="section-divider">
                    <span>{{ field.label }}</span>
                  </div>
                  <InspectionFieldRow
                    v-else
                    :key="field.id"
                    :field="field"
                    :answer="draftAnswers[field.key] ?? ''"
                    :conformity-status="conformityStatus[field.key]"
                    :conformity-justification="conformityJustification[field.key] ?? ''"
                    :is-completed="isCompleted"
                    :is-pending-required="pendingRequiredFields.includes(field.key)"
                    :evidence-attachments="evidenceAttachments[field.key] ?? []"
                    :evidence-uploading="evidenceUploading[field.key] ?? false"
                    :evidence-error="evidenceErrors[field.key]"
                    :compact="true"
                    @update-answer="v => { draftAnswers[field.key] = v; triggerAutoSave() }"
                    @set-conformity="s => setConformity(field.key, s)"
                    @update-justification="v => { conformityJustification[field.key] = v; triggerConformitySave() }"
                    @upload-evidence="e => handleEvidenceUpload(field.key, {}, e)"
                    @delete-evidence="id => handleEvidenceDelete(field.key, id)"
                  />
                </template>
              </div>
              <div v-if="hasMoreFields" style="display:flex;justify-content:center;margin-bottom:12px;">
                <button type="button" class="btn-secondary btn-sm" @click="loadMoreFields">
                  Carregar mais ({{ fields.length - listViewLimit }} restantes)
                </button>
              </div>
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

            <div class="fpanel" style="margin-bottom:16px;">
              <template v-for="field in displayedListFields">
                <div v-if="field.field_type === 'section'" :key="`sec-${field.id}`" :id="`sec-${field.key}`" class="section-divider">
                  <span>{{ field.label }}</span>
                </div>
                <InspectionFieldRow
                  v-else
                  :key="field.id"
                  :field="field"
                  :answer="draftAnswers[field.key] ?? ''"
                  :conformity-status="conformityStatus[field.key]"
                  :conformity-justification="conformityJustification[field.key] ?? ''"
                  :is-completed="isCompleted"
                  :is-pending-required="pendingRequiredFields.includes(field.key)"
                  :evidence-attachments="evidenceAttachments[field.key] ?? []"
                  :evidence-uploading="evidenceUploading[field.key] ?? false"
                  :evidence-error="evidenceErrors[field.key]"
                  @update-answer="v => { draftAnswers[field.key] = v; triggerAutoSave() }"
                  @set-conformity="s => setConformity(field.key, s)"
                  @update-justification="v => { conformityJustification[field.key] = v; triggerConformitySave() }"
                  @upload-evidence="e => handleEvidenceUpload(field.key, {}, e)"
                  @delete-evidence="id => handleEvidenceDelete(field.key, id)"
                />
              </template>
            </div>

            <div v-if="hasMoreFields" style="display:flex;justify-content:center;margin-bottom:12px;">
              <button type="button" class="btn-secondary btn-sm" @click="loadMoreFields">
                Carregar mais campos ({{ fields.length - listViewLimit }} restantes)
              </button>
            </div>
            <div style="margin-bottom:68px;"></div>
          </template>

          <!-- Errors -->
          <p v-if="saveError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:8px;">{{ saveError }}</p>
          <p v-if="finishError" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:8px;">{{ finishError }}</p>
        </div>

        <!-- ── Sticky actions ── -->
        <div class="sticky-act">
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
              @input="triggerConformitySave()"
            />
          </div>
          <div class="sheet-acts">
            <button type="button" class="sheet-cancel" @click="closeJustificationSheet()">Cancelar</button>
            <button type="button" class="sheet-confirm" @click="closeJustificationSheet()">Confirmar</button>
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
              {{ fields.find(f => f.key === evidenceSheetKey)?.label ?? evidenceSheetKey }}
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
                  @change="(e) => evidenceSheetKey && handleEvidenceUpload(evidenceSheetKey, inspectionField?.config_json ?? {}, e)"
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
  margin-bottom: 12px;
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
</style>
