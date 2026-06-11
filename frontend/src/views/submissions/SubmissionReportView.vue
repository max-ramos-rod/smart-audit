<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { listAttachments } from '@/services/attachments.service'
import { fetchFormVersion } from '@/services/forms.service'
import { exportSubmissionPdf } from '@/services/submissions.service'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
import type { AttachmentItem } from '@/types/attachments'
import type { FormVersion } from '@/types/forms'
import { scoreChipClass, scoreColorVar, scoreText } from '@/utils/score'
import { instanceKey } from '@/utils/inspectionInstances'
import { buildReportRows, componentLabel, type ReportRow } from '@/utils/reportRows'

const route = useRoute()
const router = useRouter()
const submissionsStore = useSubmissionsStore()

const submissionId = computed(() => route.params.id as string)
const submission   = computed(() => submissionsStore.current)
const formVersion  = ref<FormVersion | null>(null)
const isLoading    = ref(true)
const isExporting  = ref(false)

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não', text: 'Texto', number: 'Número', date: 'Data', select: 'Seleção',
}

const evidenceAttachments = ref<Record<string, AttachmentItem[]>>({})

onMounted(async () => {
  try {
    await submissionsStore.loadOne(submissionId.value)
    if (submission.value) {
      formVersion.value = await fetchFormVersion(
        submission.value.form_id,
        submission.value.form_version_id,
      )
      try {
        const all = await listAttachments(submissionId.value)
        // Agrupa evidência por instância (DR-0017): mesma chave dos ReportRow (field@asset).
        const grouped: Record<string, AttachmentItem[]> = {}
        for (const att of all) {
          if (!att.field_key) continue // evidência da inspeção/ativo: sem linha de campo no laudo
          const key = instanceKey(att.field_key, att.asset_id ?? null)
          if (!grouped[key]) grouped[key] = []
          grouped[key].push(att)
        }
        evidenceAttachments.value = grouped
      } catch {
        // non-fatal
      }
    }
  } finally {
    isLoading.value = false
  }
})

const fields = computed(() =>
  [...(formVersion.value?.fields ?? [])].sort((a, b) => a.position - b.position),
)

// Rótulo congelado de um componente, lido do snapshot (imune a renomeação do ativo).
function componentLabelFor(assetId: string | null | undefined): string | null {
  return componentLabel(submission.value?.components_snapshot, assetId)
}

// Expande campos escopados em uma linha por componente (DR-0002 T9, lógica pura em utils/reportRows).
const enrichedAnswers = computed<ReportRow[]>(() =>
  submission.value
    ? buildReportRows(fields.value, submission.value.answers, submission.value.components_snapshot)
    : [],
)

const boolAnswers    = computed(() => enrichedAnswers.value.filter(a => a.field.field_type === 'boolean'))
const nonBoolAnswers = computed(() => enrichedAnswers.value.filter(a => !['boolean', 'section'].includes(a.field.field_type)))

const conformes    = computed(() => boolAnswers.value.filter(a => a.value === true  || a.value === 'true').length)
const naoConformes = computed(() => boolAnswers.value.filter(a => a.value === false || a.value === 'false').length)
const naRespostas  = computed(() => boolAnswers.value.filter(a => a.value === 'na').length)
const semResposta  = computed(() => boolAnswers.value.filter(a => a.value === null  || a.value === '' || a.value === undefined).length)

const score = computed(() => submission.value?.score ?? null)
const scoreColor = computed(() => {
  if (score.value === null) return 'var(--sa-muted)'
  return scoreColorVar(score.value)
})
const scoreBadgeClass = computed(() => {
  if (score.value === null) return 'status-chip--neu'
  return scoreChipClass(score.value)
})
const scoreLabel = computed(() => {
  if (score.value === null) return '—'
  return scoreText(score.value)
})

function boolResult(val: unknown): 'ok' | 'err' | 'na' | 'none' {
  if (val === true  || val === 'true')  return 'ok'
  if (val === false || val === 'false') return 'err'
  if (val === 'na') return 'na'
  return 'none'
}

function formatValue(val: unknown, fieldType: string): string {
  if (val === null || val === undefined || val === '') return '—'
  if (fieldType === 'date') return new Date(val as string).toLocaleDateString('pt-BR')
  return String(val)
}

async function handleExport(inline = false) {
  if (!submission.value) return
  isExporting.value = true
  try {
    const blob = await exportSubmissionPdf(submissionId.value, inline)
    const url = URL.createObjectURL(blob)
    if (inline) {
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } else {
      const a = document.createElement('a')
      a.href = url
      a.download = `inspecao-${submissionId.value}.pdf`
      a.click()
      setTimeout(() => URL.revokeObjectURL(url), 10_000)
    }
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
              <RouterLink
                v-if="submission.asset_identifier"
                to="/assets"
                style="font-size:13px;font-weight:600;color:var(--sa-brand);text-decoration:none;"
              >🏷 {{ submission.asset_identifier }}</RouterLink>
            </div>
          </div>
          <div style="display:flex;gap:8px;flex-shrink:0;">
            <button
              v-if="submission.status === 'completed'"
              type="button"
              class="btn-secondary btn-sm"
              :disabled="isExporting"
              @click="handleExport(true)"
            >
              {{ isExporting ? 'Gerando...' : '⤢ Visualizar PDF' }}
            </button>
            <button
              type="button"
              class="btn-secondary btn-sm"
              :disabled="isExporting"
              @click="handleExport(false)"
            >
              {{ isExporting ? 'Gerando...' : '↓ Baixar PDF' }}
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
              <div v-if="naRespostas > 0" style="background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:8px;padding:10px 12px;">
                <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-muted);margin-bottom:3px;">N/A</div>
                <div style="font-size:14px;font-weight:700;color:var(--sa-muted);">{{ naRespostas }}</div>
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
              :key="ans.key"
              class="frow"
              style="display:flex;align-items:flex-start;gap:12px;"
            >
              <!-- Result dot -->
              <div :style="{
                width: '20px', height: '20px', borderRadius: '50%', flexShrink: 0, marginTop: '3px',
                background: boolResult(ans.value) === 'ok' ? 'var(--sa-ok-bg)' : boolResult(ans.value) === 'err' ? 'var(--sa-err-bg)' : 'var(--sa-line)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '9px', fontWeight: 800,
                color: boolResult(ans.value) === 'ok' ? 'var(--sa-ok)' : boolResult(ans.value) === 'err' ? 'var(--sa-danger)' : 'var(--sa-muted)',
              }">
                {{ boolResult(ans.value) === 'ok' ? '✓' : boolResult(ans.value) === 'err' ? '✗' : boolResult(ans.value) === 'na' ? 'N/A' : '—' }}
              </div>
              <div style="flex:1;min-width:0;">
                <div class="frow-type">Campo {{ i + 1 }}{{ ans.field.required ? ' · Obrigatório' : '' }}</div>
                <div class="frow-name" style="margin:2px 0 6px;">
                  {{ ans.field.label }}
                  <span v-if="ans.componentLabel" class="comp-chip">🧩 {{ ans.componentLabel }}</span>
                </div>
                <span v-if="boolResult(ans.value) === 'ok'"  style="font-size:13px;font-weight:700;color:var(--sa-ok);">✓ Sim (conforme)</span>
                <span v-else-if="boolResult(ans.value) === 'err'" style="font-size:13px;font-weight:700;color:var(--sa-danger);">✗ Não (não conforme)</span>
                <span v-else-if="boolResult(ans.value) === 'na'" style="font-size:13px;font-weight:600;color:var(--sa-muted);">N/A (não aplicável)</span>
                <span v-else style="font-size:13px;color:var(--sa-muted);">—</span>
                <!-- Evidências do campo (compartilhadas entre componentes — limitação T8) -->
                <div v-if="evidenceAttachments[ans.key]?.length" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;">
                  <a v-for="att in evidenceAttachments[ans.key]" :key="att.id"
                    :href="att.file_url" target="_blank" rel="noopener"
                    style="display:inline-flex;align-items:center;gap:5px;padding:3px 8px;background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:6px;font-size:11px;text-decoration:none;color:var(--sa-text);">
                    <img v-if="att.mime_type.startsWith('image/')" :src="att.file_url" style="width:18px;height:18px;object-fit:cover;border-radius:2px;flex-shrink:0;" />
                    <span v-else style="font-size:13px;flex-shrink:0;">{{ att.mime_type.startsWith('video/') ? '🎬' : att.mime_type.startsWith('audio/') ? '🎵' : '📄' }}</span>
                    <span style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ att.file_url.split('/').pop() }}</span>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- Non-boolean answers -->
        <template v-if="nonBoolAnswers.length">
          <div class="slabel" style="margin-bottom:10px;">Campos adicionais</div>
          <div class="fpanel" style="margin-bottom:16px;">
            <div v-for="ans in nonBoolAnswers" :key="ans.key" class="frow">
              <div class="frow-type">{{ TYPE_LABEL[ans.field.field_type] ?? ans.field.field_type }}</div>
              <div class="frow-name" style="margin-bottom:6px;">
                {{ ans.field.label }}
                <span v-if="ans.componentLabel" class="comp-chip">🧩 {{ ans.componentLabel }}</span>
              </div>
              <span style="font-size:13px;font-weight:500;color:var(--sa-text);">
                {{ formatValue(ans.value, ans.field.field_type) }}
              </span>
              <!-- Evidências do campo (compartilhadas entre componentes — limitação T8) -->
              <div v-if="evidenceAttachments[ans.key]?.length" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px;">
                <a v-for="att in evidenceAttachments[ans.key]" :key="att.id"
                  :href="att.file_url" target="_blank" rel="noopener"
                  style="display:inline-flex;align-items:center;gap:5px;padding:3px 8px;background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:6px;font-size:11px;text-decoration:none;color:var(--sa-text);">
                  <img v-if="att.mime_type.startsWith('image/')" :src="att.file_url" style="width:18px;height:18px;object-fit:cover;border-radius:2px;flex-shrink:0;" />
                  <span v-else style="font-size:13px;flex-shrink:0;">{{ att.mime_type.startsWith('video/') ? '🎬' : att.mime_type.startsWith('audio/') ? '🎵' : '📄' }}</span>
                  <span style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{{ att.file_url.split('/').pop() }}</span>
                </a>
              </div>
            </div>
          </div>
        </template>

        <!-- Non-conformity justifications -->
        <template v-if="submission.conformity?.some(c => c.status === 'nao_conforme')">
          <div class="slabel" style="margin-bottom:10px;color:var(--sa-danger);">Não conformidades registradas</div>
          <div class="fpanel" style="margin-bottom:16px;border:1px solid var(--sa-err-bd, #fecaca);">
            <div
              v-for="c in submission.conformity.filter(c => c.status === 'nao_conforme')"
              :key="`${c.field_key}@${c.asset_id ?? ''}`"
              class="frow"
            >
              <div style="display:flex;align-items:flex-start;gap:10px;">
                <div style="width:20px;height:20px;border-radius:50%;background:var(--sa-err-bg);display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;color:var(--sa-danger);flex-shrink:0;margin-top:2px;">✗</div>
                <div style="flex:1;min-width:0;">
                  <div class="frow-name" style="margin-bottom:4px;">
                    {{ fields.find(f => f.key === c.field_key)?.label ?? c.field_key }}
                    <span v-if="componentLabelFor(c.asset_id)" class="comp-chip">🧩 {{ componentLabelFor(c.asset_id) }}</span>
                  </div>
                  <div v-if="c.justification" style="font-size:12px;color:var(--sa-muted);background:var(--sa-err-bg);border-radius:6px;padding:6px 10px;">
                    {{ c.justification }}
                  </div>
                  <div v-else style="font-size:12px;color:var(--sa-muted);font-style:italic;">Sem justificativa</div>
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

<style scoped>
/* Chip de componente no laudo (campo escopado, DR-0002 T9) */
.comp-chip {
  display: inline-block;
  margin-left: 6px;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 99px;
  background: #f5f3ff;
  color: #7c3aed;
  vertical-align: middle;
}
</style>
