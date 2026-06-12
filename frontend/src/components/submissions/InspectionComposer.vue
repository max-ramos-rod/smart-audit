<!--
  InspectionComposer.vue
  ──────────────────────────────────────────────────────────────────────────
  Wizard de 3 passos extraído de SubmissionsView.
  Suporta pré-seleção de ativo ou cliente para fluxos contextuais.

  USO em ClientDetailView (ativo pré-selecionado):
    <InspectionComposer
      :preselected-asset-id="assetId"
      :preselected-asset-label="assetLabel"
      @created="onCreated"
      @close="showComposer = false"
    />

  USO em SubmissionsView (sem pré-seleção):
    <InspectionComposer
      @created="onCreated"
      @close="showComposer = false"
    />

  PASSOS ATIVOS:
    preselectedAssetId  → ['form']               (só escolhe o formulário)
    preselectedClientId → ['form', 'asset']       (pula a seleção de cliente)
    sem pré-seleção     → ['form', 'client', 'asset']
-->
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { extractProblemMessage } from '@/services/api/problem'
import { fetchAssets } from '@/services/assets.service'
import { fetchClients } from '@/services/clients.service'
import { useFormsStore } from '@/stores/forms/forms.store'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
import type { Asset } from '@/types/assets'
import type { Client } from '@/types/clients'

const props = defineProps<{
  /** Pré-seleciona um ativo — pula cliente e ativo, vai direto ao formulário. */
  preselectedAssetId?: string | null
  /** Label do ativo pré-selecionado (para exibição). */
  preselectedAssetLabel?: string | null
  /** Pré-seleciona um cliente — pula a etapa de seleção de cliente. */
  preselectedClientId?: string | null
}>()

const emit = defineEmits<{
  /** Emitido com o ID da inspeção criada. O pai redireciona. */
  created: [submissionId: string]
  close: []
}>()

const formsStore = useFormsStore()
const submissionsStore = useSubmissionsStore()

// ── Passos ────────────────────────────────────────────────────────────────

type StepId = 'form' | 'client' | 'asset'

const STEP_LABELS: Record<StepId, string> = {
  form: '1 · Formulário',
  client: '2 · Cliente',
  asset: '3 · Ativo',
}

const steps = computed<StepId[]>(() => {
  if (props.preselectedAssetId) return ['form']
  if (props.preselectedClientId) return ['form', 'asset']
  return ['form', 'client', 'asset']
})

const stepIndex = ref(0)
const currentStep = computed<StepId>(() => steps.value[stepIndex.value])
const isLastStep = computed(() => stepIndex.value === steps.value.length - 1)

// ── Seleções ──────────────────────────────────────────────────────────────

const selectedFormId = ref('')
const selectedClientId = ref(props.preselectedClientId ?? '')
const selectedAssetId = ref(props.preselectedAssetId ?? '')

// ── Dados remotos ─────────────────────────────────────────────────────────

const clients = ref<Client[]>([])
const clientAssets = ref<Asset[]>([])

const clientsLoading = ref(false)
const assetsLoading = ref(false)
const createError = ref<string | null>(null)

onMounted(async () => {
  if (!formsStore.items.length) await formsStore.load()
  // Se cliente já pré-selecionado, carrega ativos imediatamente (para o passo 'asset')
  if (props.preselectedClientId) {
    await loadClientAssets(props.preselectedClientId)
  }
})

async function loadClients() {
  if (clients.value.length) return
  clientsLoading.value = true
  try {
    const resp = await fetchClients(1, 100, true)
    clients.value = resp.data
  } finally {
    clientsLoading.value = false
  }
}

async function loadClientAssets(clientId: string) {
  assetsLoading.value = true
  clientAssets.value = []
  try {
    const resp = await fetchAssets(1, 100, {
      client_id: clientId || undefined,
      status: 'active',
    })
    clientAssets.value = resp.data
  } finally {
    assetsLoading.value = false
  }
}

// ── Navegação ─────────────────────────────────────────────────────────────

async function advance() {
  createError.value = null
  if (currentStep.value === 'form' && !selectedFormId.value) return
  if (isLastStep.value) {
    await handleCreate()
    return
  }

  const nextIndex = stepIndex.value + 1
  const nextStep = steps.value[nextIndex]
  stepIndex.value = nextIndex

  if (nextStep === 'client') await loadClients()
  if (nextStep === 'asset') await loadClientAssets(selectedClientId.value)
}

function back() {
  if (stepIndex.value > 0) stepIndex.value--
}

async function handleCreate() {
  if (!selectedFormId.value) return
  createError.value = null
  try {
    const created = await submissionsStore.create({
      form_id: selectedFormId.value,
      asset_id: selectedAssetId.value || null,
    })
    emit('created', created.id)
  } catch (err) {
    createError.value = extractProblemMessage(err, 'Não foi possível criar a inspeção.')
  }
}

function selectClient(c: Client) {
  selectedClientId.value = c.id
  selectedAssetId.value = ''
}
</script>

<template>
  <div class="ic">
    <!-- ── Cabeçalho ── -->
    <div class="ic-hdr">
      <div>
        <div class="eyebrow">Nova inspeção</div>
        <div class="ic-title">
          {{
            currentStep === 'form'
              ? 'Selecione o formulário'
              : currentStep === 'client'
                ? 'Selecione o cliente'
                : 'Selecione o ativo'
          }}
        </div>
      </div>
      <button type="button" class="btn-secondary btn-sm" @click="emit('close')">Fechar</button>
    </div>

    <!-- ── Indicador de passos ── -->
    <div class="ic-steps">
      <template v-for="(step, i) in steps" :key="step">
        <div
          class="ic-step"
          :class="{
            'ic-step--done': i < stepIndex,
            'ic-step--active': i === stepIndex,
          }"
        >
          <span class="ic-step-n">{{ i < stepIndex ? '✓' : i + 1 }}</span>
          <span class="ic-step-lbl">{{ STEP_LABELS[step] }}</span>
        </div>
        <div v-if="i < steps.length - 1" class="ic-step-sep"></div>
      </template>
    </div>

    <!-- ══ PASSO: FORMULÁRIO ══ -->
    <template v-if="currentStep === 'form'">
      <!-- Contexto pré-selecionado (se vier de um ativo) -->
      <div v-if="preselectedAssetId && preselectedAssetLabel" class="ic-ctx">
        <span class="ic-ctx-lbl">Ativo selecionado:</span>
        <span class="ic-ctx-val">{{ preselectedAssetLabel }}</span>
      </div>

      <div v-if="formsStore.isLoading" class="ic-loading">Carregando formulários…</div>
      <div v-else-if="!formsStore.items.length" class="ic-empty">
        Nenhum formulário disponível. Crie um formulário antes de iniciar uma inspeção.
      </div>
      <div v-else class="ic-list">
        <button
          v-for="form in formsStore.items"
          :key="form.id"
          type="button"
          class="ic-item"
          :class="{ 'ic-item--sel': selectedFormId === form.id }"
          @click="selectedFormId = form.id"
        >
          <div class="ic-item-name">{{ form.name }}</div>
          <div class="ic-item-sub">v{{ form.current_version_number }}</div>
        </button>
      </div>
    </template>

    <!-- ══ PASSO: CLIENTE ══ -->
    <template v-else-if="currentStep === 'client'">
      <div v-if="clientsLoading" class="ic-loading">Carregando clientes…</div>
      <div v-else class="ic-list">
        <!-- Opção "sem cliente" -->
        <button
          type="button"
          class="ic-item ic-item--neutral"
          :class="{ 'ic-item--sel': selectedClientId === '' }"
          @click="selectedClientId = ''; selectedAssetId = ''"
        >
          <div class="ic-item-name">Sem cliente / patrimônio próprio</div>
          <div class="ic-item-sub">A inspeção não será vinculada a um cliente</div>
        </button>
        <button
          v-for="c in clients"
          :key="c.id"
          type="button"
          class="ic-item"
          :class="{ 'ic-item--sel': selectedClientId === c.id }"
          @click="selectClient(c)"
        >
          <div class="ic-item-name">{{ c.name }}</div>
        </button>
      </div>
    </template>

    <!-- ══ PASSO: ATIVO ══ -->
    <template v-else-if="currentStep === 'asset'">
      <div v-if="assetsLoading" class="ic-loading">Carregando ativos…</div>
      <div v-else-if="!clientAssets.length && !selectedClientId" class="ic-empty">
        Nenhum cliente selecionado — a inspeção será criada sem ativo vinculado.
      </div>
      <div v-else class="ic-list">
        <!-- Opção "sem ativo" -->
        <button
          type="button"
          class="ic-item ic-item--neutral"
          :class="{ 'ic-item--sel': selectedAssetId === '' }"
          @click="selectedAssetId = ''"
        >
          <div class="ic-item-name">Sem ativo vinculado</div>
          <div class="ic-item-sub">Inspeção geral, não ligada a um ativo</div>
        </button>
        <button
          v-for="a in clientAssets"
          :key="a.id"
          type="button"
          class="ic-item"
          :class="{ 'ic-item--sel': selectedAssetId === a.id }"
          @click="selectedAssetId = a.id"
        >
          <div class="ic-item-name">{{ a.identifier }}</div>
          <div v-if="a.parent_asset_id" class="ic-item-sub">Componente</div>
        </button>
      </div>
    </template>

    <!-- ── Erro ── -->
    <p v-if="createError" class="ic-error">{{ createError }}</p>

    <!-- ── Navegação ── -->
    <div class="ic-nav">
      <button v-if="stepIndex > 0" type="button" class="btn-secondary" @click="back">
        ← Voltar
      </button>
      <div style="flex: 1"></div>
      <button
        type="button"
        class="btn-primary"
        :disabled="(currentStep === 'form' && !selectedFormId) || submissionsStore.isSaving"
        @click="advance"
      >
        {{
          isLastStep
            ? submissionsStore.isSaving
              ? 'Criando…'
              : 'Iniciar inspeção'
            : 'Avançar →'
        }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.ic {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* Cabeçalho */
.ic-hdr {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.ic-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--sa-text, #111827);
  margin-top: 3px;
}

/* Passos */
.ic-steps {
  display: flex;
  align-items: center;
  gap: 0;
  flex-wrap: nowrap;
}
.ic-step {
  display: flex;
  align-items: center;
  gap: 5px;
}
.ic-step-n {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--sa-border, #e5e7eb);
  color: var(--sa-muted, #6b7280);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}
.ic-step--active .ic-step-n {
  background: var(--sa-primary, #2563eb);
  color: #fff;
}
.ic-step--done .ic-step-n {
  background: var(--sa-ok, #10b981);
  color: #fff;
}
.ic-step-lbl {
  font-size: 11px;
  font-weight: 600;
  color: var(--sa-muted, #6b7280);
}
.ic-step--active .ic-step-lbl {
  color: var(--sa-text, #111827);
}
.ic-step-sep {
  flex: 1;
  height: 1px;
  background: var(--sa-border, #e5e7eb);
  margin: 0 8px;
  min-width: 12px;
}

/* Contexto pré-selecionado */
.ic-ctx {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 7px;
  font-size: 12px;
}
.ic-ctx-lbl {
  color: var(--sa-muted, #6b7280);
}
.ic-ctx-val {
  font-weight: 700;
  color: var(--sa-primary, #2563eb);
}

/* Lista de opções */
.ic-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 280px;
  overflow-y: auto;
}

.ic-item {
  text-align: left;
  padding: 10px 12px;
  border: 1.5px solid var(--sa-border, #e5e7eb);
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  font-family: inherit;
}
.ic-item:hover {
  border-color: var(--sa-primary, #2563eb);
  background: #fafbff;
}
.ic-item--sel {
  border-color: var(--sa-primary, #2563eb);
  background: #eff6ff;
}
.ic-item--neutral {
  background: #f9fafb;
}

.ic-item-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--sa-text, #111827);
}
.ic-item-sub {
  font-size: 11px;
  color: var(--sa-muted, #6b7280);
  margin-top: 2px;
}

/* Loading / empty */
.ic-loading {
  font-size: 13px;
  color: var(--sa-muted, #6b7280);
  padding: 8px 0;
}
.ic-empty {
  font-size: 13px;
  color: var(--sa-muted, #6b7280);
  padding: 8px 0;
  line-height: 1.5;
}

/* Erro */
.ic-error {
  font-size: 13px;
  font-weight: 600;
  color: var(--sa-danger, #ef4444);
}

/* Navegação */
.ic-nav {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
  border-top: 1px solid var(--sa-border, #e5e7eb);
}
</style>
