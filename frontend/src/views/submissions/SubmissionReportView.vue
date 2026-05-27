<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { fetchFormVersion } from '@/services/forms.service'
import { exportSubmissionPdf } from '@/services/submissions.service'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
import type { FormField, FormVersion } from '@/types/forms'
import type { SubmissionAnswer } from '@/types/submissions'

const route = useRoute()
const router = useRouter()
const submissionsStore = useSubmissionsStore()

const submissionId = computed(() => route.params.id as string)
const submission   = computed(() => submissionsStore.current)
const formVersion  = ref<FormVersion | null>(null)
const isLoading    = ref(true)
const isExporting  = ref(false)

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não', text: 'Texto', number: 'Número',
  date: 'Data', photo: 'Foto', select: 'Seleção',
}

onMounted(async () => {
  try {
    await submissionsStore.loadOne(submissionId.value)
    if (submission.value) {
      formVersion.value = await fetchFormVersion(
        submission.value.form_id,
        submission.value.form_version_id,
      )
    }
  } finally {
    isLoading.value = false
  }
})

const fields = computed(() =>
  [...(formVersion.value?.fields ?? [])].sort((a, b) => a.position - b.position),
)

interface EnrichedAnswer {
  field: FormField
  answer: SubmissionAnswer | undefined
  value: SubmissionAnswer['value']
}

const enrichedAnswers = computed<EnrichedAnswer[]>(() => {
  if (!submission.value) return []
  return fields.value.map(field => {
    const answer = submission.value!.answers.find(a => a.field_key === field.key)
    return { field, answer, value: answer?.value ?? null }
  })
})

const boolAnswers  = computed(() => enrichedAnswers.value.filter(a => a.field.field_type === 'boolean'))
const nonBoolAnswers = computed(() => enrichedAnswers.value.filter(a => a.field.field_type !== 'boolean' && a.field.field_type !== 'photo'))
const photoAnswers = computed(() => enrichedAnswers.value.filter(a => a.field.field_type === 'photo' && a.value))

const conformes    = computed(() => boolAnswers.value.filter(a => a.value === true  || a.value === 'true').length)
const naoConformes = computed(() => boolAnswers.value.filter(a => a.value === false || a.value === 'false').length)
const semResposta  = computed(() => boolAnswers.value.filter(a => a.value === null  || a.value === '' || a.value === undefined).length)

const score = computed(() => submission.value?.score ?? null)
const scoreColor = computed(() => {
  if (score.value === null) return 'var(--sa-muted)'
  return score.value >= 85 ? 'var(--sa-ok)' : score.value >= 65 ? 'var(--sa-warn)' : 'var(--sa-danger)'
})
const scoreBadgeClass = computed(() => {
  if (score.value === null) return 'status-chip--neu'
  return score.value >= 85 ? '' : score.value >= 65 ? 'status-chip--warn' : 'status-chip--inactive'
})
const scoreLabel = computed(() => {
  if (score.value === null) return '—'
  return score.value >= 85 ? 'Aprovado' : score.value >= 65 ? 'Atenção' : 'Reprovado'
})

function boolResult(val: unknown): 'ok' | 'err' | 'none' {
  if (val === true  || val === 'true')  return 'ok'
  if (val === false || val === 'false') return 'err'
  return 'none'
}

function formatValue(val: unknown, fieldType: string): string {
  if (val === null || val === undefined || val === '') return '—'
  if (fieldType === 'date') return new Date(val as string).toLocaleDateString('pt-BR')
  return String(val)
}

async function handleExport() {
  if (!submission.value) return
  isExporting.value = true
  try {
    const blob = await exportSubmissionPdf(submissionId.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `inspecao-${submissionId.value}.pdf`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 10_000)
  } finally {
    isExporting.value = false
  }
}
</script>

<template>
  <AppShell>
    <div class="page">

      <div v-if="isLoading" style="font-size:13px;color:var(--sa-muted);">Carregando relatório...</div>

      <template v-else-if="submission">

        <!-- Back header + export button -->
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:20px;flex-wrap:wrap;">
          <div class="back-hdr" style="margin:0;flex:1;min-width:0;">
            <button type="button" class="back-btn" @click="router.back()">
              <SvgIcon name="back" :size="16" />
            </button>
            <div style="flex:1;min-width:0;">
              <div class="eyebrow" style="margin-bottom:4px;">Relatório completo</div>
              <h1 style="font-size:18px;font-weight:700;letter-spacing:-.01em;color:var(--sa-text);line-height:1.2;">
                {{ submission.form_name }}
              </h1>
            </div>
          </div>
          <div style="display:flex;gap:8px;flex-shrink:0;">
            <button
              type="button"
              class="btn-secondary btn-sm"
              :disabled="isExporting"
              @click="handleExport"
            >
              {{ isExporting ? 'Gerando...' : '↓ Exportar PDF' }}
            </button>
          </div>
        </div>

        <!-- Score hero card -->
        <div class="card" style="padding:20px 24px;margin-bottom:16px;display:grid;gap:20px;grid-template-columns:auto 1fr;">
          <!-- Score number -->
          <div style="text-align:center;min-width:100px;">
            <div class="eyebrow" style="margin-bottom:8px;">Score final</div>
            <div style="display:flex;align-items:baseline;gap:2px;justify-content:center;">
              <span :style="{
                fontSize: '48px', fontWeight: 800, letterSpacing: '-.04em',
                color: scoreColor, fontVariantNumeric: 'tabular-nums', lineHeight: 1,
              }">{{ score ?? '—' }}</span>
              <span v-if="score !== null" :style="{ fontSize: '22px', fontWeight: 700, color: scoreColor }">%</span>
            </div>
            <div style="margin-top:8px;">
              <span class="status-chip" :class="scoreBadgeClass">{{ scoreLabel }}</span>
            </div>
          </div>

          <!-- Progress + meta -->
          <div style="display:grid;gap:10px;">
            <div v-if="score !== null" style="height:8px;background:var(--sa-line);border-radius:99px;overflow:hidden;">
              <div :style="{ height:'100%', borderRadius:'99px', background: scoreColor, width: score + '%', transition: 'width .4s' }"></div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
              <div style="background:var(--sa-ok-bg);border:1px solid var(--sa-ok-bd, #bbf7d0);border-radius:8px;padding:10px 12px;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-muted);margin-bottom:3px;">Conformes</div>
                <div style="font-size:14px;font-weight:700;color:var(--sa-ok);">{{ conformes }} / {{ boolAnswers.length }}</div>
              </div>
              <div style="background:var(--sa-err-bg);border:1px solid var(--sa-err-bd, #fecaca);border-radius:8px;padding:10px 12px;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-muted);margin-bottom:3px;">Não conformes</div>
                <div style="font-size:14px;font-weight:700;color:var(--sa-danger);">{{ naoConformes }} / {{ boolAnswers.length }}</div>
              </div>
              <div style="background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:8px;padding:10px 12px;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-muted);margin-bottom:3px;">Sem resposta</div>
                <div style="font-size:14px;font-weight:700;color:var(--sa-muted);">{{ semResposta }}</div>
              </div>
              <div style="background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:8px;padding:10px 12px;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-muted);margin-bottom:3px;">Concluído em</div>
                <div style="font-size:13px;font-weight:700;color:var(--sa-text);">
                  {{ submission.finished_at
                    ? new Date(submission.finished_at).toLocaleString('pt-BR', { day:'2-digit', month:'2-digit', year:'2-digit', hour:'2-digit', minute:'2-digit' })
                    : '—' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Boolean answers -->
        <template v-if="boolAnswers.length">
          <div class="slabel" style="margin-bottom:10px;">Campos de conformidade</div>
          <div class="fpanel" style="margin-bottom:16px;">
            <div
              v-for="(ans, i) in boolAnswers"
              :key="ans.field.key"
              class="frow"
              style="display:flex;align-items:flex-start;gap:12px;"
            >
              <!-- Result dot -->
              <div :style="{
                width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0, marginTop: '3px',
                background: boolResult(ans.value) === 'ok' ? 'var(--sa-ok-bg)' : boolResult(ans.value) === 'err' ? 'var(--sa-err-bg)' : 'var(--sa-line)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '11px', fontWeight: 800,
                color: boolResult(ans.value) === 'ok' ? 'var(--sa-ok)' : boolResult(ans.value) === 'err' ? 'var(--sa-danger)' : 'var(--sa-muted)',
              }">
                {{ boolResult(ans.value) === 'ok' ? '✓' : boolResult(ans.value) === 'err' ? '✗' : '—' }}
              </div>
              <div style="flex:1;min-width:0;">
                <div class="frow-type">Campo {{ i + 1 }}{{ ans.field.required ? ' · Obrigatório' : '' }}</div>
                <div class="frow-name" style="margin:2px 0 6px;">{{ ans.field.label }}</div>
                <span v-if="boolResult(ans.value) === 'ok'"  style="font-size:13px;font-weight:700;color:var(--sa-ok);">✓ Sim (conforme)</span>
                <span v-else-if="boolResult(ans.value) === 'err'" style="font-size:13px;font-weight:700;color:var(--sa-danger);">✗ Não (não conforme)</span>
                <span v-else style="font-size:13px;color:var(--sa-muted);">—</span>
              </div>
            </div>
          </div>
        </template>

        <!-- Non-boolean answers -->
        <template v-if="nonBoolAnswers.length">
          <div class="slabel" style="margin-bottom:10px;">Campos adicionais</div>
          <div class="fpanel" style="margin-bottom:16px;">
            <div v-for="ans in nonBoolAnswers" :key="ans.field.key" class="frow">
              <div class="frow-type">{{ TYPE_LABEL[ans.field.field_type] ?? ans.field.field_type }}</div>
              <div class="frow-name" style="margin-bottom:6px;">{{ ans.field.label }}</div>
              <span style="font-size:13px;font-weight:500;color:var(--sa-text);">
                {{ formatValue(ans.value, ans.field.field_type) }}
              </span>
            </div>
          </div>
        </template>

        <!-- Photo evidence -->
        <template v-if="photoAnswers.length">
          <div class="slabel" style="margin-bottom:10px;">Evidências fotográficas</div>
          <div class="card" style="padding:16px;margin-bottom:16px;">
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:10px;">
              <div v-for="ans in photoAnswers" :key="ans.field.key">
                <img
                  :src="String(ans.value)"
                  :alt="ans.field.label"
                  style="width:100%;aspect-ratio:4/3;object-fit:cover;border-radius:8px;"
                />
                <div style="font-size:11px;color:var(--sa-muted);margin-top:4px;text-align:center;">
                  {{ ans.field.label }}
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Info footer -->
        <div class="info-box">
          Relatório gerado pelo Smart Audit em {{ new Date().toLocaleDateString('pt-BR') }}.
          Score calculado com base nos {{ boolAnswers.length }} campos booleanos da inspeção.
          Formulário: {{ submission.form_name }}<template v-if="formVersion"> v{{ formVersion.version }}</template>.
        </div>

      </template>

      <div v-else-if="!isLoading" class="empty">
        <div class="empty-h">Inspeção não encontrada</div>
      </div>

    </div>
  </AppShell>
</template>
