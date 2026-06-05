<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import InspectionFieldRow from '@/components/submissions/InspectionFieldRow.vue'
import InspectionListRow from '@/components/submissions/InspectionListRow.vue'
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

// ── List-mode filter state ─────────────────────────────────────────────────────

const FILTERS = [
  { id: 'all',   label: 'Todos',       cls: ''     },
  { id: 'pend',  label: '⚡ Pendentes', cls: 'warn' },
  { id: 'conf',  label: '✓ Conformes', cls: 'ok'   },
  { id: 'nconf', label: '✕ Não conf.', cls: 'err'  },
  { id: 'bool',  label: 'S/N',         cls: ''     },
  { id: 'sel',   label: 'Seleção',     cls: ''     },
] as const

type ListFilter = typeof FILTERS[number]['id']
const listFilter = ref<ListFilter>('all')
const expandedListKey = ref<string | null>(null)

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

// ── List-mode filtered fields ─────────────────────────────────────────────────

const filteredListFields = computed(() => {
  return fields.value.filter(f => {
    if (f.field_type === 'section') return true
    if (listFilter.value === 'pend')  return !conformityStatus[f.key]
    if (listFilter.value === 'conf')  return conformityStatus[f.key] === 'conforme'
    if (listFilter.value === 'nconf') return conformityStatus[f.key] === 'nao_conforme'
    if (listFilter.value === 'bool')  return f.field_type === 'boolean'
    if (listFilter.value === 'sel')   return f.field_type === 'select'
    return true
  })
})

const visibleSectionKeys = computed(() => {
  const keys = new Set<string>()
  let currentSec: string | null = null
  for (const f of filteredListFields.value) {
    if (f.field_type === 'section') { currentSec = f.key; continue }
    if (currentSec) keys.add(currentSec)
  }
  return keys
})

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
    // Inspeções em andamento entram direto no modo lista
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

// ── Skip ──────────────────────────────────────────────────────────────────────
function doSkip() { inspectionNext() }

// ── List-mode helpers ─────────────────────────────────────────────────────────

function filterCount(filterId: ListFilter): number {
  const af = answerableFields.value
  if (filterId === 'all')   return af.length
  if (filterId === 'pend')  return af.filter(f => !conformityStatus[f.key]).length
  if (filterId === 'conf')  return af.filter(f => conformityStatus[f.key] === 'conforme').length
  if (filterId === 'nconf') return af.filter(f => conformityStatus[f.key] === 'nao_conforme').length
  if (filterId === 'bool')  return af.filter(f => f.field_type === 'boolean').length
  if (filterId === 'sel')   return af.filter(f => f.field_type === 'select').length
  return 0
}

function fieldPosition(field: { key: string }): number {
  return answerableFields.value.findIndex(f => f.key === field.key) + 1
}

function sectionFields(sectionKey: string) {
  const all = filteredListFields.value
  const secIdx = all.findIndex(f => f.field_type === 'section' && f.key === sectionKey)
  if (secIdx === -1) return []
  const result: typeof all = []
  for (let i = secIdx + 1; i < all.length; i++) {
    if (all[i].field_type === 'section') break
    result.push(all[i])
  }
  return result
}

function sectionPct(sectionKey: string): number {
  const sf = sectionFields(sectionKey)
  if (sf.length === 0) return 0
  const done = sf.filter(f => !!conformityStatus[f.key]).length
  return Math.round((done / sf.length) * 100)
}

function sectionProgress(sectionKey: string): string {
  const sf = sectionFields(sectionKey)
  const done = sf.filter(f => !!conformityStatus[f.key]).length
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
      const el = document.getElementById(`list-row-${key}`)
      const container = document.getElementById('list-scroll-container')
      if (el && container) container.scrollTo({ top: el.offsetTop - 64, behavior: 'smooth' })
    })
  }
}

function jumpFirstPending() {
  const first = answerableFields.value.find(f => !conformityStatus[f.key])
  if (!first) return
  listFilter.value = 'all'
  expandedListKey.value = first.key
  nextTick(() => {
    const el = document.getElementById(`list-row-${first.key}`)
    const container = document.getElementById('list-scroll-container')
    if (el && container) container.scrollTo({ top: el.offsetTop - 64, behavior: 'smooth' })
  })
}

function jumpNextPending(afterKey: string) {
  const keys = answerableFields.value.map(f => f.key)
  const idx = keys.indexOf(afterKey)
  for (let i = idx + 1; i < keys.length; i++) {
    if (!conformityStatus[keys[i]]) {
      const el = document.getElementById(`list-row-${keys[i]}`)
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

// ── Non-conformity: open justification sheet ──────────────────────────────────
function setNaoConformeCard(fieldKey: string) {
  setConformity(fieldKey, 'nao_conforme')
  justificationError.value = null
  justificationFieldKey.value = fieldKey
  showJustificationSheet.value = true
}

const justificationError = ref<string | null>(null)

function confirmJustification() {
  const key = justificationFieldKey.value
  if (!key) return
  const text = (conformityJustification[key] || '').trim()
  if (!text) {
    justificationError.value = 'Descreva o problema encontrado.'
    return
  }
  justificationError.value = null
  triggerConformitySave()
  showJustificationSheet.value = false
  setTimeout(() => inspectionNext(), 250)
}

// ── Nearby dots for card ──────────────────────────────────────────────────────
const nearbyDots = computed(() => {
  const idx   = inspectionIndex.value
  const all   = answerableFields.value
  const half  = 4
  const start = Math.max(0, idx - half)
  const end   = Math.min(all.length - 1, idx + half)
  return all.slice(start, end + 1).map((f, i) => ({
    key:       f.key,
    status:    conformityStatus[f.key] ?? 'pending',
    isCurrent: start + i === idx,
  }))
})

// ── Evidence count for current card field ─────────────────────────────────────
const currentFieldEvidenceCount = computed(() =>
  inspectionField.value ? (evidenceAttachments[inspectionField.value.key]?.length ?? 0) : 0,
)
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
            <div class="insp-fhdr-sub">Em andamento</div>
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
          <template v-else-if="inspectionField">

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
                    <span class="card-counter">{{ inspectionIndex + 1 }} / {{ answerableFields.length }}</span>
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
                        :class="{ 'bool-btn--active': draftAnswers[inspectionField.key] === 'true' }"
                        @click="answerBoolean(inspectionField.key, 'true')">
                        <span class="b-icon">✓</span><span class="b-lbl">Sim</span>
                      </button>
                      <button type="button" class="bool-btn bool-nao"
                        :class="{ 'bool-btn--active': draftAnswers[inspectionField.key] === 'false' }"
                        @click="answerBoolean(inspectionField.key, 'false')">
                        <span class="b-icon">✕</span><span class="b-lbl">Não</span>
                      </button>
                    </div>
                    <button v-if="inspectionField.config_json?.allow_na"
                      type="button" class="na-btn"
                      :class="{ 'na-btn--active': draftAnswers[inspectionField.key] === 'na' }"
                      @click="answerBoolean(inspectionField.key, 'na')">
                      N/A — Não aplicável
                    </button>
                  </div>

                  <!-- Number -->
                  <input v-else-if="inspectionField.field_type === 'number'"
                    v-model="draftAnswers[inspectionField.key]"
                    class="field-input" type="number" step="any" placeholder="Informe um número"
                    @change="triggerAutoSave()" />

                  <!-- Date -->
                  <input v-else-if="inspectionField.field_type === 'date'"
                    v-model="draftAnswers[inspectionField.key]"
                    class="field-input" type="date"
                    @change="triggerAutoSave()" />

                  <!-- Select -->
                  <select v-else-if="inspectionField.field_type === 'select'"
                    v-model="draftAnswers[inspectionField.key]"
                    class="field-input"
                    @change="triggerAutoSave()">
                    <option value="">— Selecione —</option>
                    <option
                      v-for="opt in selectOptions(inspectionField.config_json ?? {})"
                      :key="opt" :value="opt">{{ opt }}</option>
                  </select>

                  <!-- Text -->
                  <input v-else-if="inspectionField.field_type === 'text'"
                    v-model="draftAnswers[inspectionField.key]"
                    class="field-input" type="text" placeholder="Informe o valor"
                    @change="triggerAutoSave()" />

                  <!-- ── CONFORMIDADE ── -->
                  <div class="card-sep"><span class="card-sep-lbl">Conformidade</span></div>
                  <div class="conf-grid">
                    <button type="button" class="conf-btn conf-ok"
                      :class="{ active: conformityStatus[inspectionField.key] === 'conforme' }"
                      @click="setConformityCard(inspectionField.key, 'conforme')">
                      ✓ Conforme
                    </button>
                    <button type="button" class="conf-btn conf-err"
                      :class="{ active: conformityStatus[inspectionField.key] === 'nao_conforme' }"
                      @click="setNaoConformeCard(inspectionField.key)">
                      ✕ Não conforme
                    </button>
                  </div>
                  <!-- Justification preview (read-only) -->
                  <div
                    v-if="conformityStatus[inspectionField.key] === 'nao_conforme' && conformityJustification[inspectionField.key]"
                    class="conf-just-preview"
                    @click="setNaoConformeCard(inspectionField.key)"
                  >
                    ✎ {{ conformityJustification[inspectionField.key] }}
                  </div>
                  <p
                    v-if="inspectionField.field_type === 'boolean'"
                    class="swipe-hint"
                  >← Não conforme · Conforme →</p>

                  <!-- ── EVIDÊNCIAS DESTE CAMPO ── -->
                  <div class="card-sep"><span class="card-sep-lbl">Evidências deste campo</span></div>
                  <div class="evid-row">
                    <button
                      type="button"
                      class="evid-btn"
                      :disabled="!!evidenceUploading[inspectionField.key]"
                      @click="openEvidenceSheet(inspectionField.key)"
                    >
                      <span>📎</span>
                      <span
                        v-if="currentFieldEvidenceCount > 0"
                        class="evid-badge"
                      >{{ currentFieldEvidenceCount }}</span>
                      <span>{{ evidenceUploading[inspectionField.key] ? 'Enviando…' : 'Adicionar evidência' }}</span>
                    </button>
                    <div class="evid-thumbs">
                      <div
                        v-for="att in (evidenceAttachments[inspectionField.key] ?? []).slice(0, 3)"
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
                  <p v-if="evidenceErrors[inspectionField.key]" style="font-size:11px;color:var(--sa-danger);margin-top:4px;">
                    {{ evidenceErrors[inspectionField.key] }}
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
        <!-- ── HEADER (branco, fixo) ── -->
        <div class="insp-lshdr">
          <!-- Linha 1: voltar + nome + toggle + score ring -->
          <div class="insp-lshdr-top">
            <button type="button" class="insp-fback" @click="router.push({ name: 'submissions' })">
              <SvgIcon name="back" :size="16" />
            </button>
            <div class="insp-fhdr-info">
              <div class="insp-fhdr-name">{{ submission.form_name }}</div>
              <div class="insp-fhdr-sub">Em andamento</div>
            </div>
            <!-- Toggle inline na primeira linha -->
            <div class="insp-vt-seg insp-lshdr-toggle">
              <button class="insp-vt-btn" :class="String(viewMode) === 'card' ? 'active' : ''" @click="viewMode='card'">
                <span class="insp-vt-icon">▦</span> Cartão
              </button>
              <button class="insp-vt-btn" :class="String(viewMode) === 'list' ? 'active' : ''" @click="viewMode='list'">
                <span class="insp-vt-icon">☰</span> Lista
              </button>
            </div>
            <div class="score-ring" :style="scoreRingStyle">
              <div class="score-ring-inner">{{ liveScore !== null ? liveScore + '%' : '—' }}</div>
            </div>
          </div>

          <!-- Linha 2: barra de progresso + section chips (idêntica ao card mode) -->
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
            <div style="display:flex;flex-wrap:wrap;gap:10px;font-size:11px;color:var(--sa-muted);padding-top:4px;">
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
          </div>

          <!-- Filter bar (com separador acima) -->
          <div class="insp-filter-bar insp-filter-bar--with-sep">
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

        <!-- ── LISTA scrollável (fundo cinza) ── -->
        <div id="list-scroll-container" class="insp-list-container">
          <template v-for="field in filteredListFields">

            <!-- Section header sticky -->
            <div
              v-if="field.field_type === 'section'"
              :key="`sec-${field.key}`"
              v-show="visibleSectionKeys.has(field.key)"
              :id="`sec-${field.key}`"
              class="insp-list-sec-hdr"
            >
              <div class="insp-list-sec-ring" :style="sectionRingStyle(field.key)">
                <div class="insp-list-sec-ring-inner">
                  {{ sectionPct(field.key) === 100 ? '✓' : sectionPct(field.key) + '%' }}
                </div>
              </div>
              <span class="insp-list-sec-name">{{ field.label }}</span>
              <span class="insp-list-sec-cnt">{{ sectionProgress(field.key) }}</span>
            </div>

            <!-- Field row -->
            <div v-else :key="`row-${field.key}`" :id="`list-row-${field.key}`">
              <InspectionListRow
                :field="field"
                :position="fieldPosition(field)"
                :answer="draftAnswers[field.key] ?? ''"
                :conformity-status="conformityStatus[field.key]"
                :conformity-justification="conformityJustification[field.key] ?? ''"
                :is-completed="isCompleted"
                :is-pending-required="pendingRequiredFields.includes(field.key)"
                :evidence-count="evidenceAttachments[field.key]?.length ?? 0"
                :is-expanded="expandedListKey === field.key"
                @toggle="toggleListRow(field.key)"
                @update-answer="v => { draftAnswers[field.key] = v; triggerAutoSave() }"
                @set-conformity="s => setConformityList(field.key, s)"
                @update-justification="v => { conformityJustification[field.key] = v; triggerConformitySave() }"
                @request-evidence="openEvidenceSheet(field.key)"
                @request-justification="() => { setConformity(field.key, 'nao_conforme'); openJustificationSheet(field.key) }"
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

/* Header branco (fixo no topo) */
.insp-lshdr {
  background: #fff;
  border-bottom: 1px solid var(--sa-line);
  padding: 10px 14px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.insp-lshdr-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.insp-lshdr-toggle {
  margin: 0 auto 0 0;
  padding: 3px;
}
.insp-lshdr-prog {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.insp-lshdr-prog .insp-fprog-bar {
  flex: none;
  width: 100%;
  height: 6px;
}
.insp-lshdr-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 11px;
  color: var(--sa-muted);
}
.insp-lshdr-legend span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.insp-lshdr-legend .dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.insp-lshdr-legend .dot-ok   { background: var(--sa-ok); }
.insp-lshdr-legend .dot-err  { background: var(--sa-danger); }
.insp-lshdr-legend .dot-pend { background: var(--sa-line); }

/* Toggle + filtros dentro do header (sem borders) */
.insp-listshell .insp-view-toggle-bar {
  margin-bottom: 0; margin-top: 0; padding: 0;
  border-top: none; border-bottom: none;
  flex-shrink: 0;
}
.insp-listshell .insp-filter-bar {
  margin-bottom: 0; margin-top: 0; padding: 0;
  border-top: none; border-bottom: none;
  flex-shrink: 0;
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
