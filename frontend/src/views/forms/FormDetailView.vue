<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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
  return { key: '', label: '', field_type: 'boolean', required: false, position, config_json: {} }
}

function onFieldTypeChange(field: FormFieldCreatePayload) {
  const { visible_if } = field.config_json
  if (field.field_type === 'section') {
    field.config_json = {}
    field.required = false
  } else {
    field.config_json = visible_if ? { visible_if } : {}
  }
}

function getOptionsString(field: FormFieldCreatePayload): string {
  return Array.isArray(field.config_json.options)
    ? (field.config_json.options as string[]).join(', ')
    : ''
}

function setOptionsFromString(field: FormFieldCreatePayload, event: Event) {
  const opts = (event.target as HTMLInputElement).value
    .split(',').map(o => o.trim()).filter(Boolean)
  const { visible_if } = field.config_json
  const base: Record<string, unknown> = opts.length ? { options: opts } : {}
  field.config_json = visible_if ? { ...base, visible_if } : base
}

function setFieldWeight(field: FormFieldCreatePayload, event: Event) {
  const v = parseFloat((event.target as HTMLInputElement).value)
  field.config_json = { ...field.config_json, weight: v || 1 }
}

function setFieldAllowNa(field: FormFieldCreatePayload, event: Event) {
  const v = (event.target as HTMLSelectElement).value === 'true'
  field.config_json = { ...field.config_json, allow_na: v }
}

function otherAnswerFields(field: FormFieldCreatePayload, index: number) {
  return versionFields.value.filter((f, i) => i !== index && f.field_type !== 'section')
}

function triggerFieldForField(field: FormFieldCreatePayload, index: number): FormFieldCreatePayload | undefined {
  const key = (field.config_json.visible_if as Record<string, string> | undefined)?.field_key
  if (!key) return undefined
  return versionFields.value.find((f, i) => i !== index && f.key === key)
}

function triggerFieldType(field: FormFieldCreatePayload, index: number): string {
  return triggerFieldForField(field, index)?.field_type ?? ''
}

function triggerFieldOptions(field: FormFieldCreatePayload, index: number): string[] {
  const tf = triggerFieldForField(field, index)
  return Array.isArray(tf?.config_json?.options) ? (tf!.config_json.options as string[]) : []
}

function addVisibleIf(field: FormFieldCreatePayload) {
  field.config_json = { ...field.config_json, visible_if: { field_key: '', operator: 'eq', value: 'true' } }
}

function clearVisibleIf(field: FormFieldCreatePayload) {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { visible_if: _vi, ...rest } = field.config_json as Record<string, unknown>
  field.config_json = rest
}

function setVisibleIfTrigger(field: FormFieldCreatePayload, event: Event) {
  const key = (event.target as HTMLSelectElement).value
  const cur = (field.config_json.visible_if as Record<string, unknown>) ?? {}
  field.config_json = { ...field.config_json, visible_if: { ...cur, field_key: key } }
}

function setVisibleIfOp(field: FormFieldCreatePayload, event: Event) {
  const op = (event.target as HTMLSelectElement).value
  const cur = (field.config_json.visible_if as Record<string, unknown>) ?? {}
  field.config_json = { ...field.config_json, visible_if: { ...cur, operator: op } }
}

function setVisibleIfValue(field: FormFieldCreatePayload, event: Event) {
  const val = (event.target as HTMLInputElement | HTMLSelectElement).value
  const cur = (field.config_json.visible_if as Record<string, unknown>) ?? {}
  field.config_json = { ...field.config_json, visible_if: { ...cur, value: val } }
}

function visibleIfProp(field: FormFieldCreatePayload, prop: string): string {
  const vi = field.config_json.visible_if as Record<string, unknown> | undefined
  return vi ? String(vi[prop] ?? '') : ''
}

function openVersionComposer() {
  if (!formDetail.value) return
  versionFields.value = formDetail.value.current_version.fields.map(f => ({
    key: f.key, label: f.label, field_type: f.field_type,
    required: f.required, position: f.position, config_json: f.config_json,
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
              <div v-for="(field, index) in versionFields" :key="`v-${index}`" class="card card-p">
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                  <span style="font-size:11px;font-weight:700;color:var(--sa-muted);text-transform:uppercase;letter-spacing:.08em;">Campo {{ index + 1 }}</span>
                  <button v-if="versionFields.length > 1" type="button" class="btn-secondary btn-sm" @click="removeVersionField(index)">Remover</button>
                </div>
                <div style="display:grid;gap:10px;grid-template-columns:1fr 1fr;">
                  <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;"><span>Chave</span><input v-model="field.key" type="text" required /></label>
                  <label :style="field.field_type === 'section' ? 'display:grid;gap:6px;grid-column:1/-1;' : 'display:grid;gap:6px;'">
                    <span>{{ field.field_type === 'section' ? 'Título da seção' : 'Label' }}</span>
                    <input v-model="field.label" type="text" required />
                  </label>
                  <label style="display:grid;gap:6px;">
                    <span>Tipo</span>
                    <select v-model="field.field_type" @change="onFieldTypeChange(field)">
                      <option value="boolean">Sim / Não</option>
                      <option value="text">Texto</option>
                      <option value="number">Número</option>
                      <option value="select">Seleção</option>
                      <option value="date">Data</option>
                      <option value="section">── Seção ──</option>
                    </select>
                  </label>
                  <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;">
                    <span>Obrigatório</span>
                    <select v-model="field.required">
                      <option :value="true">Sim</option>
                      <option :value="false">Não</option>
                    </select>
                  </label>
                  <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
                    <span>Peso</span>
                    <input
                      :value="field.config_json.weight ?? 1"
                      type="number" min="0.1" step="0.1"
                      @input="setFieldWeight(field, $event)"
                    />
                  </label>
                  <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
                    <span>Permite N/A</span>
                    <select
                      :value="field.config_json.allow_na ? 'true' : 'false'"
                      @change="setFieldAllowNa(field, $event)"
                    >
                      <option value="false">Não</option>
                      <option value="true">Sim</option>
                    </select>
                  </label>
                  <label v-if="field.field_type === 'select'" style="display:grid;gap:6px;grid-column:1/-1;">
                    <span>Opções (separadas por vírgula)</span>
                    <input :value="getOptionsString(field)" type="text" placeholder="Ex: Conforme, Não conforme, Parcial" @input="setOptionsFromString(field, $event)" />
                  </label>

                  <!-- Conditional visibility rule -->
                  <div v-if="field.field_type !== 'section'" style="grid-column:1/-1;border-top:1px solid var(--sa-line);padding-top:10px;margin-top:2px;">
                    <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-muted);margin-bottom:8px;">Visibilidade condicional</div>
                    <div v-if="!field.config_json.visible_if">
                      <button type="button" class="btn-secondary btn-sm" @click="addVisibleIf(field)">+ Adicionar condição</button>
                    </div>
                    <div v-else style="display:grid;grid-template-columns:1fr 160px 1fr auto;gap:8px;align-items:end;">
                      <label style="display:grid;gap:4px;">
                        <span style="font-size:11px;color:var(--sa-muted);">Exibir se o campo</span>
                        <select :value="visibleIfProp(field, 'field_key')" @change="setVisibleIfTrigger(field, $event)">
                          <option value="">— selecione —</option>
                          <option v-for="f in otherAnswerFields(field, index)" :key="f.key" :value="f.key">{{ f.label || f.key }}</option>
                        </select>
                      </label>
                      <label style="display:grid;gap:4px;">
                        <span style="font-size:11px;color:var(--sa-muted);">Operador</span>
                        <select :value="visibleIfProp(field, 'operator')" @change="setVisibleIfOp(field, $event)">
                          <option value="eq">é igual a</option>
                          <option value="neq">é diferente de</option>
                        </select>
                      </label>
                      <label style="display:grid;gap:4px;">
                        <span style="font-size:11px;color:var(--sa-muted);">Valor</span>
                        <select v-if="triggerFieldType(field, index) === 'boolean'" :value="visibleIfProp(field, 'value')" @change="setVisibleIfValue(field, $event)">
                          <option value="true">Sim</option>
                          <option value="false">Não</option>
                          <option value="na">N/A</option>
                        </select>
                        <select v-else-if="triggerFieldType(field, index) === 'select'" :value="visibleIfProp(field, 'value')" @change="setVisibleIfValue(field, $event)">
                          <option value="">— selecione —</option>
                          <option v-for="opt in triggerFieldOptions(field, index)" :key="opt" :value="opt">{{ opt }}</option>
                        </select>
                        <input v-else :value="visibleIfProp(field, 'value')" type="text" placeholder="valor esperado" @input="setVisibleIfValue(field, $event)" />
                      </label>
                      <button type="button" class="btn-secondary btn-sm" style="align-self:end;" @click="clearVisibleIf(field)" title="Remover condição">✕</button>
                    </div>
                  </div>
                </div>
              </div>
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
