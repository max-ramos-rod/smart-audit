<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { createAttachment } from '@/services/attachments.service'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchFormVersion } from '@/services/forms.service'
import { uploadFile } from '@/services/uploads.service'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
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

const pendingRequiredFields = ref<string[]>([])
const uploadingField = ref<string | null>(null)
const uploadErrors = reactive<Record<string, string>>({})

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não',
  text: 'Texto',
  number: 'Número',
  date: 'Data',
  photo: 'Foto',
  select: 'Seleção',
}

function selectOptions(configJson: Record<string, unknown>): string[] {
  return Array.isArray(configJson.options) ? (configJson.options as string[]) : []
}

function populateDraft() {
  if (!submission.value) return
  for (const ans of submission.value.answers) {
    if (ans.value === null || ans.value === undefined) {
      draftAnswers[ans.field_key] = ''
    } else if (ans.field_type === 'boolean') {
      draftAnswers[ans.field_key] = ans.value ? 'true' : 'false'
    } else if (ans.field_type === 'select') {
      draftAnswers[ans.field_key] = typeof ans.value === 'string' ? ans.value : ''
    } else {
      draftAnswers[ans.field_key] = String(ans.value)
    }
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
  }
})

watch(
  () => submissionsStore.current?.id,
  (newId) => {
    if (newId === submissionId.value) populateDraft()
  },
)

function validateRequiredFields(): boolean {
  const missing = fields.value
    .filter((field) => field.required)
    .filter((field) => {
      const val = draftAnswers[field.key]
      return !val || val === ''
    })
    .map((field) => field.key)
  pendingRequiredFields.value = missing
  return missing.length === 0
}

function buildPayload() {
  return fields.value
    .map((field) => {
      const raw = draftAnswers[field.key] ?? ''
      if (raw === '') return null

      let value: boolean | number | string | null = null
      if (field.field_type === 'boolean') {
        value = raw === 'true'
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
          </div>
        </div>

        <div v-if="fields.length">
          <div class="slabel" style="margin-bottom: 10px;">Campos</div>
          <div class="fpanel" style="margin-bottom: 80px;">
            <div
              v-for="field in fields"
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

              <select
                v-if="field.field_type === 'boolean'"
                v-model="draftAnswers[field.key]"
                :disabled="isCompleted"
              >
                <option value="">— Sem resposta —</option>
                <option value="true">Sim (conforme)</option>
                <option value="false">Não (não conforme)</option>
              </select>

              <input
                v-else-if="field.field_type === 'number'"
                v-model="draftAnswers[field.key]"
                type="number"
                step="any"
                placeholder="Informe um número"
                :disabled="isCompleted"
              />

              <input
                v-else-if="field.field_type === 'date'"
                v-model="draftAnswers[field.key]"
                type="date"
                :disabled="isCompleted"
              />

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

              <input
                v-else
                v-model="draftAnswers[field.key]"
                type="text"
                placeholder="Informe o valor"
                :disabled="isCompleted"
              />
            </div>
          </div>

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
