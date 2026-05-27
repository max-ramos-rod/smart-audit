<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { useContextStore } from '@/stores/context/context.store'

const router = useRouter()
const contextStore = useContextStore()

const context = computed(() => contextStore.context)
const activeCompany = computed(() => context.value?.active_company)
const membership = computed(() => context.value?.membership)
const stats = computed(() => contextStore.stats)

const activePeriod = ref<string>('all')

const PERIOD_OPTIONS = [
  { label: '7 dias', value: '7d' },
  { label: '30 dias', value: '30d' },
  { label: '90 dias', value: '90d' },
  { label: 'Tudo', value: 'all' },
]

async function setPeriod(period: string) {
  activePeriod.value = period
  await contextStore.loadStats(period)
}

onMounted(() => {
  contextStore.loadStats(activePeriod.value)
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
    <div class="page">

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
      <section class="flex items-center justify-between gap-3 px-1" style="margin-top: 20px;">
        <p class="eyebrow">Métricas de inspeções</p>
        <div class="filter-tabs" style="margin-bottom: 0;">
          <button
            v-for="opt in PERIOD_OPTIONS"
            :key="opt.value"
            type="button"
            class="filter-tab"
            :class="{ active: activePeriod === opt.value }"
            @click="setPeriod(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>
      </section>

      <div
        v-if="contextStore.isLoadingStats"
        class="surface-panel p-5 text-center text-sm text-sa-muted"
        style="margin-top: 12px;"
      >
        Carregando métricas...
      </div>
      <div v-else class="stats-grid" style="margin-top: 12px;">
        <article class="scard">
          <div class="sc-label">Total</div>
          <div class="sc-value">{{ stats?.total_submissions ?? '—' }}</div>
          <div class="sc-desc">inspeções criadas</div>
        </article>
        <article class="scard sc-ok">
          <div class="sc-label">Concluídas</div>
          <div class="sc-value">{{ stats?.completed ?? '—' }}</div>
          <div class="sc-desc">status completed</div>
        </article>
        <article class="scard sc-accent">
          <div class="sc-label">Em andamento</div>
          <div class="sc-value">{{ stats?.in_progress ?? '—' }}</div>
          <div class="sc-desc">aguardando finalização</div>
        </article>
        <article class="scard">
          <div class="sc-label">Score médio</div>
          <div class="sc-value">
            {{ stats?.avg_score !== null && stats?.avg_score !== undefined ? `${stats.avg_score}%` : '—' }}
          </div>
          <div class="sc-desc">inspeções concluídas</div>
        </article>
      </div>

      <!-- inspecoes recentes -->
      <section v-if="stats?.recent?.length" style="margin-top: 20px;">
        <p class="eyebrow" style="margin-bottom: 10px; padding-left: 2px;">Inspeções recentes</p>
        <div class="lstack">
          <div
            v-for="submission in stats.recent"
            :key="submission.id"
            class="lrow"
            @click="router.push({ name: 'submission-detail', params: { id: submission.id } })"
          >
            <div class="lrow-main">
              <div class="lrow-title">{{ submission.form_name }}</div>
              <div class="lrow-sub">Iniciada {{ new Date(submission.started_at).toLocaleString('pt-BR') }}</div>
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
      </section>

    </div>
  </AppShell>
</template>
