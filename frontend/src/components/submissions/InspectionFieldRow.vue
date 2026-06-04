<script setup lang="ts">
import type { AttachmentItem } from '@/types/attachments'
import type { FormField } from '@/types/forms'

const props = defineProps<{
  field: FormField
  answer: string
  conformityStatus: 'conforme' | 'nao_conforme' | undefined
  conformityJustification: string
  isCompleted: boolean
  isPendingRequired: boolean
  evidenceAttachments: AttachmentItem[]
  evidenceUploading: boolean
  evidenceError: string | undefined
  compact?: boolean
}>()

defineEmits<{
  updateAnswer: [value: string]
  setConformity: [status: 'conforme' | 'nao_conforme']
  updateJustification: [value: string]
  uploadEvidence: [event: Event]
  deleteEvidence: [attachmentId: string]
}>()

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não', text: 'Texto', number: 'Número', date: 'Data', select: 'Seleção',
}

const ALLOWED_MIMES = 'image/jpeg,image/png,image/webp,video/mp4,video/quicktime,video/x-msvideo,audio/mpeg,audio/wav,audio/ogg,audio/mp4,application/pdf'

function selectOptions(): string[] {
  return Array.isArray(props.field.config_json.options)
    ? (props.field.config_json.options as string[])
    : []
}

function mimeCategory(mimeType: string): 'image' | 'pdf' | 'file' {
  if (mimeType.startsWith('image/')) return 'image'
  if (mimeType === 'application/pdf') return 'pdf'
  return 'file'
}

function fieldWeight(): number {
  return Number(props.field.config_json?.weight) || 0
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
</script>

<template>
  <div class="frow" :class="{ 'frow-error': isPendingRequired }">

    <!-- Header -->
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
      <div>
        <div class="frow-type">{{ TYPE_LABEL[field.field_type] ?? field.field_type }}</div>
        <div class="frow-name">{{ field.label }}</div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
        <span v-if="fieldWeight() > 1" style="font-size:9px;font-weight:700;padding:1px 5px;border-radius:3px;background:var(--sa-brand-soft);color:var(--sa-brand);">
          Peso {{ field.config_json.weight }}x
        </span>
        <span v-if="field.required" class="status-chip status-chip--neu" style="font-size:9px;">Obrigatório</span>
      </div>
    </div>

    <!-- Pending error label -->
    <div v-if="isPendingRequired" class="frow-error-label">Campo obrigatório não preenchido</div>

    <!-- Instruction -->
    <div v-if="field.instruction"
      style="font-size:12px;color:var(--sa-muted);background:var(--sa-bg);border-left:3px solid var(--sa-brand);padding:6px 9px;border-radius:0 6px 6px 0;margin-bottom:8px;line-height:1.5;">
      {{ field.instruction }}
    </div>

    <!-- ── Answer input ── -->
    <div v-if="field.field_type === 'boolean'" style="display:flex;gap:6px;flex-wrap:wrap;">
      <button type="button" class="bool-btn-sm bool-sim"
        :class="{ 'bool-btn--active': answer === 'true' }"
        :disabled="isCompleted"
        @click="$emit('updateAnswer', 'true')">✓ Sim</button>
      <button type="button" class="bool-btn-sm bool-nao"
        :class="{ 'bool-btn--active': answer === 'false' }"
        :disabled="isCompleted"
        @click="$emit('updateAnswer', 'false')">✕ Não</button>
      <button v-if="field.config_json?.allow_na"
        type="button" class="bool-btn-sm bool-na"
        :class="{ 'bool-btn--active': answer === 'na' }"
        :disabled="isCompleted"
        @click="$emit('updateAnswer', 'na')">N/A</button>
    </div>

    <input v-else-if="field.field_type === 'number'"
      :value="answer" type="number" step="any" placeholder="Informe um número"
      :disabled="isCompleted"
      @change="$emit('updateAnswer', ($event.target as HTMLInputElement).value)" />

    <input v-else-if="field.field_type === 'date'"
      :value="answer" type="date"
      :disabled="isCompleted"
      @change="$emit('updateAnswer', ($event.target as HTMLInputElement).value)" />

    <template v-else-if="field.field_type === 'select'">
      <select v-if="selectOptions().length"
        :value="answer" :disabled="isCompleted"
        @change="$emit('updateAnswer', ($event.target as HTMLSelectElement).value)">
        <option value="">— Selecione —</option>
        <option v-for="opt in selectOptions()" :key="opt" :value="opt">{{ opt }}</option>
      </select>
      <input v-else :value="answer" type="text" :disabled="isCompleted"
        @change="$emit('updateAnswer', ($event.target as HTMLInputElement).value)" />
    </template>

    <input v-else
      :value="answer" type="text" placeholder="Informe o valor"
      :disabled="isCompleted"
      @input="$emit('updateAnswer', ($event.target as HTMLInputElement).value)" />

    <!-- ── Conformity ── -->
    <div :style="compact
      ? 'margin-top:8px;padding-top:6px;border-top:1px solid var(--sa-line);'
      : 'margin-top:10px;padding-top:8px;border-top:1px solid var(--sa-line);'">
      <div style="display:flex;gap:5px;flex-wrap:wrap;align-items:center;">
        <span style="font-size:10px;font-weight:700;color:var(--sa-muted);text-transform:uppercase;letter-spacing:.04em;margin-right:2px;">Conformidade:</span>
        <button type="button" class="bool-btn-sm bool-sim"
          :class="{ 'bool-btn--active': conformityStatus === 'conforme' }"
          :disabled="isCompleted"
          @click="$emit('setConformity', 'conforme')">✓ Conforme</button>
        <button type="button" class="bool-btn-sm bool-nao"
          :class="{ 'bool-btn--active': conformityStatus === 'nao_conforme' }"
          :disabled="isCompleted"
          @click="$emit('setConformity', 'nao_conforme')">✕ Não conforme</button>
      </div>
      <textarea v-if="conformityStatus === 'nao_conforme'"
        :value="conformityJustification"
        placeholder="Justificativa obrigatória"
        rows="2"
        :disabled="isCompleted"
        :style="compact
          ? 'width:100%;margin-top:6px;font-size:12px;padding:5px 7px;border-radius:6px;border:1px solid var(--sa-danger);resize:vertical;box-sizing:border-box;'
          : 'width:100%;margin-top:8px;font-size:12px;padding:6px 8px;border-radius:6px;border:1px solid var(--sa-danger);resize:vertical;box-sizing:border-box;'"
        @input="$emit('updateJustification', ($event.target as HTMLTextAreaElement).value)"
      ></textarea>
      <!-- Justification text (completed, full mode only) -->
      <div v-if="!compact && isCompleted && conformityStatus === 'nao_conforme' && conformityJustification"
        style="margin-top:8px;font-size:12px;color:var(--sa-muted);background:var(--sa-err-bg);border-radius:6px;padding:6px 10px;">
        {{ conformityJustification }}
      </div>
    </div>

    <!-- ── Evidence: compact (inspection list) ── -->
    <div v-if="compact && (!isCompleted || evidenceAttachments.length > 0)"
      style="margin-top:8px;display:flex;flex-wrap:wrap;align-items:center;gap:4px;">
      <div v-for="att in evidenceAttachments" :key="att.id"
        style="display:inline-flex;align-items:center;gap:4px;padding:3px 7px;background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:6px;font-size:11px;max-width:150px;">
        <a :href="att.file_url" target="_blank" rel="noopener"
          style="display:inline-flex;align-items:center;gap:4px;text-decoration:none;min-width:0;">
          <img v-if="mimeCategory(att.mime_type) === 'image'" :src="att.file_url"
            style="width:16px;height:16px;object-fit:cover;border-radius:2px;flex-shrink:0;" />
          <span v-else style="font-size:11px;flex-shrink:0;">📄</span>
          <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--sa-text);">
            {{ att.file_url.split('/').pop() }}
          </span>
        </a>
        <button v-if="!isCompleted" type="button"
          style="border:none;background:none;cursor:pointer;color:var(--sa-danger);font-size:13px;padding:0;line-height:1;flex-shrink:0;"
          @click="$emit('deleteEvidence', att.id)">×</button>
      </div>
      <label v-if="!isCompleted"
        style="display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:600;color:var(--sa-brand);cursor:pointer;padding:3px 7px;border:1px dashed var(--sa-brand);border-radius:6px;">
        {{ evidenceUploading ? '…' : '📎' }}
        <input type="file" :accept="ALLOWED_MIMES" style="display:none;"
          :disabled="evidenceUploading" @change="$emit('uploadEvidence', $event)" />
      </label>
      <span v-if="evidenceError" style="font-size:11px;color:var(--sa-danger);">{{ evidenceError }}</span>
    </div>

    <!-- ── Evidence: full (normal list) ── -->
    <div v-else-if="!compact && (!isCompleted || evidenceAttachments.length > 0)" style="margin-top:10px;">
      <div v-if="evidenceAttachments.length" style="display:grid;gap:6px;margin-bottom:8px;">
        <div v-for="att in evidenceAttachments" :key="att.id"
          style="display:flex;align-items:center;gap:8px;background:var(--sa-bg);border:1px solid var(--sa-line);border-radius:8px;padding:8px 10px;overflow:hidden;">
          <a :href="att.file_url" target="_blank" rel="noopener"
            style="flex:1;min-width:0;display:flex;align-items:center;gap:8px;text-decoration:none;">
            <img v-if="mimeCategory(att.mime_type) === 'image'" :src="att.file_url" alt=""
              style="width:40px;height:40px;object-fit:cover;border-radius:4px;flex-shrink:0;" />
            <div v-else
              style="width:40px;height:40px;border-radius:4px;flex-shrink:0;background:var(--sa-brand-soft);display:flex;align-items:center;justify-content:center;font-size:18px;">📄</div>
            <div style="flex:1;min-width:0;">
              <div style="font-size:12px;font-weight:600;color:var(--sa-text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                {{ att.file_url.split('/').pop() }}
              </div>
              <div style="font-size:11px;color:var(--sa-muted);margin-top:2px;">{{ formatFileSize(att.file_size) }}</div>
            </div>
          </a>
          <button v-if="!isCompleted" type="button" title="Remover"
            style="border:none;background:none;cursor:pointer;color:var(--sa-danger);font-size:18px;line-height:1;padding:0 4px;flex-shrink:0;"
            @click="$emit('deleteEvidence', att.id)">×</button>
        </div>
      </div>
      <template v-if="!isCompleted">
        <label style="cursor:pointer;display:inline-block;">
          <span class="inline-action">{{ evidenceUploading ? 'Enviando…' : '📎 Adicionar evidência' }}</span>
          <input type="file" :accept="ALLOWED_MIMES" style="display:none;"
            :disabled="evidenceUploading" @change="$emit('uploadEvidence', $event)" />
        </label>
      </template>
      <p v-if="evidenceError" style="font-size:12px;font-weight:600;color:var(--sa-danger);margin-top:6px;">
        {{ evidenceError }}
      </p>
    </div>

  </div>
</template>

<style scoped>
.bool-btn-sm {
  padding: 6px 14px;
  border-radius: 8px;
  border: 1px solid var(--sa-line);
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  color: var(--sa-muted);
  cursor: pointer;
  transition: border-color .15s, background .15s, color .15s;
}
.bool-btn-sm:disabled { opacity: .45; cursor: not-allowed; }
.bool-btn-sm.bool-sim.bool-btn--active { border-color: var(--sa-ok); color: var(--sa-ok); background: var(--sa-ok-bg); }
.bool-btn-sm.bool-nao.bool-btn--active { border-color: var(--sa-danger); color: var(--sa-danger); background: var(--sa-err-bg); }
.bool-btn-sm.bool-na.bool-btn--active  { border-color: var(--sa-warn); color: var(--sa-warn); background: var(--sa-warn-bg); }
</style>
