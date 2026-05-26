<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { useFormsStore } from '@/stores/forms/forms.store'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'

const router = useRouter()
const submissionsStore = useSubmissionsStore()
const formsStore = useFormsStore()

const showComposer = ref(false)
const selectedFormId = ref('')
const createError = ref<string | null>(null)

const completedCount = computed(
  () => submissionsStore.items.filter((s) => s.status === 'completed').length,
)

const currentPage = ref(1)

async function loadPage(page: number) {
  currentPage.value = page
  await submissionsStore.load(page)
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
    <section class="flex flex-wrap items-center justify-between gap-3 px-1">
      <div>
        <p class="eyebrow">Execução</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-sa-text">Inspeções recentes</h2>
        <p class="mt-2 text-sm text-sa-muted">Acompanhe status, início de execução e score operacional.</p>
      </div>
      <BaseButton type="button" @click="openComposer">Nova inspeção</BaseButton>
    </section>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <article class="surface-panel p-4">
        <span class="eyebrow">Total</span>
        <strong class="mt-2 block text-2xl font-semibold text-sa-text">
          {{ submissionsStore.meta?.total ?? submissionsStore.items.length }}
        </strong>
      </article>
      <article class="surface-panel p-4">
        <span class="eyebrow">Concluídas</span>
        <strong class="mt-2 block text-2xl font-semibold text-sa-text">{{ completedCount }}</strong>
      </article>
      <article class="surface-panel p-4">
        <span class="eyebrow">Página</span>
        <strong class="mt-2 block text-2xl font-semibold text-sa-text">
          {{ currentPage }} / {{ submissionsStore.meta?.total_pages ?? 1 }}
        </strong>
      </article>
      <article class="surface-panel p-4">
        <span class="eyebrow">Mostrando</span>
        <strong class="mt-2 block text-2xl font-semibold text-sa-text">
          {{ submissionsStore.items.length }}
        </strong>
        <p class="mt-1 text-sm text-sa-muted">de {{ submissionsStore.meta?.total ?? submissionsStore.items.length }}</p>
      </article>
    </section>

    <section v-if="showComposer" class="surface-panel p-5 sm:p-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="eyebrow">Nova inspeção</p>
          <h3 class="mt-2 text-xl font-semibold text-sa-text">Selecione o formulário</h3>
        </div>
        <BaseButton type="button" variant="ghost" @click="closeComposer">Fechar</BaseButton>
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
            <BaseButton type="submit" :disabled="submissionsStore.isSaving || !selectedFormId">
              {{ submissionsStore.isSaving ? 'Criando...' : 'Iniciar inspeção' }}
            </BaseButton>
          </div>
        </template>

        <p v-if="createError" class="text-sm font-medium text-sa-danger">{{ createError }}</p>
      </form>
    </section>

    <p v-if="submissionsStore.error" class="text-sm font-medium text-sa-danger">
      {{ submissionsStore.error }}
    </p>
    <p v-else-if="submissionsStore.isLoading" class="text-sm font-medium text-sa-muted">
      Carregando inspeções...
    </p>

    <section v-if="submissionsStore.items.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="submission in submissionsStore.items"
        :key="submission.id"
        class="surface-panel p-5"
      >
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="eyebrow">{{ statusLabel(submission.status) }}</p>
            <h3 class="mt-3 text-xl font-semibold text-sa-text">{{ submission.form_name }}</h3>
          </div>
          <span
            class="status-chip"
            :class="{ 'status-chip--inactive': submission.status !== 'completed' }"
          >
            {{ submission.score !== null ? `${submission.score}%` : 'N/A' }}
          </span>
        </div>
        <p class="mt-3 text-sm leading-6 text-sa-muted">
          Início: {{ new Date(submission.started_at).toLocaleString('pt-BR') }}
        </p>
        <footer class="mt-5 flex items-center justify-between gap-3">
          <span class="text-sm text-sa-muted">
            {{ submission.finished_at ? new Date(submission.finished_at).toLocaleString('pt-BR') : 'Em andamento' }}
          </span>
          <button
            class="inline-action"
            type="button"
            @click="router.push({ name: 'submission-detail', params: { id: submission.id } })"
          >
            Abrir →
          </button>
        </footer>
      </article>
    </section>

    <section v-else-if="!submissionsStore.isLoading" class="surface-panel p-6 text-center">
      <p class="eyebrow">Sem dados</p>
      <h3 class="mt-3 text-xl font-semibold text-sa-text">Nenhuma inspeção registrada</h3>
      <p class="mt-2 text-sm text-sa-muted">
        Clique em "Nova inspeção" para iniciar a partir de um formulário cadastrado.
      </p>
    </section>

    <nav
      v-if="submissionsStore.meta && submissionsStore.meta.total_pages > 1"
      class="flex items-center justify-center gap-4"
    >
      <BaseButton
        type="button"
        variant="ghost"
        :disabled="currentPage <= 1 || submissionsStore.isLoading"
        @click="loadPage(currentPage - 1)"
      >
        ← Anterior
      </BaseButton>
      <span class="text-sm text-sa-muted">
        Página {{ currentPage }} de {{ submissionsStore.meta.total_pages }}
      </span>
      <BaseButton
        type="button"
        variant="ghost"
        :disabled="!submissionsStore.meta.has_next || submissionsStore.isLoading"
        @click="loadPage(currentPage + 1)"
      >
        Próxima →
      </BaseButton>
    </nav>
  </AppShell>
</template>
