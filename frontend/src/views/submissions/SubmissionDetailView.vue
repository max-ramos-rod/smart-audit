<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { createAttachment, deleteAttachment, listAttachments } from '@/services/attachments.service'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchFormVersion } from '@/services/forms.service'
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

// Bottom sheet: evidence prompt after marking non-compliant
const showEvidenceSheet     = ref(false)
const evidenceSheetFieldKey = ref<string | null>(null)

// Progressive list loading
const LIST_PAGE    = 50
const listViewLimit = ref(LIST_PAGE)

// Evidence per field
const evidenceAttachments = reactive<Record<string, AttachmentItem[]>>({})
const evidenceUploading   = reactive<Record<string, boolean>>({})
const evidenceErrors      = reactive<Record<string, string>>({})

const pendingRequiredFields = ref<string[]>([])

// ── Derived ───────────────────────────────────────────────────────────────────

const submissionId = computed(() => route.params.id as string)
const submission   = computed(() => submissionsStore.current)
const isCompleted  = computed(() => submission.value?.status === 'completed')

const fields = computed(() =>
  [...(formVersion.value?.fields ?? [])].sort((a, b) => a.position - b.position),
)

const visibleFields = computed(() =>
  fields.value.filter((field) => {
    const vi = field.config_json?.visible_if as Record<string, string> | undefined
    if (!vi?.field_key) return true
    const actual   = String(draftAnswers[vi.field_key] ?? '').toLowerCase()
    const expected = String(vi.value ?? '').toLowerCase()
    return vi.operator === 'neq' ? actual !== expected : actual === expected
  }),
)

// Fields that accept answers (skip section dividers)
const answerableFields = computed(() =>
  visibleFields.value.filter((f) => f.field_type !== 'section'),
)

// ── Progress counters ─────────────────────────────────────────────────────────

const progressStats = computed(() => {
  let conformes    = 0
  let naoConformes = 0
  let naCount      = 0
  let outros       = 0

  for (const field of answerableFields.value) {
    const val = draftAnswers[field.key]
    if (!val || val === '') continue
    if (field.field_type === 'boolean') {
      if (val === 'true') conformes++
      else if (val === 'false') naoConformes++
      else if (val === 'na') naCount++
    } else {
      outros++
    }
  }

  const answered   = conformes + naoConformes + naCount + outros
  const total      = answerableFields.value.length
  const percentage = total === 0 ? 0 : Math.round((answered / total) * 100)
  const pending    = total - answered

  return { conformes, naoConformes, naCount, outros, answered, pending, total, percentage }
})

// Real-time weighted score (mirrors backend calculate_score logic)
const liveScore = computed((): number | null => {
  let wConformes = 0
  let wTotal     = 0
  for (const field of answerableFields.value) {
    if (field.field_type !== 'boolean') continue
    const val    = draftAnswers[field.key]
    const weight = (field.config_json?.weight as number | undefined) ?? 1
    if (val === 'true')  { wConformes += weight; wTotal += weight }
    else if (val === 'false') { wTotal += weight }
    // 'na' and empty are excluded from denominator
  }
  return wTotal === 0 ? null : Math.round((wConformes / wTotal) * 100)
})

const progressPct = computed(() => progressStats.value.percentage)

// All answerable fields have a value
const allAnswered = computed(() => progressStats.value.pending === 0 && progressStats.value.total > 0)

// ── Sections ──────────────────────────────────────────────────────────────────

const formSections = computed(() =>
  visibleFields.value
    .filter((f) => f.field_type === 'section')
    .map((section, idx, arr) => {
      const nextSectionPos = arr[idx + 1]?.position ?? Infinity
      const sectionItems   = answerableFields.value.filter(
        (f) => f.position > section.position && f.position < nextSectionPos,
      )
      const answered = sectionItems.filter((f) => {
        const v = draftAnswers[f.key]
        return v !== undefined && v !== ''
      }).length
      const pct = sectionItems.length === 0 ? 100 : Math.round((answered / sectionItems.length) * 100)
      return { key: section.key, label: section.label, pct }
    }),
)

// ── Inspection card (current field) ───────────────────────────────────────────

const inspectionField = computed(() => answerableFields.value[inspectionIndex.value] ?? null)

const inspectionSectionLabel = computed(() => {
  const field = inspectionField.value
  if (!field) return ''
  const allVisible = visibleFields.value
  const idx = allVisible.findIndex((f) => f.key === field.key)
  for (let i = idx - 1; i >= 0; i--) {
    if (allVisible[i].field_type === 'section') return allVisible[i].label
  }
  return ''
})

function fieldAnswerStatus(fieldKey: string, fieldType: string): 'pending' | 'conformes' | 'nao_conformes' | 'na' | 'answered' {
  const val = draftAnswers[fieldKey]
  if (!val || val === '') return 'pending'
  if (fieldType === 'boolean') {
    if (val === 'true') return 'conformes'
    if (val === 'false') return 'nao_conformes'
    if (val === 'na') return 'na'
  }
  return 'answered'
}

const currentFieldStatus = computed(() => {
  if (!inspectionField.value) return 'pending'
  return fieldAnswerStatus(inspectionField.value.key, inspectionField.value.field_type)
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
  const sectionField = visibleFields.value.find((f) => f.key === sectionKey && f.field_type === 'section')
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
    // Swipe right → Conforme
    if (field.field_type === 'boolean') {
      draftAnswers[field.key] = 'true'
      triggerAutoSave()
    }
    inspectionNext()
  } else {
    // Swipe left → Não conforme + open evidence sheet
    if (field.field_type === 'boolean') {
      draftAnswers[field.key] = 'false'
      triggerAutoSave()
      openEvidenceSheet(field.key)
    } else {
      inspectionNext()
    }
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

// Swipe indicator opacity
const rightIndicatorOpacity = computed(() => Math.min(1, Math.max(0, swipeDeltaX.value / 100)))
const leftIndicatorOpacity  = computed(() => Math.min(1, Math.max(0, -swipeDeltaX.value / 100)))

// ── Boolean quick-answer buttons ──────────────────────────────────────────────

function answerBoolean(fieldKey: string, value: 'true' | 'false' | 'na') {
  draftAnswers[fieldKey] = value
  triggerAutoSave()
  if (value === 'false') {
    openEvidenceSheet(fieldKey)
  } else {
    setTimeout(() => inspectionNext(), 300)
  }
}

// ── Evidence bottom sheet ─────────────────────────────────────────────────────

function openEvidenceSheet(fieldKey: string) {
  evidenceSheetFieldKey.value = fieldKey
  showEvidenceSheet.value = true
}

function closeEvidenceSheet() {
  showEvidenceSheet.value = false
  evidenceSheetFieldKey.value = null
  inspectionNext()
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

const EVIDENCE_MIME_MAP: Record<string, string[]> = {
  image:    ['image/jpeg', 'image/png', 'image/webp'],
  pdf:      ['application/pdf'],
  document: ['application/pdf'],
}
const ALLOWED_MIMES = ([] as string[]).concat(...Object.values(EVIDENCE_MIME_MAP)).join(',')

function evidenceAccept(configJson: Record<string, unknown>): string {
  const types = configJson.allowed_types
  if (!Array.isArray(types) || types.length === 0) return ALLOWED_MIMES
  const mimes: string[] = []
  for (const t of types) {
    const mapped = EVIDENCE_MIME_MAP[t as string]
    if (mapped) mimes.push(...mapped)
  }
  return mimes.join(',') || ALLOWED_MIMES
}

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

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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
}

async function loadEvidenceAttachments() {
  if (!submission.value) return
  try {
    const all = await listAttachments(submissionId.value)
    for (const att of all) {
      if (!evidenceAttachments[att.field_key]) evidenceAttachments[att.field_key] = []
      evidenceAttachments[att.field_key].push(att)
    }
  } catch { /* non-fatal */ }
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
  return visibleFields.value
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
  const missing = visibleFields.value
    .filter((f) => f.field_type !== 'section' && f.required)
    .filter((f) => {
      const val = draftAnswers[f.key]
      return !val || val === ''
    })
    .map((f) => f.key)
  pendingRequiredFields.value = missing
  return missing.length === 0
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
    finishError.value = `Campos obrigatórios pendentes: ${pendingRequiredFields.value.join(', ')}`
    return
  }
  try {
    await submissionsStore.updateAnswers(submissionId.value, { answers: buildPayload() })
    await submissionsStore.finish(submissionId.value)
    inspectionMode.value = false
  } catch (err: any) {
    finishError.value = extractProblemMessage(err, 'Não foi possível finalizar a inspeção.')
  }
}

// ── List progressive loading ──────────────────────────────────────────────────

const displayedListFields = computed(() => visibleFields.value.slice(0, listViewLimit.value))
const hasMoreFields        = computed(() => listViewLimit.value < visibleFields.value.length)
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
            color: submission.score >= 85 ? 'var(--sa-ok)' : submission.score >= 65 ? 'var(--sa-warn)' : 'var(--sa-danger)',
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
              {{ progressStats.answered }}/{{ progressStats.total }} campos
            </div>
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
              <!-- Live score badge -->
              <span v-if="liveScore !== null" :style="{
                fontSize:'11px', fontWeight:700, fontVariantNumeric:'tabular-nums',
                color: liveScore >= 85 ? 'var(--sa-ok)' : liveScore >= 65 ? 'var(--sa-warn)' : 'var(--sa-danger)',
              }">
                Score {{ liveScore }}%
              </span>
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
            <div style="display:flex;height:100%;border-radius:99px;overflow:hidden;">
              <div
                style="background:var(--sa-ok);transition:width .35s ease;"
                :style="{ width: progressStats.total ? (progressStats.conformes / progressStats.total * 100) + '%' : '0%' }"
              />
              <div
                style="background:var(--sa-danger);transition:width .35s ease;"
                :style="{ width: progressStats.total ? (progressStats.naoConformes / progressStats.total * 100) + '%' : '0%' }"
              />
              <div
                style="background:var(--sa-warn);transition:width .35s ease;"
                :style="{ width: progressStats.total ? (progressStats.naCount / progressStats.total * 100) + '%' : '0%' }"
              />
              <div
                style="background:var(--sa-brand);transition:width .35s ease;"
                :style="{ width: progressStats.total ? (progressStats.outros / progressStats.total * 100) + '%' : '0%' }"
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
            <span v-if="progressStats.naCount > 0" style="display:flex;align-items:center;gap:4px;font-size:11px;color:var(--sa-muted);">
              <span style="width:8px;height:8px;border-radius:50%;background:var(--sa-warn);flex-shrink:0;"></span>
              {{ progressStats.naCount }} N/A
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

            <!-- Section jump chips (inspection mode) -->
            <div v-if="formSections.length" style="display:flex;gap:6px;overflow-x:auto;padding-bottom:4px;margin-bottom:12px;scrollbar-width:none;">
              <button
                v-for="sec in formSections"
                :key="sec.key"
                type="button"
                class="section-jump-chip"
                :style="sec.pct === 100 ? 'background:var(--sa-ok);color:#fff;border-color:var(--sa-ok);' : ''"
                @click="jumpToSection(sec.key)"
              >
                {{ sec.label.length > 18 ? sec.label.slice(0, 18) + '…' : sec.label }}
                <span style="opacity:.75;font-size:10px;margin-left:3px;">{{ sec.pct }}%</span>
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
                    color: liveScore >= 85 ? 'var(--sa-ok)' : liveScore >= 65 ? 'var(--sa-warn)' : 'var(--sa-danger)',
                  }">{{ liveScore }}%</span>
                  <div style="font-size:12px;color:var(--sa-muted);margin-top:2px;">Score parcial</div>
                </div>
                <button type="button" class="btn-primary" @click="inspectionMode = false">Ver resumo completo</button>
              </div>

              <!-- Swipe card -->
              <div v-else-if="inspectionField" style="position:relative;min-height:320px;margin-bottom:80px;">

                <!-- Swipe indicators -->
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
                      currentFieldStatus === 'conformes'    ? 'var(--sa-ok-bg)'  :
                      currentFieldStatus === 'nao_conformes' ? 'var(--sa-err-bg)' :
                      currentFieldStatus === 'na'           ? 'var(--sa-warn-bg)' :
                      currentFieldStatus === 'answered'     ? 'var(--sa-brand-soft)' :
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
                          currentFieldStatus === 'conformes'    ? 'var(--sa-ok-bg)'  :
                          currentFieldStatus === 'nao_conformes' ? 'var(--sa-err-bg)' :
                          currentFieldStatus === 'na'           ? 'var(--sa-warn-bg)' :
                          '#f1f5f9',
                        color:
                          currentFieldStatus === 'conformes'    ? 'var(--sa-ok)'     :
                          currentFieldStatus === 'nao_conformes' ? 'var(--sa-danger)' :
                          currentFieldStatus === 'na'           ? 'var(--sa-warn)'   :
                          'var(--sa-muted)',
                      }">
                        {{
                          currentFieldStatus === 'conformes'    ? 'Conforme' :
                          currentFieldStatus === 'nao_conformes' ? 'Não conforme' :
                          currentFieldStatus === 'na'           ? 'N/A' :
                          currentFieldStatus === 'answered'     ? 'Respondido' :
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
                  <span v-if="inspectionField.required" style="display:inline-block;font-size:9px;font-weight:700;color:var(--sa-danger);text-transform:uppercase;letter-spacing:.06em;margin-bottom:14px;">
                    Obrigatório
                  </span>

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
                        <span>Sim (Conforme)</span>
                      </button>
                      <button type="button" class="bool-btn bool-nao"
                        :class="{ 'bool-btn--active': draftAnswers[inspectionField.key] === 'false' }"
                        :disabled="isCompleted"
                        @click="answerBoolean(inspectionField.key, 'false')">
                        <span style="font-size:20px;">✕</span>
                        <span>Não (Não conforme)</span>
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

                  <!-- ── Evidências (todos os tipos de campo) ── -->
                  <div v-if="!isCompleted || (evidenceAttachments[inspectionField.key]?.length ?? 0) > 0"
                    style="margin-top:12px;padding-top:10px;border-top:1px solid var(--sa-line);">
                    <div v-if="evidenceAttachments[inspectionField.key]?.length" style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px;">
                      <div v-for="att in evidenceAttachments[inspectionField.key]" :key="att.id"
                        style="display:inline-flex;align-items:center;gap:5px;padding:4px 8px;background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:6px;font-size:11px;max-width:180px;">
                        <img v-if="mimeCategory(att.mime_type) === 'image'" :src="att.file_url" style="width:18px;height:18px;object-fit:cover;border-radius:2px;flex-shrink:0;" />
                        <span v-else style="font-size:12px;flex-shrink:0;">📄</span>
                        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--sa-text);">{{ att.file_url.split('/').pop() }}</span>
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
                    ← Deslize para não conforme · Conforme para →
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
                  <div v-else :key="field.id" class="frow" :class="{ 'frow-error': pendingRequiredFields.includes(field.key) }">
                    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
                      <div>
                        <div class="frow-type">{{ TYPE_LABEL[field.field_type] ?? field.field_type }}</div>
                        <div class="frow-name">{{ field.label }}</div>
                      </div>
                      <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                        <span v-if="fieldWeight(field.config_json) > 1" style="font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;background:var(--sa-brand-soft);color:var(--sa-brand);">Peso {{ field.config_json.weight }}x</span>
                        <span v-if="field.required" class="status-chip status-chip--neu" style="font-size:9px;">Obrigatório</span>
                      </div>
                    </div>
                    <div v-if="pendingRequiredFields.includes(field.key)" class="frow-error-label">Campo obrigatório não preenchido</div>

                    <!-- Boolean: buttons in list mode -->
                    <div v-if="field.field_type === 'boolean'" style="display:flex;gap:6px;flex-wrap:wrap;">
                      <button type="button" class="bool-btn-sm bool-sim"
                        :class="{ 'bool-btn--active': draftAnswers[field.key] === 'true' }"
                        :disabled="isCompleted" @click="draftAnswers[field.key] = 'true'; triggerAutoSave()">✓ Sim</button>
                      <button type="button" class="bool-btn-sm bool-nao"
                        :class="{ 'bool-btn--active': draftAnswers[field.key] === 'false' }"
                        :disabled="isCompleted" @click="draftAnswers[field.key] = 'false'; triggerAutoSave()">✕ Não</button>
                      <button v-if="field.config_json?.allow_na"
                        type="button" class="bool-btn-sm bool-na"
                        :class="{ 'bool-btn--active': draftAnswers[field.key] === 'na' }"
                        :disabled="isCompleted" @click="draftAnswers[field.key] = 'na'; triggerAutoSave()">N/A</button>
                    </div>
                    <input v-else-if="field.field_type === 'number'" v-model="draftAnswers[field.key]" type="number" step="any" :disabled="isCompleted" @change="triggerAutoSave()" />
                    <input v-else-if="field.field_type === 'date'" v-model="draftAnswers[field.key]" type="date" :disabled="isCompleted" @change="triggerAutoSave()" />
                    <template v-else-if="field.field_type === 'select'">
                      <select v-if="selectOptions(field.config_json ?? {}).length" v-model="draftAnswers[field.key]" :disabled="isCompleted" @change="triggerAutoSave()">
                        <option value="">— Selecione —</option>
                        <option v-for="opt in selectOptions(field.config_json ?? {})" :key="opt" :value="opt">{{ opt }}</option>
                      </select>
                      <input v-else v-model="draftAnswers[field.key]" type="text" :disabled="isCompleted" @change="triggerAutoSave()" />
                    </template>
                    <input v-else-if="field.field_type === 'text'" v-model="draftAnswers[field.key]" type="text" :disabled="isCompleted" @change="triggerAutoSave()" />
                    <input v-else v-model="draftAnswers[field.key]" type="text" :disabled="isCompleted" @change="triggerAutoSave()" />

                    <!-- Evidências (todos os tipos) -->
                    <div v-if="!isCompleted || (evidenceAttachments[field.key]?.length ?? 0) > 0" style="margin-top:8px;display:flex;flex-wrap:wrap;align-items:center;gap:4px;">
                      <div v-for="att in evidenceAttachments[field.key]" :key="att.id"
                        style="display:inline-flex;align-items:center;gap:4px;padding:3px 7px;background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:6px;font-size:11px;max-width:150px;">
                        <img v-if="mimeCategory(att.mime_type) === 'image'" :src="att.file_url" style="width:16px;height:16px;object-fit:cover;border-radius:2px;flex-shrink:0;" />
                        <span v-else style="font-size:11px;flex-shrink:0;">📄</span>
                        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ att.file_url.split('/').pop() }}</span>
                        <button v-if="!isCompleted" type="button" @click="handleEvidenceDelete(field.key, att.id)"
                          style="border:none;background:none;cursor:pointer;color:var(--sa-danger);font-size:13px;padding:0;line-height:1;flex-shrink:0;">×</button>
                      </div>
                      <label v-if="!isCompleted" style="display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:600;color:var(--sa-muted);cursor:pointer;padding:3px 7px;border:1px dashed var(--sa-line);border-radius:6px;">
                        {{ evidenceUploading[field.key] ? '…' : '📎' }}
                        <input type="file" :accept="ALLOWED_MIMES" style="display:none;" :disabled="evidenceUploading[field.key]" @change="handleEvidenceUpload(field.key, {}, $event)" />
                      </label>
                      <span v-if="evidenceErrors[field.key]" style="font-size:11px;color:var(--sa-danger);">{{ evidenceErrors[field.key] }}</span>
                    </div>
                  </div>
                </template>
              </div>
              <div v-if="hasMoreFields" style="display:flex;justify-content:center;margin-bottom:12px;">
                <button type="button" class="btn-secondary btn-sm" @click="loadMoreFields">
                  Carregar mais ({{ visibleFields.length - listViewLimit }} restantes)
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

            <div class="fpanel" style="margin-bottom:16px;">
              <template v-for="field in displayedListFields">
                <div v-if="field.field_type === 'section'" :key="`sec-${field.id}`" :id="`sec-${field.key}`" class="section-divider">
                  <span>{{ field.label }}</span>
                </div>
                <div v-else :key="field.id" class="frow" :class="{ 'frow-error': pendingRequiredFields.includes(field.key) }">
                  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
                    <div>
                      <div class="frow-type">{{ TYPE_LABEL[field.field_type] ?? field.field_type }}</div>
                      <div class="frow-name">{{ field.label }}</div>
                    </div>
                    <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
                      <span v-if="fieldWeight(field.config_json) > 1" style="font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;background:var(--sa-brand-soft);color:var(--sa-brand);">Peso {{ field.config_json.weight }}x</span>
                      <span v-if="field.required" class="status-chip status-chip--neu" style="font-size:9px;">Obrigatório</span>
                    </div>
                  </div>
                  <div v-if="pendingRequiredFields.includes(field.key)" class="frow-error-label">Campo obrigatório não preenchido</div>

                  <!-- Boolean: buttons -->
                  <div v-if="field.field_type === 'boolean'" style="display:flex;gap:6px;flex-wrap:wrap;">
                    <button type="button" class="bool-btn-sm bool-sim"
                      :class="{ 'bool-btn--active': draftAnswers[field.key] === 'true' }"
                      :disabled="isCompleted" @click="draftAnswers[field.key] = 'true'; triggerAutoSave()">✓ Sim</button>
                    <button type="button" class="bool-btn-sm bool-nao"
                      :class="{ 'bool-btn--active': draftAnswers[field.key] === 'false' }"
                      :disabled="isCompleted" @click="draftAnswers[field.key] = 'false'; triggerAutoSave()">✕ Não</button>
                    <button v-if="field.config_json?.allow_na"
                      type="button" class="bool-btn-sm bool-na"
                      :class="{ 'bool-btn--active': draftAnswers[field.key] === 'na' }"
                      :disabled="isCompleted" @click="draftAnswers[field.key] = 'na'; triggerAutoSave()">N/A</button>
                  </div>

                  <!-- Other field types (same as list view inside inspection) -->
                  <input v-else-if="field.field_type === 'number'" v-model="draftAnswers[field.key]" type="number" step="any" placeholder="Informe um número" :disabled="isCompleted" @change="triggerAutoSave()" />
                  <input v-else-if="field.field_type === 'date'" v-model="draftAnswers[field.key]" type="date" :disabled="isCompleted" @change="triggerAutoSave()" />
                  <template v-else-if="field.field_type === 'select'">
                    <select v-if="selectOptions(field.config_json ?? {}).length" v-model="draftAnswers[field.key]" :disabled="isCompleted" @change="triggerAutoSave()">
                      <option value="">— Selecione uma opção —</option>
                      <option v-for="opt in selectOptions(field.config_json ?? {})" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                    <input v-else v-model="draftAnswers[field.key]" type="text" placeholder="Informe a opção" :disabled="isCompleted" @change="triggerAutoSave()" />
                  </template>
                  <input v-else-if="field.field_type === 'text'" v-model="draftAnswers[field.key]" type="text" placeholder="Informe o valor" :disabled="isCompleted" @change="triggerAutoSave()" />
                  <input v-else v-model="draftAnswers[field.key]" type="text" placeholder="Informe o valor" :disabled="isCompleted" @change="triggerAutoSave()" />

                  <!-- Evidências (todos os tipos de campo) -->
                  <div v-if="!isCompleted || (evidenceAttachments[field.key]?.length ?? 0) > 0" style="margin-top:10px;">
                    <div v-if="evidenceAttachments[field.key]?.length" style="display:grid;gap:6px;margin-bottom:8px;">
                      <div v-for="att in evidenceAttachments[field.key]" :key="att.id"
                        style="display:flex;align-items:center;gap:10px;background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:8px;padding:8px 10px;">
                        <img v-if="mimeCategory(att.mime_type) === 'image'" :src="att.file_url" alt="" style="width:40px;height:40px;object-fit:cover;border-radius:4px;flex-shrink:0;" />
                        <div v-else style="width:40px;height:40px;border-radius:4px;flex-shrink:0;background:var(--sa-brand-soft);display:flex;align-items:center;justify-content:center;font-size:18px;">📄</div>
                        <div style="flex:1;min-width:0;">
                          <div style="font-size:12px;font-weight:600;color:var(--sa-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ att.file_url.split('/').pop() }}</div>
                          <div style="font-size:11px;color:var(--sa-muted);margin-top:2px;">{{ formatFileSize(att.file_size) }}</div>
                        </div>
                        <button v-if="!isCompleted" type="button" title="Remover" @click="handleEvidenceDelete(field.key, att.id)"
                          style="border:none;background:none;cursor:pointer;color:var(--sa-danger);font-size:18px;line-height:1;padding:0 4px;flex-shrink:0;">×</button>
                      </div>
                    </div>
                    <template v-if="!isCompleted">
                      <label style="cursor:pointer;display:inline-block;">
                        <span class="inline-action">{{ evidenceUploading[field.key] ? 'Enviando…' : '📎 Adicionar evidência' }}</span>
                        <input type="file" :accept="ALLOWED_MIMES" style="display:none;" :disabled="evidenceUploading[field.key]" @change="handleEvidenceUpload(field.key, {}, $event)" />
                      </label>
                    </template>
                    <p v-if="evidenceErrors[field.key]" style="font-size:12px;font-weight:600;color:var(--sa-danger);margin-top:6px;">{{ evidenceErrors[field.key] }}</p>
                  </div>
                </div>
              </template>
            </div>

            <div v-if="hasMoreFields" style="display:flex;justify-content:center;margin-bottom:12px;">
              <button type="button" class="btn-secondary btn-sm" @click="loadMoreFields">
                Carregar mais campos ({{ visibleFields.length - listViewLimit }} restantes)
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

    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!--  EVIDENCE BOTTOM SHEET                                              -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <Teleport to="body">
      <Transition name="sheet">
        <div v-if="showEvidenceSheet" style="position:fixed;inset:0;z-index:200;display:flex;flex-direction:column;justify-content:flex-end;">
          <!-- Backdrop -->
          <div style="position:absolute;inset:0;background:rgba(15,23,42,.45);" @click="closeEvidenceSheet" />

          <!-- Sheet -->
          <div style="position:relative;background:#fff;border-radius:20px 20px 0 0;padding:20px 20px 32px;max-height:80vh;overflow-y:auto;">
            <div style="width:40px;height:4px;border-radius:99px;background:var(--sa-line);margin:0 auto 20px;"></div>

            <div style="margin-bottom:16px;">
              <div style="font-size:16px;font-weight:700;color:var(--sa-text);margin-bottom:4px;">Não-conformidade registrada</div>
              <div style="font-size:13px;color:var(--sa-muted);">Deseja adicionar uma evidência fotográfica?</div>
            </div>

            <!-- Evidence upload shortcut -->
            <div v-if="evidenceSheetFieldKey" style="margin-bottom:16px;">
              <label style="display:flex;align-items:center;gap:12px;padding:14px;border:1px solid var(--sa-line);border-radius:12px;cursor:pointer;background:var(--sa-bg);transition:background .15s;">
                <div style="width:40px;height:40px;border-radius:10px;background:var(--sa-brand-soft);display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">📷</div>
                <div>
                  <div style="font-size:13px;font-weight:600;color:var(--sa-text);">{{ evidenceUploading[evidenceSheetFieldKey] ? 'Enviando…' : 'Adicionar foto da evidência' }}</div>
                  <div style="font-size:11px;color:var(--sa-muted);">JPG, PNG ou WebP · máx. 10MB</div>
                </div>
                <input type="file" accept="image/jpeg,image/png,image/webp" style="display:none;"
                  :disabled="evidenceUploading[evidenceSheetFieldKey || '']"
                  @change="handleEvidenceUpload(evidenceSheetFieldKey || '', {}, $event); closeEvidenceSheet()" />
              </label>
              <p v-if="evidenceErrors[evidenceSheetFieldKey || '']" style="font-size:12px;color:var(--sa-danger);margin-top:6px;">{{ evidenceErrors[evidenceSheetFieldKey || ''] }}</p>
            </div>

            <button type="button" class="btn-secondary btn-full" @click="closeEvidenceSheet">
              Pular por agora
            </button>
          </div>
        </div>
      </Transition>
    </Teleport>

  </AppShell>
</template>

<style scoped>
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

/* Bottom sheet transition */
.sheet-enter-active,
.sheet-leave-active { transition: opacity .25s ease; }
.sheet-enter-active > div:last-child,
.sheet-leave-active > div:last-child { transition: transform .25s ease; }
.sheet-enter-from { opacity: 0; }
.sheet-enter-from > div:last-child { transform: translateY(100%); }
.sheet-leave-to { opacity: 0; }
.sheet-leave-to > div:last-child { transform: translateY(100%); }
</style>
