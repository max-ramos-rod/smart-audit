<template>
  <!-- Compact row -->
  <div class="ilr-row" @click="$emit('toggle')">
    <!-- Left status bar -->
    <div
      class="ilr-bar"
      :style="{ background: barColor }"
    />

    <!-- Position number -->
    <span
      class="ilr-pos"
      style="
        font-family: 'DM Mono', monospace;
        font-size: 11px;
        color: var(--sa-muted);
        width: 22px;
        flex-shrink: 0;
        user-select: none;
      "
    >{{ posLabel }}</span>

    <!-- Field-type chip -->
    <span
      class="ilr-type-chip"
      :style="typeChipStyle"
    >{{ typeLabel }}</span>

    <!-- Field label -->
    <span class="ilr-label">{{ field.label }}</span>

    <!-- Answer label (only when answered) -->
    <span
      v-if="ansLabel"
      class="ilr-ans-lbl"
      style="
        font-family: 'DM Mono', monospace;
        font-size: 10px;
        color: var(--sa-muted);
        flex-shrink: 0;
        max-width: 80px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      "
    >{{ ansLabel }}</span>

    <!-- Evidence badge -->
    <span
      v-if="evidenceCount > 0"
      class="ilr-evid-dot"
      style="
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        border-radius: 50%;
        background: var(--sa-brand-soft);
        color: var(--sa-brand);
        font-size: 10px;
        font-weight: 800;
        flex-shrink: 0;
      "
    >{{ evidenceCount }}</span>

    <!-- Status chip -->
    <span
      class="ilr-status-chip"
      :style="statusChipStyle"
    >{{ statusLabel }}</span>

    <!-- Arrow -->
    <span
      style="font-size: 14px; color: var(--sa-muted); flex-shrink: 0; transition: transform .15s;"
      :style="{ transform: isExpanded ? 'rotate(90deg)' : 'none' }"
    >›</span>
  </div>

  <!-- Expanded panel -->
  <div v-show="isExpanded" class="ilr-panel">

    <!-- RESPOSTA section -->
    <div class="ilr-sep-lbl">RESPOSTA</div>

    <!-- Boolean -->
    <div v-if="field.field_type === 'boolean'" style="display: flex; gap: 8px; flex-wrap: wrap;">
      <button
        class="ilr-bool-btn ilr-bool-btn--sim"
        :class="{ active: answer === 'true' }"
        :disabled="isCompleted"
        @click.stop="$emit('updateAnswer', 'true')"
      >✓ Sim</button>
      <button
        class="ilr-bool-btn ilr-bool-btn--nao"
        :class="{ active: answer === 'false' }"
        :disabled="isCompleted"
        @click.stop="$emit('updateAnswer', 'false')"
      >✕ Não</button>
      <button
        v-if="field.config_json?.allow_na"
        class="ilr-bool-btn ilr-bool-btn--na"
        :class="{ active: answer === 'na' }"
        :disabled="isCompleted"
        @click.stop="$emit('updateAnswer', 'na')"
      >N/A</button>
    </div>

    <!-- Select -->
    <select
      v-else-if="field.field_type === 'select'"
      class="ilr-input"
      :value="answer"
      :disabled="isCompleted"
      @change.stop="$emit('updateAnswer', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">— Selecione —</option>
      <option
        v-for="opt in selectOptions"
        :key="opt"
        :value="opt"
      >{{ opt }}</option>
    </select>

    <!-- Number -->
    <input
      v-else-if="field.field_type === 'number'"
      type="number"
      class="ilr-input"
      :value="answer"
      :disabled="isCompleted"
      @input.stop="$emit('updateAnswer', ($event.target as HTMLInputElement).value)"
    />

    <!-- Date -->
    <input
      v-else-if="field.field_type === 'date'"
      type="date"
      class="ilr-input"
      :value="answer"
      :disabled="isCompleted"
      @change.stop="$emit('updateAnswer', ($event.target as HTMLInputElement).value)"
    />

    <!-- Text (fallback) -->
    <input
      v-else
      type="text"
      class="ilr-input"
      :value="answer"
      :disabled="isCompleted"
      @input.stop="$emit('updateAnswer', ($event.target as HTMLInputElement).value)"
    />

    <!-- CONFORMIDADE section -->
    <div class="ilr-sep-lbl">CONFORMIDADE</div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
      <button
        class="ilr-conf-btn ilr-conf-ok"
        :class="{ active: conformityStatus === 'conforme' }"
        :disabled="isCompleted"
        @click.stop="onConforme"
      >✓ Conforme</button>
      <button
        class="ilr-conf-btn ilr-conf-err"
        :class="{ active: conformityStatus === 'nao_conforme' }"
        :disabled="isCompleted"
        @click.stop="onNaoConforme"
      >✕ Não conforme</button>
    </div>

    <!-- Inline justification when nao_conforme + already has text -->
    <textarea
      v-if="conformityStatus === 'nao_conforme' && conformityJustification"
      class="ilr-input"
      style="margin-top: 8px; resize: vertical; min-height: 60px;"
      :value="conformityJustification"
      :disabled="isCompleted"
      @input.stop="$emit('updateJustification', ($event.target as HTMLTextAreaElement).value)"
    />

    <!-- EVIDÊNCIAS section -->
    <div class="ilr-sep-lbl">EVIDÊNCIAS DESTE CAMPO</div>
    <button
      class="ilr-evid-btn"
      @click.stop="$emit('requestEvidence')"
    >
      📎
      <span v-if="evidenceCount > 0" class="ilr-evid-badge">{{ evidenceCount }}</span>
      Adicionar evidência
    </button>

  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FormField } from '@/types/forms'

const props = defineProps<{
  field: FormField
  position: number
  answer: string
  conformityStatus: 'conforme' | 'nao_conforme' | undefined
  conformityJustification: string
  isCompleted: boolean
  isPendingRequired: boolean
  evidenceCount: number
  isExpanded: boolean
}>()

const emit = defineEmits<{
  toggle: []
  updateAnswer: [value: string]
  setConformity: [status: 'conforme' | 'nao_conforme']
  updateJustification: [value: string]
  requestEvidence: []
  requestJustification: []
}>()

// ── Derived values ──────────────────────────────────────────────────────────

const posLabel = computed(() => String(props.position).padStart(2, '0'))

// Left bar color
const barColor = computed(() => {
  if (props.conformityStatus === 'conforme') return 'var(--sa-ok)'
  if (props.conformityStatus === 'nao_conforme') return 'var(--sa-danger)'
  return 'var(--sa-warn)'
})

// Field-type chip label + style
const typeLabel = computed(() => {
  switch (props.field.field_type) {
    case 'boolean': return 'S/N'
    case 'text':    return 'TXT'
    case 'number':  return 'NUM'
    case 'select':  return 'SEL'
    case 'date':    return 'DAT'
    default:        return props.field.field_type.slice(0, 3).toUpperCase()
  }
})

const typeChipStyle = computed(() => {
  const base = {
    fontFamily: "'DM Mono', monospace",
    fontSize: '9px',
    fontWeight: '700',
    borderRadius: '4px',
    padding: '2px 5px',
    flexShrink: '0',
  }
  switch (props.field.field_type) {
    case 'boolean':
      return { ...base, background: 'var(--sa-brand-soft)', color: 'var(--sa-brand)' }
    case 'text':
      return { ...base, background: '#f1f5f9', color: 'var(--sa-muted)' }
    case 'number':
      return { ...base, background: 'var(--sa-ok-bg)', color: 'var(--sa-ok)' }
    case 'select':
      return { ...base, background: '#f5f3ff', color: '#7c3aed' }
    case 'date':
      return { ...base, background: 'var(--sa-warn-bg)', color: 'var(--sa-warn)' }
    default:
      return { ...base, background: '#f1f5f9', color: 'var(--sa-muted)' }
  }
})

// Answer label shown in compact row
const ansLabel = computed(() => {
  if (!props.answer) return ''
  if (props.field.field_type === 'boolean') {
    if (props.answer === 'true')  return 'Sim'
    if (props.answer === 'false') return 'Não'
    if (props.answer === 'na')    return 'N/A'
    return ''
  }
  return props.answer.length > 12 ? props.answer.slice(0, 12) + '…' : props.answer
})

// Status chip label + style
const statusLabel = computed(() => {
  if (props.conformityStatus === 'conforme')     return 'Conforme'
  if (props.conformityStatus === 'nao_conforme') return 'Não conf.'
  return 'Pendente'
})

const statusChipStyle = computed(() => {
  const base = {
    borderRadius: '99px',
    fontSize: '10px',
    fontWeight: '700',
    padding: '2px 8px',
    flexShrink: '0',
    whiteSpace: 'nowrap',
  }
  if (props.conformityStatus === 'conforme') {
    return { ...base, background: 'var(--sa-ok-bg)', color: 'var(--sa-ok)' }
  }
  if (props.conformityStatus === 'nao_conforme') {
    return { ...base, background: 'var(--sa-err-bg)', color: 'var(--sa-danger)' }
  }
  return { ...base, background: '#f1f5f9', color: 'var(--sa-muted)' }
})

// Select options (safe cast from config_json)
const selectOptions = computed<string[]>(() => {
  const opts = props.field.config_json?.options
  if (Array.isArray(opts)) return opts as string[]
  return []
})

// ── Event handlers ──────────────────────────────────────────────────────────

function onConforme() {
  emit('setConformity', 'conforme')
}

function onNaoConforme() {
  emit('setConformity', 'nao_conforme')
  emit('requestJustification')
}
</script>

<style scoped>
/* Compact row */
.ilr-row {
  display: flex;
  align-items: center;
  min-height: 52px;
  background: #fff;
  border-bottom: 1px solid var(--sa-line);
  cursor: pointer;
  user-select: none;
  gap: 10px;
  padding-right: 12px;
  transition: background .1s;
}
.ilr-row:hover  { background: #fafafa; }
.ilr-row:active { background: #f1f5f9; }

/* Left bar */
.ilr-bar {
  width: 3px;
  align-self: stretch;
  border-radius: 0 2px 2px 0;
  flex-shrink: 0;
}

/* Field label */
.ilr-label {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Expanded panel */
.ilr-panel {
  background: #f8fafc;
  border-top: 1px solid #bfdbfe;
  padding: 10px 14px 14px 14px;
}

/* Section separator label */
.ilr-sep-lbl {
  font-size: 9px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .1em;
  color: var(--sa-muted);
  margin: 10px 0 6px 0;
}

/* Generic input inside panel */
.ilr-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid var(--sa-line);
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  background: #fff;
  color: inherit;
}
.ilr-input:disabled {
  opacity: .5;
  cursor: not-allowed;
}

/* Bool buttons */
.ilr-bool-btn {
  padding: 7px 14px;
  border-radius: 8px;
  border: 1px solid var(--sa-line);
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  color: var(--sa-muted);
  cursor: pointer;
  font-family: inherit;
  transition: all .12s;
}
.ilr-bool-btn:disabled { opacity: .4; cursor: not-allowed; }
.ilr-bool-btn--sim.active { border-color: var(--sa-ok);     color: var(--sa-ok);     background: var(--sa-ok-bg); }
.ilr-bool-btn--nao.active { border-color: var(--sa-danger); color: var(--sa-danger); background: var(--sa-err-bg); }
.ilr-bool-btn--na.active  { border-color: var(--sa-warn);   color: var(--sa-warn);   background: var(--sa-warn-bg); }

/* Conformity buttons */
.ilr-conf-btn {
  padding: 9px;
  border-radius: 10px;
  border: 1px solid var(--sa-line);
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  color: var(--sa-muted);
  cursor: pointer;
  font-family: inherit;
  text-align: center;
  transition: all .12s;
}
.ilr-conf-btn:disabled { opacity: .4; cursor: not-allowed; }
.ilr-conf-ok.active  { border-color: var(--sa-ok);     background: var(--sa-ok-bg);  color: var(--sa-ok); }
.ilr-conf-err.active { border-color: var(--sa-danger); background: var(--sa-err-bg); color: var(--sa-danger); }

/* Evidence button */
.ilr-evid-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 12px;
  border: 1px solid var(--sa-line);
  border-radius: 8px;
  background: #fff;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
  font-family: inherit;
  transition: all .12s;
}
.ilr-evid-btn:hover { border-color: var(--sa-brand); color: var(--sa-brand); background: var(--sa-brand-soft); }

.ilr-evid-badge {
  background: var(--sa-brand);
  color: #fff;
  border-radius: 99px;
  padding: 0 5px;
  font-size: 10px;
  font-weight: 800;
  min-width: 16px;
  text-align: center;
}

/* Desktop adjustments */
@media (min-width: 768px) {
  .ilr-row   { min-height: 44px; }
  .ilr-panel { padding-left: 46px; }
}
</style>
