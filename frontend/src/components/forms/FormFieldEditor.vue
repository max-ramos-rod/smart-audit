<script setup lang="ts">
import type { FieldType, FormFieldCreatePayload } from '@/types/forms'

const field = defineModel<FormFieldCreatePayload>({ required: true })

const props = defineProps<{
  index: number
  otherFields: FormFieldCreatePayload[]
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
  const vi = (field.value.config_json as Config).visible_if
  if (ft === 'section') {
    field.value = { ...field.value, field_type: ft, config_json: {}, required: false }
  } else {
    field.value = { ...field.value, field_type: ft, config_json: vi ? { visible_if: vi } : {} }
  }
}

function getOptionsString(): string {
  const opts = (field.value.config_json as Config).options
  return Array.isArray(opts) ? (opts as string[]).join(', ') : ''
}

function setOptionsFromString(event: Event) {
  const opts = (event.target as HTMLInputElement).value
    .split(',').map(o => o.trim()).filter(Boolean)
  const vi = (field.value.config_json as Config).visible_if
  const base: Config = opts.length ? { options: opts } : {}
  set({ config_json: vi ? { ...base, visible_if: vi } : base })
}

function visibleIf(): Config | undefined {
  return (field.value.config_json as Config).visible_if as Config | undefined
}

function visibleIfProp(prop: string): string {
  const vi = visibleIf()
  return vi ? String(vi[prop] ?? '') : ''
}

function setVisibleIfProp(prop: string, value: string) {
  setConfig({ visible_if: { ...(visibleIf() ?? {}), [prop]: value } })
}

function clearVisibleIf() {
  const { visible_if: _vi, ...rest } = field.value.config_json as Config
  set({ config_json: rest })
}

function triggerField(): FormFieldCreatePayload | undefined {
  const key = visibleIfProp('field_key')
  return key ? props.otherFields.find(f => f.key === key) : undefined
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

      <!-- Visibilidade condicional -->
      <div v-if="field.field_type !== 'section'" style="grid-column:1/-1;border-top:1px solid var(--sa-line);padding-top:10px;margin-top:2px;">
        <div style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.08em;color:var(--sa-muted);margin-bottom:8px;">
          Visibilidade condicional
        </div>

        <div v-if="!visibleIf()">
          <button
            type="button"
            class="btn-secondary btn-sm"
            @click="setConfig({ visible_if: { field_key: '', operator: 'eq', value: 'true' } })"
          >
            + Adicionar condição
          </button>
        </div>

        <div v-else style="display:grid;grid-template-columns:1fr 160px 1fr auto;gap:8px;align-items:end;">
          <label style="display:grid;gap:4px;">
            <span style="font-size:11px;color:var(--sa-muted);">Exibir se o campo</span>
            <select
              :value="visibleIfProp('field_key')"
              @change="setVisibleIfProp('field_key', ($event.target as HTMLSelectElement).value)"
            >
              <option value="">— selecione —</option>
              <option v-for="f in otherFields" :key="f.key" :value="f.key">{{ f.label || f.key }}</option>
            </select>
          </label>

          <label style="display:grid;gap:4px;">
            <span style="font-size:11px;color:var(--sa-muted);">Operador</span>
            <select
              :value="visibleIfProp('operator')"
              @change="setVisibleIfProp('operator', ($event.target as HTMLSelectElement).value)"
            >
              <option value="eq">é igual a</option>
              <option value="neq">é diferente de</option>
            </select>
          </label>

          <label style="display:grid;gap:4px;">
            <span style="font-size:11px;color:var(--sa-muted);">Valor</span>
            <select
              v-if="triggerField()?.field_type === 'boolean'"
              :value="visibleIfProp('value')"
              @change="setVisibleIfProp('value', ($event.target as HTMLSelectElement).value)"
            >
              <option value="true">Sim</option>
              <option value="false">Não</option>
              <option value="na">N/A</option>
            </select>
            <select
              v-else-if="triggerField()?.field_type === 'select'"
              :value="visibleIfProp('value')"
              @change="setVisibleIfProp('value', ($event.target as HTMLSelectElement).value)"
            >
              <option value="">— selecione —</option>
              <option
                v-for="opt in (triggerField()?.config_json?.options as string[] ?? [])"
                :key="opt"
                :value="opt"
              >
                {{ opt }}
              </option>
            </select>
            <input
              v-else
              :value="visibleIfProp('value')"
              type="text"
              placeholder="valor esperado"
              @input="setVisibleIfProp('value', ($event.target as HTMLInputElement).value)"
            />
          </label>

          <button
            type="button"
            class="btn-secondary btn-sm"
            style="align-self:end;"
            title="Remover condição"
            @click="clearVisibleIf()"
          >
            ✕
          </button>
        </div>
      </div>

    </div>
  </div>
</template>
