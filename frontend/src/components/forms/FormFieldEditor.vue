<script setup lang="ts">
import type { FieldType, FormFieldCreatePayload } from '@/types/forms'

const field = defineModel<FormFieldCreatePayload>({ required: true })

const props = defineProps<{
  index: number
  showRemove: boolean
  mode?: 'inline' | 'full'
}>()

const emit = defineEmits<{ remove: [], updateKey: [key: string] }>()

type Config = Record<string, unknown>

function set(patch: Partial<FormFieldCreatePayload>) {
  field.value = { ...field.value, ...patch }
}

function setConfig(patch: Config) {
  set({ config_json: { ...(field.value.config_json as Config), ...patch } })
}

function onTypeChange(event: Event) {
  const ft = (event.target as HTMLSelectElement).value as FieldType
  if (ft === 'section') {
    field.value = { ...field.value, field_type: ft, config_json: {}, required: false }
  } else {
    field.value = { ...field.value, field_type: ft, config_json: {} }
  }
}

function getOptionsString(): string {
  const opts = (field.value.config_json as Config).options
  return Array.isArray(opts) ? (opts as string[]).join(', ') : ''
}

function setOptionsFromString(event: Event) {
  const opts = (event.target as HTMLInputElement).value
    .split(',').map(o => o.trim()).filter(Boolean)
  set({ config_json: opts.length ? { options: opts } : {} })
}

function slugify(str: string): string {
  return str.toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_|_$/g, '')
    .slice(0, 64)
}

function onLabelBlur(e: FocusEvent) {
  const lbl = (e.target as HTMLInputElement).value
  const currentKey = field.value.key ?? ''
  if (!currentKey || /^campo_\d+$/.test(currentKey)) {
    const newKey = slugify(lbl)
    if (newKey) {
      set({ key: newKey })
      emit('updateKey', newKey)
    }
  }
}
</script>

<template>
  <!-- ── FULL mode (default — comportamento original preservado) ── -->
  <div v-if="!props.mode || props.mode === 'full'" class="card card-p">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
      <span style="font-size:11px;font-weight:700;color:var(--sa-muted);text-transform:uppercase;letter-spacing:.08em;">
        Campo {{ index + 1 }}
      </span>
      <button v-if="showRemove" type="button" class="btn-secondary btn-sm" @click="$emit('remove')">
        Remover
      </button>
    </div>

    <div style="display:grid;gap:10px;grid-template-columns:1fr 1fr;">

      <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;">
        <span>Chave</span>
        <input
          :value="field.key"
          type="text"
          required
          @input="set({ key: ($event.target as HTMLInputElement).value })"
        />
      </label>

      <label :style="field.field_type === 'section' ? 'display:grid;gap:6px;grid-column:1/-1;' : 'display:grid;gap:6px;'">
        <span>{{ field.field_type === 'section' ? 'Título da seção' : 'Label' }}</span>
        <input
          :value="field.label"
          type="text"
          required
          @input="set({ label: ($event.target as HTMLInputElement).value })"
          @blur="field.field_type !== 'section' && onLabelBlur($event)"
        />
      </label>

      <label style="display:grid;gap:6px;">
        <span>Tipo</span>
        <select :value="field.field_type" @change="onTypeChange($event)">
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
        <select
          :value="String(field.required)"
          @change="set({ required: ($event.target as HTMLSelectElement).value === 'true' })"
        >
          <option value="true">Sim</option>
          <option value="false">Não</option>
        </select>
      </label>

      <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
        <span>Peso</span>
        <input
          :value="(field.config_json as Record<string, unknown>).weight ?? 1"
          type="number" min="0.1" step="0.1"
          @input="setConfig({ weight: parseFloat(($event.target as HTMLInputElement).value) || 1 })"
        />
      </label>

      <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
        <span>Permite N/A</span>
        <select
          :value="(field.config_json as Record<string, unknown>).allow_na ? 'true' : 'false'"
          @change="setConfig({ allow_na: ($event.target as HTMLSelectElement).value === 'true' })"
        >
          <option value="false">Não</option>
          <option value="true">Sim</option>
        </select>
      </label>

      <label v-if="field.field_type === 'select'" style="display:grid;gap:6px;grid-column:1/-1;">
        <span>Opções (separadas por vírgula)</span>
        <input
          :value="getOptionsString()"
          type="text"
          placeholder="Ex: Conforme, Não conforme, Parcial"
          @input="setOptionsFromString($event)"
        />
      </label>

      <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;grid-column:1/-1;">
        <span>
          Instrução
          <span style="font-weight:400;color:var(--sa-muted);">(opcional — aparece na tela de inspeção)</span>
        </span>
        <textarea
          :value="field.instruction ?? ''"
          rows="2"
          style="resize:vertical;"
          placeholder="Ex: Verifique a validade do extintor e o lacre de segurança."
          @input="set({ instruction: ($event.target as HTMLTextAreaElement).value || null })"
        />
      </label>

    </div>
  </div>

  <!-- ── INLINE mode (painel compacto dentro da linha de campo) ── -->
  <div v-else-if="props.mode === 'inline'" class="ffe-inline">

    <!-- Cabeçalho -->
    <div class="ffe-inline-hdr">
      <span class="ffe-inline-type">
        {{ field.field_type.toUpperCase() }} · campo {{ String(index + 1).padStart(2, '0') }}
      </span>
      <div style="display:flex;gap:6px;">
        <button
          v-if="showRemove"
          type="button"
          class="ffe-btn-ghost"
          @click="$emit('remove')"
        >Remover</button>
      </div>
    </div>

    <!-- Grade responsiva -->
    <div class="ffe-grid">

      <!-- Label (span 2 cols) -->
      <label class="ffe-field ffe-span2">
        <span class="ffe-lbl">{{ field.field_type === 'section' ? 'Título da seção' : 'Label' }}</span>
        <input
          class="finput"
          :value="field.label"
          type="text"
          @input="set({ label: ($event.target as HTMLInputElement).value })"
          @blur="field.field_type !== 'section' ? onLabelBlur($event) : undefined"
        />
      </label>

      <!-- Tipo -->
      <label class="ffe-field">
        <span class="ffe-lbl">Tipo</span>
        <select class="fselect" :value="field.field_type" @change="onTypeChange($event)">
          <option value="boolean">Sim / Não</option>
          <option value="text">Texto</option>
          <option value="number">Número</option>
          <option value="select">Seleção</option>
          <option value="date">Data</option>
          <option value="section">── Seção ──</option>
        </select>
      </label>

      <!-- Chave (DM Mono) -->
      <label v-if="field.field_type !== 'section'" class="ffe-field">
        <span class="ffe-lbl">Chave</span>
        <input
          class="finput finput--mono"
          :value="field.key"
          type="text"
          @input="set({ key: ($event.target as HTMLInputElement).value })"
        />
      </label>

      <!-- Obrigatório -->
      <label v-if="field.field_type !== 'section'" class="ffe-field">
        <span class="ffe-lbl">Obrigatório</span>
        <select
          class="fselect"
          :value="String(field.required)"
          @change="set({ required: ($event.target as HTMLSelectElement).value === 'true' })"
        >
          <option value="true">Sim</option>
          <option value="false">Não</option>
        </select>
      </label>

      <!-- Peso (boolean) -->
      <label v-if="field.field_type === 'boolean'" class="ffe-field">
        <span class="ffe-lbl">Peso no score</span>
        <input
          class="finput"
          :value="(field.config_json as Record<string, unknown>).weight ?? 1"
          type="number" min="0.1" step="0.5"
          @input="setConfig({ weight: parseFloat(($event.target as HTMLInputElement).value) || 1 })"
        />
      </label>

      <!-- Permite N/A (boolean) -->
      <label v-if="field.field_type === 'boolean'" class="ffe-field">
        <span class="ffe-lbl">Permite N/A</span>
        <select
          class="fselect"
          :value="(field.config_json as Record<string, unknown>).allow_na ? 'true' : 'false'"
          @change="setConfig({ allow_na: ($event.target as HTMLSelectElement).value === 'true' })"
        >
          <option value="false">Não</option>
          <option value="true">Sim</option>
        </select>
      </label>

      <!-- Opções (select) — full width -->
      <label v-if="field.field_type === 'select'" class="ffe-field ffe-span-all">
        <span class="ffe-lbl">Opções (separadas por vírgula)</span>
        <input
          class="finput"
          :value="getOptionsString()"
          type="text"
          placeholder="Ex: Conforme, Não conforme, Parcial"
          @input="setOptionsFromString($event)"
        />
      </label>

      <!-- Instrução — full width -->
      <label v-if="field.field_type !== 'section'" class="ffe-field ffe-span-all">
        <span class="ffe-lbl">
          Instrução para o inspetor
          <span style="font-weight:400;color:var(--sa-muted);">(opcional)</span>
        </span>
        <textarea
          class="ftarea"
          :value="field.instruction ?? ''"
          rows="2"
          placeholder="Ex: Verifique a validade do extintor e o lacre de segurança."
          @input="set({ instruction: ($event.target as HTMLTextAreaElement).value || null })"
        />
      </label>

    </div>
  </div>
</template>

<style scoped>
/* ── Inline mode ── */
.ffe-inline {
  background: #f8fafc;
  border-top: 2px solid var(--sa-brand-soft);
  padding: 12px 16px 16px;
}

.ffe-inline-hdr {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.ffe-inline-type {
  font-size: 11px;
  font-weight: 700;
  font-family: 'DM Mono', monospace;
  text-transform: uppercase;
  color: var(--sa-brand);
  letter-spacing: .06em;
}

.ffe-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

@media (min-width: 480px) {
  .ffe-grid { grid-template-columns: 1fr 1fr; }
}

@media (min-width: 768px) {
  .ffe-grid    { grid-template-columns: 1fr 1fr 1fr; }
  .ffe-inline  { padding-left: 88px; }
}

.ffe-field    { display: grid; gap: 5px; }
.ffe-span2    { grid-column: 1 / -1; }
.ffe-span-all { grid-column: 1 / -1; }

@media (min-width: 480px) {
  .ffe-span2 { grid-column: span 2; }
}

.ffe-lbl {
  font-size: 11px;
  font-weight: 600;
  color: var(--sa-muted);
}

.finput, .fselect, .ftarea {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid var(--sa-line);
  border-radius: 7px;
  font-size: 13px;
  font-family: inherit;
  color: var(--sa-text);
  background: #fff;
  outline: none;
  box-sizing: border-box;
}
.finput:focus, .fselect:focus, .ftarea:focus {
  border-color: var(--sa-brand);
  box-shadow: 0 0 0 3px rgba(37,99,235,.08);
}
.finput--mono { font-family: 'DM Mono', monospace; font-size: 12px; }
.ftarea { resize: vertical; min-height: 60px; }

.ffe-btn-ghost {
  background: none;
  border: 1px solid var(--sa-line);
  border-radius: 6px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--sa-muted);
  cursor: pointer;
  padding: 4px 10px;
  transition: all .12s;
}
.ffe-btn-ghost:hover { border-color: var(--sa-danger); color: var(--sa-danger); background: var(--sa-err-bg); }
</style>
