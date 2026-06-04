<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import FormFieldEditor from '@/components/forms/FormFieldEditor.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchForm } from '@/services/forms.service'
import { fetchSubmissions } from '@/services/submissions.service'
import { scoreClass } from '@/utils/score'
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

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não', text: 'Texto', number: 'Número',
  date: 'Data', select: 'Seleção',
}
const TYPE_COLOR: Record<string, string> = {
  boolean: 'var(--sa-brand)', text: 'var(--sa-muted)', number: 'var(--sa-ok)',
  date: 'var(--sa-warn)', select: 'var(--sa-muted)',
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
  return { key: '', label: '', field_type: 'boolean', required: false, position, config_json: {}, instruction: null }
}

function otherAnswerableFields(index: number): FormFieldCreatePayload[] {
  return versionFields.value.filter((f, i) => i !== index && f.field_type !== 'section')
}

function openVersionComposer() {
  if (!formDetail.value) return
  versionFields.value = formDetail.value.current_version.fields.map(f => ({
    key: f.key, label: f.label, field_type: f.field_type,
    required: f.required, position: f.position, config_json: f.config_json,
    instruction: f.instruction ?? null,
  }))
  versionError.value = null
  showVersionComposer.value = true
}

function addVersionField() {
  versionFields.value.push(createEmptyField(versionFields.value.length + 1))
}

function removeVersionField(index: number) {
  if (versionFields.value.length === 1) return
  versionFields.value.splice(index, 1)
  versionFields.value.forEach((f, i) => { f.position = i + 1 })
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
        instruction: f.instruction || null,
      })),
    })
    formDetail.value = await fetchForm(formId.value)
    showVersionComposer.value = false
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

        <!-- Version composer -->
        <div v-if="showVersionComposer" class="card card-p" style="margin-bottom:20px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
            <div>
              <div class="eyebrow">Nova versão</div>
              <div style="font-size:17px;font-weight:700;color:var(--sa-text);margin-top:3px;">{{ formDetail.name }}</div>
              <div style="font-size:12px;color:var(--sa-muted);margin-top:4px;">
                Edite os campos. Uma nova versão será publicada sem alterar inspeções anteriores.
              </div>
            </div>
            <button type="button" class="btn-secondary btn-sm" @click="showVersionComposer = false">Fechar</button>
          </div>

          <form style="display:grid;gap:12px;" @submit.prevent="submitVersion">
            <div class="slabel">Campos</div>
            <div style="display:grid;gap:10px;">
              <FormFieldEditor
                v-for="(_, index) in versionFields"
                :key="`v-${index}`"
                v-model="versionFields[index]"
                :index="index"
                :other-fields="otherAnswerableFields(index)"
                :show-remove="versionFields.length > 1"
                @remove="removeVersionField(index)"
              />
            </div>
            <p v-if="versionError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ versionError }}</p>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              <button type="button" class="btn-secondary btn-sm" @click="addVersionField">+ Adicionar campo</button>
              <button type="submit" class="btn-primary" :disabled="formsStore.isSaving">
                {{ formsStore.isSaving ? 'Publicando...' : 'Publicar nova versão' }}
              </button>
            </div>
          </form>
        </div>

        <!-- Fields list -->
        <div class="slabel" style="margin-bottom:10px;">
          Campos da versão atual (v{{ formDetail.current_version.version }})
        </div>
        <div class="fpanel">
          <template v-for="(field, i) in formDetail.current_version.fields">
            <!-- Section divider -->
            <div v-if="field.field_type === 'section'" :key="`sec-${field.id}`" class="section-divider">
              <span>{{ field.label }}</span>
            </div>

            <!-- Regular field row -->
            <div
              v-else
              :key="field.id"
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
                <div v-if="field.instruction" style="font-size:11px;color:var(--sa-muted);margin-top:4px;font-style:italic;">
                  {{ field.instruction }}
                </div>
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
                  :class="scoreClass(sub.score ?? 0)"
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
