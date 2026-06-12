<!--
  AttributeValueEditor.vue
  ──────────────────────────────────────────────────────────────────────────
  Substitui o textarea de attributes_json (JSON manual) em AssetsView.
  Renderiza campos dinâmicos a partir do schema do Tipo de Ativo selecionado.

  USO:
    <AttributeValueEditor
      v-model="form.attributesJson"
      :schema="selectedTypeSchema"
    />

  COMPORTAMENTO:
    • Se schema != null: renderiza um campo por atributo definido no tipo.
    • Se schema == null: exibe mensagem informativa (sem campos a preencher).
    • Quando o schema muda (usuário troca o tipo), os valores locais são resetados
      e o pai deve também resetar form.attributesJson = {}.

  FORMATO:
    modelValue: Record<string, unknown>  — valores dos atributos (ex: { placa: 'ABC-1234' })
    schema:     Record<string, unknown> | null — schema do tipo (produzido pelo AttributeSchemaBuilder)
-->
<script setup lang="ts">
import { reactive, watch } from 'vue'

const props = defineProps<{
  modelValue: Record<string, unknown>
  schema: Record<string, unknown> | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown>]
}>()

// ── Tipos internos ─────────────────────────────────────────────────────────

interface FieldDef {
  type: string
  required?: boolean
}

// Normaliza uma entrada do schema (suporta formato antigo e novo)
function normalizeDef(raw: unknown): FieldDef {
  if (typeof raw === 'string') return { type: raw, required: false }
  if (typeof raw === 'object' && raw !== null) {
    const d = raw as { type?: string; required?: boolean }
    return { type: d.type ?? 'string', required: d.required ?? false }
  }
  return { type: 'string', required: false }
}

// Mapa de tipo do schema → tipo de <input>
const INPUT_TYPE: Record<string, string> = {
  string: 'text',
  number: 'number',
  date: 'date',
  boolean: 'checkbox',
  select: 'text', // sem opções nesta fase; torna-se select quando config_options for impl.
}

// ── Estado local ───────────────────────────────────────────────────────────

// Valores editáveis (string); convertemos ao emitir se necessário.
const values = reactive<Record<string, string>>({})

// Sincroniza modelValue → values (quando o pai reseta ou edita)
watch(
  () => props.modelValue,
  (incoming) => {
    // Aplica apenas chaves que diferem para não sobrescrever digitação em curso
    for (const [k, v] of Object.entries(incoming)) {
      const asStr = String(v ?? '')
      if (values[k] !== asStr) values[k] = asStr
    }
  },
  { immediate: true, deep: true },
)

// Quando o schema muda (usuário troca tipo de ativo), limpa os valores
watch(
  () => props.schema,
  () => {
    // Limpa tudo; o pai também deve fazer form.attributesJson = {}
    for (const key of Object.keys(values)) {
      delete values[key]
    }
  },
)

// ── Emissão ────────────────────────────────────────────────────────────────

function onInput(key: string, value: string, type: string) {
  values[key] = value
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(values)) {
    if (v === '') continue
    // Converte para o tipo correto
    if (type === 'number') {
      const n = Number(v)
      if (!isNaN(n)) out[k] = n
    } else {
      out[k] = v
    }
  }
  emit('update:modelValue', out)
}

// Expõe lista de campos calculada (para o template)
function schemaFields(): Array<{ key: string; def: FieldDef }> {
  if (!props.schema) return []
  return Object.entries(props.schema).map(([key, raw]) => ({
    key,
    def: normalizeDef(raw),
  }))
}
</script>

<template>
  <!-- Modo schema: campos definidos pelo tipo de ativo -->
  <template v-if="schema && schemaFields().length > 0">
    <div v-for="{ key, def } in schemaFields()" :key="key" class="field">
      <span class="flabel">
        {{ key }}
        <span v-if="def.required" style="color: var(--sa-danger, #ef4444)"> *</span>
        <span class="ave-type-hint">({{ def.type }})</span>
      </span>

      <!-- Checkbox para boolean -->
      <label v-if="def.type === 'boolean'" class="ave-bool">
        <input
          type="checkbox"
          :checked="values[key] === 'true'"
          @change="
            onInput(key, ($event.target as HTMLInputElement).checked ? 'true' : 'false', 'boolean')
          "
        />
        <span>{{ values[key] === 'true' ? 'Sim' : 'Não' }}</span>
      </label>

      <!-- Demais tipos -->
      <input
        v-else
        :type="INPUT_TYPE[def.type] ?? 'text'"
        :value="values[key] ?? ''"
        :required="def.required"
        :placeholder="def.type === 'number' ? '0' : def.type === 'date' ? 'aaaa-mm-dd' : ''"
        @input="onInput(key, ($event.target as HTMLInputElement).value, def.type)"
      />
    </div>
  </template>

  <!-- Schema existe mas sem campos: improvável, mas defensivo -->
  <template v-else-if="schema && schemaFields().length === 0">
    <p class="ave-hint">O tipo selecionado não possui atributos definidos.</p>
  </template>

  <!-- Sem schema: tipo não tem schema ou usa formato antigo -->
  <template v-else>
    <p class="ave-hint">
      O tipo selecionado não possui schema de atributos. Os atributos livres foram removidos nesta
      versão — defina atributos no <strong>Tipo de Ativo</strong> para habilitar este campo.
    </p>
  </template>
</template>

<style scoped>
.ave-type-hint {
  font-size: 10px;
  color: var(--sa-muted, #6b7280);
  font-weight: 400;
  margin-left: 4px;
}

.ave-bool {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 0;
}

.ave-bool input[type='checkbox'] {
  width: 16px;
  height: 16px;
  accent-color: var(--sa-primary, #2563eb);
  cursor: pointer;
}

.ave-hint {
  font-size: 12px;
  color: var(--sa-muted, #6b7280);
  line-height: 1.55;
  padding: 8px 10px;
  background: var(--sa-surface, #f9fafb);
  border: 1px dashed var(--sa-border, #e5e7eb);
  border-radius: 6px;
}

.ave-hint strong {
  color: var(--sa-text, #111827);
}
</style>
