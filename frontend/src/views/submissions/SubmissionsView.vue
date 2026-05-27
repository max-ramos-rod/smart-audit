<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { useFormsStore } from '@/stores/forms/forms.store'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'

const router = useRouter()
const submissionsStore = useSubmissionsStore()
const formsStore = useFormsStore()

const showComposer = ref(false)
const selectedFormId = ref('')
const createError = ref<string | null>(null)

const currentPage = ref(1)
const activeStatus = ref<string | undefined>(undefined)

const STATUS_OPTIONS = [
  { label: 'Todas', value: undefined },
  { label: 'Em andamento', value: 'in_progress' },
  { label: 'Concluídas', value: 'completed' },
] as const

async function loadPage(page: number, status?: string) {
  currentPage.value = page
  await submissionsStore.load(page, 20, status)
}

async function setStatus(status: string | undefined) {
  activeStatus.value = status
  await loadPage(1, status)
}

onMounted(() => {
  loadPage(1)
})

async function openComposer() {
  createError.value = null
  selectedFormId.value = ''
  if (!formsStore.items.length) {
    await formsStore.load()
  }
  showComposer.value = true
}

function closeComposer() {
  showComposer.value = false
  selectedFormId.value = ''
  createError.value = null
}

async function handleCreate() {
  if (!selectedFormId.value) return
  createError.value = null
  try {
    const created = await submissionsStore.create({ form_id: selectedFormId.value })
    closeComposer()
    await loadPage(1)
    router.push({ name: 'submission-detail', params: { id: created.id } })
  } catch (err: any) {
    createError.value = extractProblemMessage(err, 'Não foi possível criar a inspeção.')
  }
}

function statusLabel(status: string) {
  const map: Record<string, string> = {
    in_progress: 'Em andamento',
    completed: 'Concluída',
    draft: 'Rascunho',
    cancelled: 'Cancelada',
  }
  return map[status] ?? status
}
</script>

<template>
  <AppShell>
    <div class="page">

      <div class="phdr">
        <div>
          <p class="eyebrow">Execução</p>
          <h2 class="page-h1">Inspeções</h2>
          <p class="page-desc">Acompanhe status, início de execução e score operacional.</p>
        </div>
        <button type="button" class="btn-primary" @click="openComposer">Nova inspeção</button>
      </div>

      <!-- composer -->
      <section v-if="showComposer" class="surface-panel p-5 sm:p-6" style="margin-bottom: 16px;">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="eyebrow">Nova inspeção</p>
            <h3 class="mt-2 text-xl font-semibold text-sa-text">Selecione o formulário</h3>
          </div>
          <button type="button" class="btn-secondary btn-sm" @click="closeComposer">Fechar</button>
        </div>

        <form class="mt-5 grid gap-4" @submit.prevent="handleCreate">
          <div v-if="formsStore.isLoading" class="text-sm text-sa-muted">
            Carregando formulários...
          </div>
          <div v-else-if="!formsStore.items.length" class="text-sm text-sa-muted">
            Nenhum formulário disponível. Crie um formulário antes de iniciar uma inspeção.
          </div>
          <template v-else>
            <label class="grid gap-2">
              <span>Formulário</span>
              <select v-model="selectedFormId" required>
                <option value="" disabled>Selecione um formulário</option>
                <option v-for="form in formsStore.items" :key="form.id" :value="form.id">
                  {{ form.name }} — v{{ form.current_version_number }}
                </option>
              </select>
            </label>

            <div class="flex gap-3">
              <button
                type="submit"
                class="btn-primary"
                :disabled="submissionsStore.isSaving || !selectedFormId"
              >
                {{ submissionsStore.isSaving ? 'Criando...' : 'Iniciar inspeção' }}
              </button>
            </div>
          </template>

          <p v-if="createError" class="text-sm font-medium text-sa-danger">{{ createError }}</p>
        </form>
      </section>

      <p v-if="submissionsStore.error" class="text-sm font-medium text-sa-danger" style="margin-bottom: 8px;">
        {{ submissionsStore.error }}
      </p>
      <p v-else-if="submissionsStore.isLoading" class="text-sm font-medium text-sa-muted" style="margin-bottom: 8px;">
        Carregando inspeções...
      </p>

      <!-- filter tabs -->
      <div class="filter-tabs">
        <button
          v-for="opt in STATUS_OPTIONS"
          :key="String(opt.value)"
          type="button"
          class="filter-tab"
          :class="{ active: activeStatus === opt.value }"
          @click="setStatus(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>

      <!-- list -->
      <div v-if="submissionsStore.items.length" class="lstack">
        <div
          v-for="submission in submissionsStore.items"
          :key="submission.id"
          class="lrow"
          @click="router.push({ name: 'submission-detail', params: { id: submission.id } })"
        >
          <div class="lrow-main">
            <div class="lrow-title">{{ submission.form_name }}</div>
            <div class="lrow-sub">
              {{ submission.finished_at
                ? 'Concluída ' + new Date(submission.finished_at).toLocaleString('pt-BR')
                : 'Início ' + new Date(submission.started_at).toLocaleString('pt-BR') }}
            </div>
          </div>
          <div class="lrow-end">
            <span
              v-if="submission.score !== null"
              class="score-val"
              :class="submission.score >= 85 ? 'ok' : submission.score >= 65 ? 'warn' : 'err'"
            >
              {{ submission.score }}%
            </span>
            <span
              class="status-chip"
              :class="{
                'status-chip--warn': submission.status === 'in_progress',
                'status-chip--inactive': submission.status === 'cancelled',
              }"
            >
              {{ statusLabel(submission.status) }}
            </span>
          </div>
        </div>
      </div>

      <div v-else-if="!submissionsStore.isLoading" class="surface-panel p-6 text-center">
        <p class="eyebrow">Sem dados</p>
        <h3 class="mt-3 text-xl font-semibold text-sa-text">Nenhuma inspeção registrada</h3>
        <p class="mt-2 text-sm text-sa-muted">
          Clique em "Nova inspeção" para iniciar a partir de um formulário cadastrado.
        </p>
      </div>

      <nav
        v-if="submissionsStore.meta && submissionsStore.meta.total_pages > 1"
        class="flex items-center justify-center gap-4"
        style="margin-top: 16px;"
      >
        <button
          type="button"
          class="btn-secondary btn-sm"
          :disabled="currentPage <= 1 || submissionsStore.isLoading"
          @click="loadPage(currentPage - 1, activeStatus)"
        >
          ← Anterior
        </button>
        <span class="text-sm text-sa-muted">
          Página {{ currentPage }} de {{ submissionsStore.meta.total_pages }}
        </span>
        <button
          type="button"
          class="btn-secondary btn-sm"
          :disabled="!submissionsStore.meta.has_next || submissionsStore.isLoading"
          @click="loadPage(currentPage + 1, activeStatus)"
        >
          Próxima →
        </button>
      </nav>

    </div>
  </AppShell>
</template>
