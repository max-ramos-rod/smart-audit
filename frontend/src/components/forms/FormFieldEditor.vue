<script setup lang="ts">
import type { FieldType, FormFieldCreatePayload } from '@/types/forms'

const field = defineModel<FormFieldCreatePayload>({ required: true })

const props = defineProps<{
  index: number
  showRemove: boolean
}>()

defineEmits<{ remove: [] }>()

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
</script>

<template>
  <div class="card card-p">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
      <span style="font-size:11px;font-weight:700;color:var(--sa-muted);text-transform:uppercase;letter-spacing:.08em;">
        Campo {{ index + 1 }}
      </span>
      <button v-if="showRemove" type="button" class="btn-secondary btn-sm" @click="$emit('remove')">
        Remover
      </button>
    </div>

    <div style="display:grid;gap:10px;grid-template-columns:1fr 1fr;">

      <!-- Chave -->
      <label v-if="field.field_type !== 'section'" style="display:grid;gap:6px;">
        <span>Chave</span>
        <input
          :value="field.key"
          type="text"
          required
          @input="set({ key: ($event.target as HTMLInputElement).value })"
        />
      </label>

      <!-- Label -->
      <label :style="field.field_type === 'section' ? 'display:grid;gap:6px;grid-column:1/-1;' : 'display:grid;gap:6px;'">
        <span>{{ field.field_type === 'section' ? 'Título da seção' : 'Label' }}</span>
        <input
          :value="field.label"
          type="text"
          required
          @input="set({ label: ($event.target as HTMLInputElement).value })"
        />
      </label>

      <!-- Tipo -->
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

      <!-- Obrigatório -->
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

      <!-- Peso (boolean) -->
      <label v-if="field.field_type === 'boolean'" style="display:grid;gap:6px;">
        <span>Peso</span>
        <input
          :value="(field.config_json as Record<string, unknown>).weight ?? 1"
          type="number" min="0.1" step="0.1"
          @input="setConfig({ weight: parseFloat(($event.target as HTMLInputElement).value) || 1 })"
        />
      </label>

      <!-- Permite N/A (boolean) -->
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

      <!-- Opções (select) -->
      <label v-if="field.field_type === 'select'" style="display:grid;gap:6px;grid-column:1/-1;">
        <span>Opções (separadas por vírgula)</span>
        <input
          :value="getOptionsString()"
          type="text"
          placeholder="Ex: Conforme, Não conforme, Parcial"
          @input="setOptionsFromString($event)"
        />
      </label>

      <!-- Instrução -->
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
</template>
