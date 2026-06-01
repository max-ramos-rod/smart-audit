<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import {
  createAttachment,
  deleteAttachment,
  listAttachments,
} from '@/services/attachments.service'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchFormVersion } from '@/services/forms.service'
import { uploadFile } from '@/services/uploads.service'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
import type { AttachmentItem } from '@/types/attachments'
import type { FormVersion } from '@/types/forms'

const route = useRoute()
const router = useRouter()
const submissionsStore = useSubmissionsStore()

const formVersion = ref<FormVersion | null>(null)
const draftAnswers = reactive<Record<string, string>>({})
const saveError = ref<string | null>(null)
const finishError = ref<string | null>(null)
const savedOnce = ref(false)

const submissionId = computed(() => route.params.id as string)
const submission = computed(() => submissionsStore.current)
const isCompleted = computed(() => submission.value?.status === 'completed')
const fields = computed(() => [...(formVersion.value?.fields ?? [])].sort((a, b) => a.position - b.position))

const visibleFields = computed(() =>
  fields.value.filter((field) => {
    const vi = field.config_json?.visible_if as Record<string, string> | undefined
    if (!vi?.field_key) return true
    const actual = String(draftAnswers[vi.field_key] ?? '').toLowerCase()
    const expected = String(vi.value ?? '').toLowerCase()
    return vi.operator === 'neq' ? actual !== expected : actual === expected
  }),
)

const pendingRequiredFields = ref<string[]>([])
const uploadingField = ref<string | null>(null)
const uploadErrors = reactive<Record<string, string>>({})

// Inspection mode
const inspectionMode = ref(false)
const inspectionIndex = ref(0)

const answerableFields = computed(() => visibleFields.value.filter((f) => f.field_type !== 'section'))

const answeredCount = computed(() =>
  answerableFields.value.filter((f) => {
    if (f.field_type === 'evidence') return (evidenceAttachments[f.key]?.length ?? 0) > 0
    return draftAnswers[f.key] !== undefined && draftAnswers[f.key] !== ''
  }).length,
)

const progressPct = computed(() =>
  answerableFields.value.length === 0 ? 0 : Math.round((answeredCount.value / answerableFields.value.length) * 100),
)

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

function enterInspectionMode() {
  inspectionIndex.value = 0
  inspectionMode.value = true
}

function inspectionNext() {
  if (inspectionIndex.value < answerableFields.value.length - 1) inspectionIndex.value++
}

function inspectionPrev() {
  if (inspectionIndex.value > 0) inspectionIndex.value--
}

// Large-form list view: progressive loading
const LIST_PAGE = 50
const listViewLimit = ref(LIST_PAGE)

const displayedListFields = computed(() => visibleFields.value.slice(0, listViewLimit.value))
const hasMoreFields = computed(() => listViewLimit.value < visibleFields.value.length)

function loadMoreFields() {
  listViewLimit.value += LIST_PAGE
}

// Sections for quick-jump navigation
const formSections = computed(() =>
  visibleFields.value
    .filter((f) => f.field_type === 'section')
    .map((f) => ({ key: f.key, label: f.label })),
)

// Reset list limit when the underlying field list changes (new form loaded)
watch(fields, () => { listViewLimit.value = LIST_PAGE })

// evidence state (per field_key)
const evidenceAttachments = reactive<Record<string, AttachmentItem[]>>({})
const evidenceUploading = reactive<Record<string, boolean>>({})
const evidenceErrors = reactive<Record<string, string>>({})

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não',
  text: 'Texto',
  number: 'Número',
  date: 'Data',
  photo: 'Foto',
  select: 'Seleção',
  evidence: 'Evidências',
}

// Mapping from evidence allowed_types to MIME strings
const EVIDENCE_MIME_MAP: Record<string, string[]> = {
  image: ['image/jpeg', 'image/png', 'image/webp'],
  video: ['video/mp4', 'video/quicktime', 'video/x-msvideo'],
  audio: ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4'],
  pdf: ['application/pdf'],
  document: ['application/pdf'],
}

const ALL_EVIDENCE_MIMES = ([] as string[]).concat(...Object.values(EVIDENCE_MIME_MAP)).join(',')

function evidenceAccept(configJson: Record<string, unknown>): string {
  const types = configJson.allowed_types
  if (!Array.isArray(types) || types.length === 0) return ALL_EVIDENCE_MIMES
  const mimes: string[] = []
  for (const t of types) {
    const mapped = EVIDENCE_MIME_MAP[t as string]
    if (mapped) mimes.push(...mapped)
  }
  return mimes.join(',')
}

function evidenceMaxFiles(configJson: Record<string, unknown>): number {
  const v = configJson.max_files
  return typeof v === 'number' ? v : 20
}

function evidenceCanAddMore(fieldKey: string, configJson: Record<string, unknown>): boolean {
  const current = evidenceAttachments[fieldKey]?.length ?? 0
  return current < evidenceMaxFiles(configJson)
}

function mimeCategory(mimeType: string): 'image' | 'video' | 'audio' | 'pdf' | 'file' {
  if (mimeType.startsWith('image/')) return 'image'
  if (mimeType.startsWith('video/')) return 'video'
  if (mimeType.startsWith('audio/')) return 'audio'
  if (mimeType === 'application/pdf') return 'pdf'
  return 'file'
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function selectOptions(configJson: Record<string, unknown>): string[] {
  return Array.isArray(configJson.options) ? (configJson.options as string[]) : []
}

function hasSelectOptions(configJson: Record<string, unknown>): boolean {
  return Array.isArray(configJson.options) && (configJson.options as unknown[]).length > 0
}

function populateDraft() {
  if (!submission.value) return
  for (const ans of submission.value.answers) {
    if (ans.value === null || ans.value === undefined) {
      draftAnswers[ans.field_key] = ''
    } else if (ans.field_type === 'boolean') {
      if (ans.value === 'na') {
        draftAnswers[ans.field_key] = 'na'
      } else {
        draftAnswers[ans.field_key] = ans.value ? 'true' : 'false'
      }
    } else if (ans.field_type === 'select') {
      draftAnswers[ans.field_key] = typeof ans.value === 'string' ? ans.value : ''
    } else {
      draftAnswers[ans.field_key] = String(ans.value)
    }
  }
}

async function loadEvidenceAttachments() {
  if (!submission.value || !formVersion.value) return
  const evidenceFields = formVersion.value.fields.filter((f) => f.field_type === 'evidence')
  if (evidenceFields.length === 0) return

  try {
    const all = await listAttachments(submissionId.value)
    for (const field of evidenceFields) {
      evidenceAttachments[field.key] = all.filter((a) => a.field_key === field.key)
    }
  } catch {
    // non-fatal; evidence list stays empty
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
  }
})

watch(
  () => submissionsStore.current?.id,
  (newId) => {
    if (newId === submissionId.value) populateDraft()
  },
)

function validateRequiredFields(): boolean {
  const missing = visibleFields.value
    .filter((field) => field.field_type !== 'section')
    .filter((field) => field.required)
    .filter((field) => {
      if (field.field_type === 'evidence') {
        return (evidenceAttachments[field.key]?.length ?? 0) === 0
      }
      const val = draftAnswers[field.key]
      return !val || val === ''
    })
    .map((field) => field.key)
  pendingRequiredFields.value = missing
  return missing.length === 0
}

function buildPayload() {
  return visibleFields.value
    .map((field) => {
      if (field.field_type === 'section') return null
      if (field.field_type === 'evidence') return null
      const raw = draftAnswers[field.key] ?? ''
      if (raw === '') return null

      let value: boolean | number | string | null = null
      if (field.field_type === 'boolean') {
        if (raw === 'na') {
          value = 'na'
        } else {
          value = raw === 'true'
        }
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

async function handlePhotoUpload(fieldKey: string, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploadingField.value = fieldKey
  delete uploadErrors[fieldKey]
  try {
    const result = await uploadFile(file)
    draftAnswers[fieldKey] = result.url
    await createAttachment(submissionId.value, {
      field_key: fieldKey,
      file_url: result.url,
      mime_type: result.mime_type,
      file_size: result.file_size,
    })
  } catch (err: any) {
    uploadErrors[fieldKey] = extractProblemMessage(err, 'Erro ao enviar arquivo.')
  } finally {
    uploadingField.value = null
    input.value = ''
  }
}

async function handleEvidenceUpload(fieldKey: string, configJson: Record<string, unknown>, event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
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
    const att = await createAttachment(submissionId.value, {
      field_key: fieldKey,
      file_url: result.url,
      mime_type: result.mime_type,
      file_size: result.file_size,
    })
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
  saveError.value = null
  savedOnce.value = false
  pendingRequiredFields.value = []

  if (!validateRequiredFields()) {
    finishError.value = `Campos obrigatórios pendentes: ${pendingRequiredFields.value.join(', ')}`
    return
  }

  try {
    await submissionsStore.updateAnswers(submissionId.value, { answers: buildPayload() })
    await submissionsStore.finish(submissionId.value)
  } catch (err: any) {
    finishError.value = extractProblemMessage(err, 'Não foi possível finalizar a inspeção.')
  }
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    in_progress: 'Em andamento',
    completed: 'Concluída',
    draft: 'Rascunho',
    cancelled: 'Cancelada',
  }
  return map[status] ?? status
}
</script>

<template>
  <AppShell>
    <div class="page">
      <div v-if="submissionsStore.isLoading" style="font-size: 13px; color: var(--sa-muted);">
        Carregando inspeção...
      </div>

      <template v-else-if="submission">
        <div class="back-hdr">
          <button type="button" class="back-btn" @click="router.push({ name: 'submissions' })">
            <SvgIcon name="back" :size="16" />
          </button>
          <div style="flex: 1; min-width: 0;">
            <div class="eyebrow">Inspeção</div>
            <h1 style="font-size: 18px; font-weight: 700; letter-spacing: -.01em; color: var(--sa-text); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
              {{ submission.form_name }}
            </h1>
            <div style="font-size: 12px; color: var(--sa-muted); margin-top: 2px;">
              Iniciada
              {{ new Date(submission.started_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) }}
            </div>
          </div>
          <span
            class="status-chip"
            style="flex-shrink: 0;"
            :class="{
              'status-chip--warn': submission.status === 'in_progress',
              'status-chip--inactive': submission.status === 'cancelled',
              'status-chip--neu': submission.status === 'draft',
            }"
          >
            {{ statusLabel(submission.status) }}
          </span>
        </div>

        <div v-if="isCompleted && submission.score !== null" class="card card-p" style="margin-bottom: 20px;">
          <div class="eyebrow" style="margin-bottom: 4px;">Score final</div>
          <div
            :style="{
              fontSize: '36px',
              fontWeight: 800,
              fontVariantNumeric: 'tabular-nums',
              color: submission.score >= 85 ? 'var(--sa-ok)' : submission.score >= 65 ? 'var(--sa-warn)' : 'var(--sa-danger)',
            }"
          >
            {{ submission.score }}%
          </div>

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

        <div v-if="fields.length">
          <!-- Progress bar + mode toggle -->
          <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px;">
            <div class="slabel" style="margin-bottom:0;">Campos</div>
            <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;">
              <span style="font-size:11px;font-weight:600;color:var(--sa-muted);">{{ answeredCount }}/{{ answerableFields.length }}</span>
              <button
                v-if="!isCompleted"
                type="button"
                class="btn-secondary btn-sm"
                @click="inspectionMode ? inspectionMode = false : enterInspectionMode()"
              >
                {{ inspectionMode ? 'Lista' : 'Modo inspeção' }}
              </button>
            </div>
          </div>
          <div v-if="answerableFields.length" class="insp-progress-bar" style="margin-bottom:12px;">
            <div class="insp-progress-fill" :style="{ width: progressPct + '%' }"></div>
          </div>

          <!-- Inspection mode: one field at a time -->
          <div v-if="inspectionMode && inspectionField" class="insp-card" style="margin-bottom:80px;">
            <div class="insp-meta">
              <span class="insp-section" v-if="inspectionSectionLabel">{{ inspectionSectionLabel }}</span>
              <span class="insp-counter">{{ inspectionIndex + 1 }} / {{ answerableFields.length }}</span>
            </div>
            <div style="margin-bottom:16px;">
              <div class="frow-type">{{ TYPE_LABEL[inspectionField.field_type] ?? inspectionField.field_type }}</div>
              <div class="frow-name" style="font-size:17px;margin-top:4px;">{{ inspectionField.label }}</div>
              <span v-if="inspectionField.required" class="status-chip" style="font-size:9px;margin-top:6px;display:inline-block;">Obrigatório</span>
            </div>

            <div v-if="pendingRequiredFields.includes(inspectionField.key)" class="frow-error-label" style="margin-bottom:8px;">
              Campo obrigatório não preenchido
            </div>

            <!-- Reuse the same input logic for the current inspection field -->
            <select v-if="inspectionField.field_type === 'boolean'" v-model="draftAnswers[inspectionField.key]" style="width:100%;">
              <option value="">— Sem resposta —</option>
              <option value="true">Sim (conforme)</option>
              <option value="false">Não (não conforme)</option>
              <option v-if="inspectionField.config_json?.allow_na" value="na">N/A (não aplicável)</option>
            </select>

            <input v-else-if="inspectionField.field_type === 'number'" v-model="draftAnswers[inspectionField.key]" type="number" style="width:100%;" :disabled="isCompleted" />
            <input v-else-if="inspectionField.field_type === 'date'" v-model="draftAnswers[inspectionField.key]" type="date" style="width:100%;" :disabled="isCompleted" />

            <template v-else-if="inspectionField.field_type === 'select'">
              <select v-if="hasSelectOptions(inspectionField.config_json ?? {})" v-model="draftAnswers[inspectionField.key]" style="width:100%;" :disabled="isCompleted">
                <option value="">— Sem resposta —</option>
                <option v-for="opt in selectOptions(inspectionField.config_json ?? {})" :key="opt" :value="opt">{{ opt }}</option>
              </select>
              <input v-else v-model="draftAnswers[inspectionField.key]" type="text" style="width:100%;" :disabled="isCompleted" />
            </template>

            <input v-else-if="inspectionField.field_type === 'text'" v-model="draftAnswers[inspectionField.key]" type="text" style="width:100%;" :disabled="isCompleted" />

            <div v-else-if="inspectionField.field_type === 'photo'" style="margin-top:4px;">
              <img v-if="draftAnswers[inspectionField.key]" :src="draftAnswers[inspectionField.key]" style="max-width:100%;border-radius:8px;margin-bottom:8px;" />
              <label v-if="!isCompleted" class="btn-secondary btn-sm" style="cursor:pointer;display:inline-block;">
                {{ draftAnswers[inspectionField.key] ? 'Trocar foto' : 'Adicionar foto' }}
                <input type="file" accept="image/jpeg,image/png,image/webp" style="display:none;" @change="handlePhotoUpload(inspectionField.key, $event)" />
              </label>
            </div>

            <div v-else-if="inspectionField.field_type === 'evidence'" style="margin-top:4px;">
              <div v-if="evidenceAttachments[inspectionField.key]?.length" style="display:grid;gap:6px;margin-bottom:8px;">
                <div v-for="att in evidenceAttachments[inspectionField.key]" :key="att.id" style="display:flex;align-items:center;gap:8px;font-size:12px;">
                  <img v-if="att.thumbnail_url" :src="att.thumbnail_url" style="width:36px;height:36px;object-fit:cover;border-radius:4px;" />
                  <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ att.file_url.split('/').pop() }}</span>
                  <button v-if="!isCompleted" type="button" class="btn-secondary btn-sm" style="padding:2px 6px;" @click="handleEvidenceDelete(inspectionField.key, att.id)">✕</button>
                </div>
              </div>
              <label v-if="!isCompleted && evidenceCanAddMore(inspectionField.key, inspectionField.config_json ?? {})" class="btn-secondary btn-sm" style="cursor:pointer;display:inline-block;">
                + Evidência
                <input type="file" :accept="evidenceAccept(inspectionField.config_json ?? {})" style="display:none;" @change="handleEvidenceUpload(inspectionField.key, inspectionField.config_json ?? {}, $event)" />
              </label>
              <span v-if="evidenceErrors[inspectionField.key]" style="display:block;font-size:11px;color:var(--sa-danger);margin-top:4px;">{{ evidenceErrors[inspectionField.key] }}</span>
            </div>

            <!-- Navigation -->
            <div class="insp-nav">
              <button type="button" class="btn-secondary" :disabled="inspectionIndex === 0" @click="inspectionPrev">← Anterior</button>
              <button
                v-if="inspectionIndex < answerableFields.length - 1"
                type="button" class="btn-primary"
                @click="inspectionNext"
              >Próximo →</button>
              <button v-else type="button" class="btn-primary" @click="inspectionMode = false">Ver resumo</button>
            </div>
          </div>

          <!-- Section quick-jump chips (only when sections exist and list mode) -->
          <div v-if="!inspectionMode && formSections.length" class="section-jump-bar" style="margin-bottom:10px;">
            <a v-for="sec in formSections" :key="sec.key" :href="`#sec-${sec.key}`" class="section-jump-chip">{{ sec.label }}</a>
          </div>

          <!-- List mode -->
          <div v-if="!inspectionMode" class="fpanel" style="margin-bottom: 16px;">
            <template v-for="field in displayedListFields">
            <!-- section header -->
            <div v-if="field.field_type === 'section'" :key="`sec-${field.id}`" :id="`sec-${field.key}`" class="section-divider">
              <span>{{ field.label }}</span>
            </div>

            <!-- regular field -->
            <div
              v-else
              :key="field.id"
              class="frow"
              :class="{ 'frow-error': pendingRequiredFields.includes(field.key) }"
            >
              <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 10px;">
                <div>
                  <div class="frow-type">{{ TYPE_LABEL[field.field_type] ?? field.field_type }}</div>
                  <div class="frow-name">{{ field.label }}</div>
                </div>
                <span v-if="field.required" class="status-chip" style="font-size: 9px; flex-shrink: 0;">Obrigatório</span>
              </div>

              <div v-if="pendingRequiredFields.includes(field.key)" class="frow-error-label">
                Campo obrigatório não preenchido
              </div>

              <!-- boolean -->
              <select
                v-if="field.field_type === 'boolean'"
                v-model="draftAnswers[field.key]"
                :disabled="isCompleted"
              >
                <option value="">— Sem resposta —</option>
                <option value="true">Sim (conforme)</option>
                <option value="false">Não (não conforme)</option>
                <option v-if="field.config_json?.allow_na" value="na">N/A (não aplicável)</option>
              </select>

              <!-- number -->
              <input
                v-else-if="field.field_type === 'number'"
                v-model="draftAnswers[field.key]"
                type="number"
                step="any"
                placeholder="Informe um número"
                :disabled="isCompleted"
              />

              <!-- date -->
              <input
                v-else-if="field.field_type === 'date'"
                v-model="draftAnswers[field.key]"
                type="date"
                :disabled="isCompleted"
              />

              <!-- photo (single image, backward compat) -->
              <div v-else-if="field.field_type === 'photo'">
                <img
                  v-if="draftAnswers[field.key]"
                  :src="draftAnswers[field.key]"
                  alt="Evidência"
                  style="width: 100%; height: 180px; object-fit: cover; border-radius: 8px; margin-bottom: 8px;"
                />
                <p v-if="draftAnswers[field.key]" style="font-size: 11px; color: var(--sa-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 8px;">
                  {{ draftAnswers[field.key] }}
                </p>
                <template v-if="!isCompleted">
                  <label style="cursor: pointer;">
                    <span class="inline-action">
                      {{ uploadingField === field.key ? 'Enviando...' : draftAnswers[field.key] ? 'Substituir foto' : 'Selecionar arquivo' }}
                    </span>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      style="display: none;"
                      :disabled="uploadingField === field.key"
                      @change="handlePhotoUpload(field.key, $event)"
                    />
                  </label>
                  <p v-if="uploadErrors[field.key]" style="font-size: 12px; font-weight: 600; color: var(--sa-danger); margin-top: 6px;">
                    {{ uploadErrors[field.key] }}
                  </p>
                </template>
              </div>

              <!-- evidence (multi-file) -->
              <div v-else-if="field.field_type === 'evidence'">
                <!-- Attachments list -->
                <div v-if="evidenceAttachments[field.key]?.length" style="display: grid; gap: 8px; margin-bottom: 10px;">
                  <div
                    v-for="att in evidenceAttachments[field.key]"
                    :key="att.id"
                    style="display: flex; align-items: center; gap: 10px; background: var(--sa-bg); border: 1px solid var(--sa-line); border-radius: 8px; padding: 8px 10px;"
                  >
                    <!-- image thumbnail -->
                    <img
                      v-if="mimeCategory(att.mime_type) === 'image'"
                      :src="att.file_url"
                      alt=""
                      style="width: 40px; height: 40px; object-fit: cover; border-radius: 4px; flex-shrink: 0;"
                    />
                    <!-- non-image icon -->
                    <div
                      v-else
                      style="width: 40px; height: 40px; border-radius: 4px; flex-shrink: 0; background: var(--sa-brand)18; display: flex; align-items: center; justify-content: center; font-size: 18px;"
                    >
                      {{ mimeCategory(att.mime_type) === 'video' ? '🎬' : mimeCategory(att.mime_type) === 'audio' ? '🎵' : '📄' }}
                    </div>

                    <div style="flex: 1; min-width: 0;">
                      <div style="font-size: 12px; font-weight: 600; color: var(--sa-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        {{ att.file_url.split('/').pop() }}
                      </div>
                      <div style="font-size: 11px; color: var(--sa-muted); margin-top: 2px;">
                        {{ mimeCategory(att.mime_type).toUpperCase() }} · {{ formatFileSize(att.file_size) }}
                      </div>
                    </div>

                    <button
                      v-if="!isCompleted"
                      type="button"
                      style="border: none; background: none; cursor: pointer; color: var(--sa-danger); font-size: 18px; line-height: 1; padding: 0 4px; flex-shrink: 0;"
                      title="Remover evidência"
                      @click="handleEvidenceDelete(field.key, att.id)"
                    >×</button>
                  </div>
                </div>

                <div v-if="!evidenceAttachments[field.key]?.length && isCompleted" style="font-size: 13px; color: var(--sa-muted);">
                  Nenhuma evidência registrada.
                </div>

                <!-- Add button -->
                <template v-if="!isCompleted && evidenceCanAddMore(field.key, field.config_json)">
                  <label style="cursor: pointer; display: inline-block;">
                    <span class="inline-action">
                      {{ evidenceUploading[field.key] ? 'Enviando...' : '+ Adicionar evidência' }}
                    </span>
                    <input
                      type="file"
                      :accept="evidenceAccept(field.config_json)"
                      style="display: none;"
                      :disabled="evidenceUploading[field.key]"
                      @change="handleEvidenceUpload(field.key, field.config_json, $event)"
                    />
                  </label>
                  <span style="font-size: 11px; color: var(--sa-muted); margin-left: 8px;">
                    {{ evidenceAttachments[field.key]?.length ?? 0 }}/{{ evidenceMaxFiles(field.config_json) }}
                  </span>
                </template>

                <p v-if="evidenceErrors[field.key]" style="font-size: 12px; font-weight: 600; color: var(--sa-danger); margin-top: 6px;">
                  {{ evidenceErrors[field.key] }}
                </p>
              </div>

              <!-- select -->
              <template v-else-if="field.field_type === 'select'">
                <select
                  v-if="selectOptions(field.config_json).length"
                  v-model="draftAnswers[field.key]"
                  :disabled="isCompleted"
                >
                  <option value="">— Selecione uma opção —</option>
                  <option v-for="opt in selectOptions(field.config_json)" :key="opt" :value="opt">
                    {{ opt }}
                  </option>
                </select>
                <input
                  v-else
                  v-model="draftAnswers[field.key]"
                  type="text"
                  placeholder="Informe a opção selecionada"
                  :disabled="isCompleted"
                />
              </template>

              <!-- text (default) -->
              <input
                v-else
                v-model="draftAnswers[field.key]"
                type="text"
                placeholder="Informe o valor"
                :disabled="isCompleted"
              />
            </div>
            </template>
          </div>

          <!-- Load more -->
          <div v-if="!inspectionMode && hasMoreFields" style="display:flex;justify-content:center;margin-bottom:12px;">
            <button type="button" class="btn-secondary btn-sm" @click="loadMoreFields">
              Carregar mais campos ({{ visibleFields.length - listViewLimit }} restantes)
            </button>
          </div>
          <div v-if="!inspectionMode" style="margin-bottom:68px;"></div>

          <p v-if="saveError" style="font-size: 13px; font-weight: 600; color: var(--sa-danger); margin-bottom: 8px;">{{ saveError }}</p>
          <p v-if="finishError" style="font-size: 13px; font-weight: 600; color: var(--sa-danger); margin-bottom: 8px;">{{ finishError }}</p>
        </div>

        <div class="sticky-act">
          <template v-if="!isCompleted">
            <button
              type="button"
              class="btn-secondary"
              :disabled="submissionsStore.isSaving"
              @click="handleSave"
            >
              {{ submissionsStore.isSaving ? 'Salvando...' : savedOnce ? '✓ Salvo' : 'Salvar rascunho' }}
            </button>
            <button
              type="button"
              class="btn-primary"
              :disabled="submissionsStore.isSaving"
              @click="handleFinish"
            >
              {{ submissionsStore.isSaving ? 'Finalizando...' : 'Finalizar inspeção' }}
            </button>
          </template>
          <button
            v-else
            type="button"
            class="btn-primary"
            @click="router.push({ name: 'submission-report', params: { id: submissionId } })"
          >
            Ver relatório completo →
          </button>
        </div>
      </template>

      <div v-else-if="!submissionsStore.isLoading" class="empty">
        <div class="empty-h">Inspeção não encontrada</div>
      </div>
    </div>
  </AppShell>
</template>
