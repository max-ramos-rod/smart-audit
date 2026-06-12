<!--
  AttributeSchemaBuilder.vue
  ──────────────────────────────────────────────────────────────────────────
  Substitui o textarea de attributes_schema (JSON manual) em AssetTypesView.
  Constrói visualmente um Record<string, { type, required }> sem expor JSON.

  USO:
    <AttributeSchemaBuilder
      :key="form.id || 'new'"
      v-model="form.schema"
    />

  O :key garante que ao trocar de tipo (edição) ou resetar o form,
  o componente remonta e inicializa com o novo modelValue — sem watchers.

  FORMATO EMITIDO:
    null → nenhum atributo definido
    { placa: { type: 'string', required: true }, ano: { type: 'number', required: false } }

  FORMATO LIDO (retrocompatível):
    Novo: { placa: { type: 'string', required: true } }
    Antigo (M1): { placa: 'string' }  ← normalizado automaticamente
-->
<script setup lang="ts">
import { reactive } from 'vue'

const props = defineProps<{
  modelValue: Record<string, unknown> | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: Record<string, unknown> | null]
}>()

// ── Tipos internos ─────────────────────────────────────────────────────────

type FieldType = 'string' | 'number' | 'date' | 'boolean' | 'select'

interface AttrRow {
  key: string
  type: FieldType
  required: boolean
}

const TYPE_LABELS: Record<FieldType, string> = {
  string: 'Texto',
  number: 'Número',
  date: 'Data',
  boolean: 'Sim/Não',
  select: 'Seleção',
}

// ── Estado interno ─────────────────────────────────────────────────────────

const rows = reactive<AttrRow[]>([])

// Inicializa a partir do modelValue (chamado uma vez no setup).
// O pai controla re-inicialização via :key.
function parseIncoming(val: Record<string, unknown> | null) {
  rows.length = 0
  if (!val) return
  for (const [key, def] of Object.entries(val)) {
    if (typeof def === 'string') {
      // Formato antigo (M1): { placa: 'string' }
      rows.push({ key, type: (def as FieldType) || 'string', required: false })
    } else if (typeof def === 'object' && def !== null) {
      // Formato novo: { placa: { type: 'string', required: true } }
      const d = def as { type?: string; required?: boolean }
      rows.push({
        key,
        type: (d.type ?? 'string') as FieldType,
        required: d.required ?? false,
      })
    }
  }
}

parseIncoming(props.modelValue)

// ── Emissão ────────────────────────────────────────────────────────────────

function emitUpdate() {
  const schema: Record<string, unknown> = {}
  for (const row of rows) {
    const k = row.key.trim()
    if (!k) continue
    schema[k] = { type: row.type, required: row.required }
  }
  emit('update:modelValue', Object.keys(schema).length ? schema : null)
}

// ── Ações ──────────────────────────────────────────────────────────────────

function addRow() {
  rows.push({ key: '', type: 'string', required: false })
  // Não emitimos ainda — chave ainda está vazia; emitiremos quando o usuário preencher.
}

function removeRow(index: number) {
  rows.splice(index, 1)
  emitUpdate()
}
</script>

<template>
  <div class="asb">
    <!-- Cabeçalho da tabela -->
    <div v-if="rows.length > 0" class="asb-head">
      <span>Nome do atributo</span>
      <span>Tipo</span>
      <span>Obrigatório</span>
      <span></span>
    </div>

    <!-- Linhas de atributos -->
    <div v-for="(row, i) in rows" :key="i" class="asb-row">
      <input
        v-model="row.key"
        class="asb-input"
        type="text"
        placeholder="Ex: placa, ano, cor…"
        @input="emitUpdate"
      />
      <select v-model="row.type" class="asb-select" @change="emitUpdate">
        <option v-for="(label, val) in TYPE_LABELS" :key="val" :value="val">{{ label }}</option>
      </select>
      <div class="asb-toggle-wrap">
        <button
          type="button"
          class="asb-toggle"
          :class="{ 'asb-toggle--on': row.required }"
          :aria-label="row.required ? 'Obrigatório' : 'Opcional'"
          @click="
            () => {
              row.required = !row.required
              emitUpdate()
            }
          "
        >
          <span class="asb-toggle-thumb"></span>
        </button>
        <span class="asb-toggle-lbl">{{ row.required ? 'Sim' : 'Não' }}</span>
      </div>
      <button type="button" class="asb-rm" aria-label="Remover atributo" @click="removeRow(i)">
        ×
      </button>
    </div>

    <!-- Estado vazio -->
    <p v-if="rows.length === 0" class="asb-empty">
      Nenhum atributo definido — clique em "+ Adicionar" para começar.
    </p>

    <button type="button" class="asb-add" @click="addRow">+ Adicionar atributo</button>
  </div>
</template>

<style scoped>
.asb {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* Cabeçalho */
.asb-head {
  display: grid;
  grid-template-columns: 1fr 108px 92px 28px;
  gap: 6px;
  padding: 0 0 5px;
  border-bottom: 2px solid var(--sa-border, #e5e7eb);
  font-size: 10px;
  font-weight: 700;
  color: var(--sa-muted, #6b7280);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

/* Linha de atributo */
.asb-row {
  display: grid;
  grid-template-columns: 1fr 108px 92px 28px;
  gap: 6px;
  align-items: center;
  padding: 5px 0;
  border-bottom: 1px solid #f3f4f6;
}

/* Input e select */
.asb-input,
.asb-select {
  height: 30px;
  border: 1px solid var(--sa-border, #e5e7eb);
  border-radius: 6px;
  padding: 0 8px;
  font-size: 12px;
  font-family: inherit;
  color: var(--sa-text, #111827);
  background: #fff;
  width: 100%;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.asb-input:focus,
.asb-select:focus {
  outline: none;
  border-color: var(--sa-primary, #2563eb);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.asb-select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='%236b7280'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 7px center;
  padding-right: 22px;
  cursor: pointer;
}

/* Toggle obrigatório */
.asb-toggle-wrap {
  display: flex;
  align-items: center;
  gap: 5px;
}

.asb-toggle {
  width: 28px;
  height: 16px;
  background: #d1d5db;
  border: none;
  border-radius: 100px;
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.2s;
  padding: 0;
}

.asb-toggle--on {
  background: var(--sa-primary, #2563eb);
}

.asb-toggle-thumb {
  position: absolute;
  width: 12px;
  height: 12px;
  background: #fff;
  border-radius: 50%;
  top: 2px;
  left: 2px;
  transition: transform 0.2s;
  display: block;
  pointer-events: none;
}

.asb-toggle--on .asb-toggle-thumb {
  transform: translateX(12px);
}

.asb-toggle-lbl {
  font-size: 11px;
  color: var(--sa-muted, #6b7280);
  min-width: 20px;
}

/* Botão remover */
.asb-rm {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--sa-border, #e5e7eb);
  border-radius: 5px;
  background: #fff;
  cursor: pointer;
  font-size: 15px;
  line-height: 1;
  color: var(--sa-danger, #ef4444);
  transition: background 0.15s;
  flex-shrink: 0;
}

.asb-rm:hover {
  background: #fef2f2;
}

/* Estado vazio */
.asb-empty {
  font-size: 12px;
  color: var(--sa-muted, #6b7280);
  padding: 10px;
  text-align: center;
  border: 1px dashed var(--sa-border, #e5e7eb);
  border-radius: 6px;
  margin-bottom: 2px;
}

/* Botão adicionar */
.asb-add {
  margin-top: 6px;
  padding: 5px 10px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  background: var(--sa-surface, #f9fafb);
  border: 1px solid var(--sa-border, #e5e7eb);
  border-radius: 6px;
  color: var(--sa-text, #111827);
  cursor: pointer;
  align-self: flex-start;
  transition: background 0.15s;
}

.asb-add:hover {
  background: var(--sa-border, #e5e7eb);
}
</style>
