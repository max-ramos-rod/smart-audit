<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { useContextStore } from '@/stores/context/context.store'

const router = useRouter()
const contextStore = useContextStore()

const context = computed(() => contextStore.context)
const activeCompany = computed(() => context.value?.active_company)
const membership = computed(() => context.value?.membership)
const stats = computed(() => contextStore.stats)

onMounted(() => {
  contextStore.loadStats()
})

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
    <!-- header da empresa ativa -->
    <section class="surface-panel grid gap-5 p-5 sm:p-6">
      <div class="space-y-3">
        <p class="eyebrow">Operação ativa</p>
        <h2 class="text-2xl font-semibold tracking-tight text-sa-text sm:text-3xl">
          {{ activeCompany?.name ?? 'Selecione uma empresa' }}
        </h2>
        <p class="muted-copy max-w-2xl text-base">
          Painel de acompanhamento de auditorias, checklists e inspeções por empresa.
        </p>
      </div>

      <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article class="rounded-3xl border border-[color:var(--sa-line)] bg-white/75 p-4">
          <span class="eyebrow">Papel atual</span>
          <strong class="mt-2 block text-xl font-semibold text-sa-text">
            {{ membership?.role ?? '—' }}
          </strong>
        </article>
        <article class="rounded-3xl border border-[color:var(--sa-line)] bg-white/75 p-4">
          <span class="eyebrow">Plano</span>
          <strong class="mt-2 block text-xl font-semibold text-sa-text">
            {{ activeCompany?.plan ?? '—' }}
          </strong>
        </article>
        <article class="rounded-3xl border border-[color:var(--sa-line)] bg-white/75 p-4">
          <span class="eyebrow">Empresas disponíveis</span>
          <strong class="mt-2 block text-xl font-semibold text-sa-text">
            {{ context?.available_companies.length ?? 0 }}
          </strong>
        </article>
        <article class="rounded-3xl border border-[color:var(--sa-line)] bg-white/75 p-4">
          <span class="eyebrow">Seleção pendente</span>
          <strong class="mt-2 block text-xl font-semibold text-sa-text">
            {{ context?.requires_company_selection ? 'Sim' : 'Não' }}
          </strong>
        </article>
      </div>
    </section>

    <!-- metricas de inspecoes -->
    <section>
      <p class="eyebrow mb-3 px-1">Métricas de inspeções</p>
      <div
        v-if="contextStore.isLoadingStats"
        class="surface-panel p-5 text-center text-sm text-sa-muted"
      >
        Carregando métricas...
      </div>
      <div v-else class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article class="surface-panel p-5">
          <span class="eyebrow">Total</span>
          <strong class="mt-2 block text-3xl font-semibold text-sa-text">
            {{ stats?.total_submissions ?? '—' }}
          </strong>
          <p class="mt-1 text-sm text-sa-muted">inspecoes criadas</p>
        </article>
        <article class="surface-panel p-5">
          <span class="eyebrow">Concluídas</span>
          <strong class="mt-2 block text-3xl font-semibold text-sa-text">
            {{ stats?.completed ?? '—' }}
          </strong>
          <p class="mt-1 text-sm text-sa-muted">status completed</p>
        </article>
        <article class="surface-panel p-5">
          <span class="eyebrow">Em andamento</span>
          <strong class="mt-2 block text-3xl font-semibold text-sa-text">
            {{ stats?.in_progress ?? '—' }}
          </strong>
          <p class="mt-1 text-sm text-sa-muted">aguardando finalização</p>
        </article>
        <article class="surface-panel p-5">
          <span class="eyebrow">Score médio</span>
          <strong class="mt-2 block text-3xl font-semibold text-sa-text">
            {{ stats?.avg_score !== null && stats?.avg_score !== undefined ? `${stats.avg_score}%` : '—' }}
          </strong>
          <p class="mt-1 text-sm text-sa-muted">inspeções concluídas</p>
        </article>
      </div>
    </section>

    <!-- inspecoes recentes -->
    <section v-if="stats?.recent?.length">
      <p class="eyebrow mb-3 px-1">Inspeções recentes</p>
      <div class="surface-panel overflow-hidden">
        <table>
          <thead>
            <tr>
              <th>Formulário</th>
              <th>Status</th>
              <th>Score</th>
              <th>Início</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="submission in stats.recent" :key="submission.id">
              <td class="font-medium text-sa-text">{{ submission.form_name }}</td>
              <td>
                <span
                  class="status-chip"
                  :class="{ 'status-chip--inactive': submission.status !== 'completed' }"
                >
                  {{ statusLabel(submission.status) }}
                </span>
              </td>
              <td class="text-sa-muted">
                {{ submission.score !== null ? `${submission.score}%` : '—' }}
              </td>
              <td class="text-sa-muted">
                {{ new Date(submission.started_at).toLocaleString('pt-BR') }}
              </td>
              <td class="text-right">
                <button
                  class="inline-action"
                  type="button"
                  @click="router.push({ name: 'submission-detail', params: { id: submission.id } })"
                >
                  Abrir →
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </AppShell>
</template>
