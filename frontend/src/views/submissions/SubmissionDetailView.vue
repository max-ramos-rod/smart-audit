<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { createAttachment } from '@/services/attachments.service'
import { fetchFormVersion } from '@/services/forms.service'
import { exportSubmissionPdf } from '@/services/submissions.service'
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
const fields = computed(() =>
  [...(formVersion.value?.fields ?? [])].sort((a, b) => a.position - b.position),
)

const uploadingField = ref<string | null>(null)
const uploadErrors = reactive<Record<string, string>>({})

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
    } else if (
      ans.field_type === 'select' &&
      typeof ans.value === 'object' &&
      ans.value !== null
    ) {
      draftAnswers[ans.field_key] =
        ((ans.value as Record<string, unknown>).option as string) ?? ''
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

function buildPayload() {
  return fields.value
    .map((field) => {
      const raw = draftAnswers[field.key] ?? ''
      if (raw === '') return null

      let value: boolean | number | string | Record<string, unknown> | null = null
      if (field.field_type === 'boolean') {
        value = raw === 'true' ? true : false
      } else if (field.field_type === 'number') {
        const n = parseFloat(raw)
        value = isNaN(n) ? null : n
      } else if (field.field_type === 'select') {
        value = { option: raw }
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
  } catch (err: any) {
    saveError.value = extractProblemMessage(err, 'Não foi possível salvar as respostas.')
  }
}

async function handleFinish() {
  finishError.value = null
  saveError.value = null
  savedOnce.value = false
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

const isExporting = ref(false)

async function handleExport() {
  if (!submission.value) return
  isExporting.value = true
  try {
    const blob = await exportSubmissionPdf(submissionId.value)
    const url = URL.createObjectURL(blob)
    window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 10_000)
  } finally {
    isExporting.value = false
  }
}
</script>

<template>
  <AppShell>
    <section class="flex flex-wrap items-center justify-between gap-3 px-1">
      <div>
        <p class="eyebrow">Inspeção</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-sa-text">
          {{ submission?.form_name ?? 'Carregando...' }}
        </h2>
        <p class="mt-2 text-sm text-sa-muted">
          Iniciada em
          {{
            submission?.started_at
              ? new Date(submission.started_at).toLocaleString('pt-BR')
              : '—'
          }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <span
          v-if="submission"
          class="status-chip"
          :class="{ 'status-chip--inactive': submission.status !== 'completed' }"
        >
          {{ statusLabel(submission.status) }}
        </span>
        <BaseButton
          v-if="isCompleted"
          type="button"
          variant="ghost"
          :disabled="isExporting"
          @click="handleExport"
        >
          {{ isExporting ? 'Gerando PDF...' : 'Exportar PDF' }}
        </BaseButton>
        <BaseButton type="button" variant="ghost" @click="router.push({ name: 'submissions' })">
          Voltar
        </BaseButton>
      </div>
    </section>

    <div v-if="submissionsStore.isLoading" class="surface-panel p-6 text-center">
      <p class="text-sm text-sa-muted">Carregando inspeção...</p>
    </div>

    <template v-else-if="submission && fields.length">
      <section v-if="submission.score !== null && isCompleted" class="surface-panel p-5">
        <p class="eyebrow">Score final</p>
        <strong class="mt-2 block text-3xl font-semibold text-sa-text">
          {{ submission.score }}%
        </strong>
        <p class="mt-1 text-sm text-sa-muted">Baseado nos campos booleanos respondidos.</p>
      </section>

      <section class="surface-panel p-5 sm:p-6">
        <div class="mb-5">
          <p class="eyebrow">Campos</p>
          <h3 class="mt-2 text-xl font-semibold text-sa-text">Respostas</h3>
        </div>

        <div class="grid gap-5">
          <article
            v-for="field in fields"
            :key="field.id"
            class="rounded-3xl border border-[color:var(--sa-line)] bg-white/70 p-4"
          >
            <div class="mb-3 flex items-start justify-between gap-3">
              <div>
                <p class="eyebrow">{{ field.field_type }}</p>
                <h4 class="mt-1 text-base font-semibold text-sa-text">{{ field.label }}</h4>
              </div>
              <span v-if="field.required" class="status-chip text-[0.65rem]">Obrigatório</span>
            </div>

            <!-- boolean -->
            <label v-if="field.field_type === 'boolean'" class="grid gap-2">
              <select
                v-model="draftAnswers[field.key]"
                :disabled="isCompleted"
              >
                <option value="">— Sem resposta —</option>
                <option value="true">Sim (conforme)</option>
                <option value="false">Não (não conforme)</option>
              </select>
            </label>

            <!-- number -->
            <label v-else-if="field.field_type === 'number'" class="grid gap-2">
              <input
                v-model="draftAnswers[field.key]"
                type="number"
                step="any"
                placeholder="Informe um número"
                :disabled="isCompleted"
              />
            </label>

            <!-- date -->
            <label v-else-if="field.field_type === 'date'" class="grid gap-2">
              <input
                v-model="draftAnswers[field.key]"
                type="date"
                :disabled="isCompleted"
              />
            </label>

            <!-- photo -->
            <div v-else-if="field.field_type === 'photo'" class="grid gap-2">
              <img
                v-if="draftAnswers[field.key]"
                :src="draftAnswers[field.key]"
                class="h-48 w-full rounded-2xl object-cover"
                alt="Evidência"
              />
              <p v-if="draftAnswers[field.key]" class="truncate text-xs text-sa-muted">
                {{ draftAnswers[field.key] }}
              </p>
              <template v-if="!isCompleted">
                <label class="cursor-pointer">
                  <span class="inline-action">
                    {{ uploadingField === field.key ? 'Enviando...' : draftAnswers[field.key] ? 'Substituir' : 'Selecionar arquivo' }}
                  </span>
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    class="sr-only"
                    :disabled="uploadingField === field.key"
                    @change="handlePhotoUpload(field.key, $event)"
                  />
                </label>
                <p v-if="uploadErrors[field.key]" class="text-xs font-medium text-sa-danger">
                  {{ uploadErrors[field.key] }}
                </p>
              </template>
            </div>

            <!-- select -->
            <label v-else-if="field.field_type === 'select'" class="grid gap-2">
              <select v-model="draftAnswers[field.key]" :disabled="isCompleted">
                <option value="">— Sem resposta —</option>
                <option
                  v-for="opt in selectOptions(field.config_json)"
                  :key="opt"
                  :value="opt"
                >
                  {{ opt }}
                </option>
              </select>
            </label>

            <!-- text (default) -->
            <label v-else class="grid gap-2">
              <input
                v-model="draftAnswers[field.key]"
                type="text"
                placeholder="Informe o valor"
                :disabled="isCompleted"
              />
            </label>
          </article>
        </div>

        <div v-if="!isCompleted" class="mt-6 flex flex-wrap gap-3">
          <BaseButton
            type="button"
            variant="ghost"
            :disabled="submissionsStore.isSaving"
            @click="handleSave"
          >
            {{ submissionsStore.isSaving ? 'Salvando...' : 'Salvar rascunho' }}
          </BaseButton>
          <BaseButton
            type="button"
            :disabled="submissionsStore.isSaving"
            @click="handleFinish"
          >
            {{ submissionsStore.isSaving ? 'Finalizando...' : 'Finalizar inspeção' }}
          </BaseButton>
        </div>

        <p v-if="saveError" class="mt-3 text-sm font-medium text-sa-danger">{{ saveError }}</p>
        <p v-if="finishError" class="mt-3 text-sm font-medium text-sa-danger">{{ finishError }}</p>
        <p v-if="savedOnce && !saveError && !submissionsStore.isSaving" class="mt-3 text-sm font-medium text-sa-brand">
          Respostas salvas com sucesso.
        </p>
      </section>
    </template>

    <div v-else-if="!submissionsStore.isLoading" class="surface-panel p-6 text-center">
      <p class="eyebrow">Sem dados</p>
      <h3 class="mt-3 text-xl font-semibold text-sa-text">Inspeção não encontrada</h3>
    </div>
  </AppShell>
</template>
