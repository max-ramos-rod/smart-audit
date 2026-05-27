<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'
import { useFormsStore } from '@/stores/forms/forms.store'

const router = useRouter()
const contextStore = useContextStore()
const authStore = useAuthStore()
const formsStore = useFormsStore()

const context = computed(() => contextStore.context)
const activeCompany = computed(() => context.value?.active_company)
const stats = computed(() => contextStore.stats)

const activePeriod = ref<string>('all')

const PERIOD_OPTIONS = [
  { label: '7 dias', value: '7d' },
  { label: '30 dias', value: '30d' },
  { label: '90 dias', value: '90d' },
  { label: 'Tudo', value: 'all' },
]

const greeting = computed(() => {
  const hour = new Date().getHours()
  const greet = hour < 12 ? 'Bom dia' : hour < 18 ? 'Boa tarde' : 'Boa noite'
  const firstName = authStore.user?.name?.split(' ')[0] ?? ''
  return firstName ? `${greet}, ${firstName}` : greet
})

const activeForms = computed(() => formsStore.items.filter((f) => f.is_active).slice(0, 3))

async function setPeriod(period: string) {
  activePeriod.value = period
  await contextStore.loadStats(period)
}

onMounted(async () => {
  contextStore.loadStats(activePeriod.value)
  if (!formsStore.items.length) formsStore.load(1, 100)
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
      <div class="phdr">
        <div>
          <p class="eyebrow">Operação ativa · {{ activeCompany?.name ?? '—' }}</p>
          <h2 class="page-h1">{{ greeting }}</h2>
          <p class="page-desc">Acompanhe o status das inspeções e checklists em tempo real.</p>
        </div>
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; flex-wrap: wrap;">
        <div class="slabel" style="margin-bottom: 0;">Métricas</div>
        <div class="filter-tabs" style="margin-bottom: 0; width: 100%; max-width: 420px;">
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
      </div>

      <div v-if="contextStore.isLoadingStats" style="font-size: 13px; color: var(--sa-muted); text-align: center; padding: 20px 0;">
        Carregando métricas...
      </div>
      <div v-else class="stats-grid" style="margin-bottom: 20px;">
        <article class="scard">
          <div class="sc-label">Total de inspeções</div>
          <div class="sc-value">{{ stats?.total_submissions ?? '—' }}</div>
          <div class="sc-desc">período selecionado</div>
        </article>
        <article class="scard sc-ok">
          <div class="sc-label">Concluídas</div>
          <div class="sc-value">{{ stats?.completed ?? '—' }}</div>
          <div class="sc-desc">status completed</div>
        </article>
        <article class="scard">
          <div class="sc-label">Em andamento</div>
          <div class="sc-value">{{ stats?.in_progress ?? '—' }}</div>
          <div class="sc-desc">aguardando finalização</div>
        </article>
        <article class="scard sc-accent">
          <div class="sc-label">Score médio</div>
          <div class="sc-value">
            {{ stats?.avg_score !== null && stats?.avg_score !== undefined ? `${stats.avg_score}%` : '—' }}
          </div>
          <div class="sc-desc">inspeções concluídas</div>
        </article>
      </div>

      <template v-if="stats?.recent?.length">
        <div class="slabel">Inspeções recentes</div>
        <div class="lstack" style="margin-bottom: 20px;">
          <div
            v-for="submission in stats.recent"
            :key="submission.id"
            class="lrow"
            @click="router.push({ name: 'submission-detail', params: { id: submission.id } })"
          >
            <div class="lrow-main">
              <div class="lrow-title">{{ submission.form_name }}</div>
              <div class="lrow-sub">
                Iniciada
                {{ new Date(submission.started_at).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) }}
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
                  'status-chip--neu': submission.status === 'draft',
                }"
              >
                {{ statusLabel(submission.status) }}
              </span>
            </div>
          </div>
        </div>
      </template>

      <template v-if="activeForms.length">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
          <div class="slabel" style="margin-bottom: 0;">Formulários ativos</div>
          <button
            type="button"
            @click="router.push({ name: 'forms' })"
            style="border: none; background: none; cursor: pointer; font-size: 12px; font-weight: 600; color: var(--sa-brand); font-family: inherit; padding: 0;"
          >
            Ver todos →
          </button>
        </div>
        <div class="lstack">
          <div
            v-for="form in activeForms"
            :key="form.id"
            class="lrow"
            style="cursor: default;"
          >
            <div class="lrow-main">
              <div class="lrow-title">{{ form.name }}</div>
              <div class="lrow-sub">
                v{{ form.current_version_number }}
                <template v-if="form.published_at"> · publicado {{ new Date(form.published_at).toLocaleDateString('pt-BR') }}</template>
              </div>
            </div>
            <div class="lrow-end">
              <span class="status-chip">Ativo</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </AppShell>
</template>
