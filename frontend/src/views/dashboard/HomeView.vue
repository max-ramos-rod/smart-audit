<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { useAuthStore } from '@/stores/auth/auth.store'
import { useContextStore } from '@/stores/context/context.store'
import { useFormsStore } from '@/stores/forms/forms.store'
import type { ScoreTrendPoint } from '@/types/context'
import { scoreClass } from '@/utils/score'

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

const sparklinePoints = computed(() => {
  const trend = stats.value?.score_trend
  if (!trend?.length) return ''
  const n = trend.length
  const scores = trend.map((p: ScoreTrendPoint) => p.avg_score)
  const minS = Math.min(...scores)
  const maxS = Math.max(...scores)
  const range = maxS - minS || 1
  return trend
    .map((p: ScoreTrendPoint, i: number) => {
      const x = n === 1 ? 150 : (i / (n - 1)) * 300
      const y = 56 - ((p.avg_score - minS) / range) * 52
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
})

// ── Onboarding checklist (Sprint 3) ─────────────────────────────────────────
// Mostra quando a empresa parece nova: sem inspeções e sem formulários ativos.

const showOnboarding = computed(
  () =>
    !contextStore.isLoadingStats &&
    (stats.value?.total_submissions ?? 0) === 0 &&
    formsStore.items.filter((f) => f.is_active).length === 0,
)

const onboardingSteps = computed(() => [
  {
    id: 'asset-types',
    label: 'Criar tipo de ativo',
    desc: 'Define a categoria dos ativos inspecionáveis (ex: Veículo, Prédio).',
    done: false,
    route: '/asset-types',
    action: 'Criar tipo →',
  },
  {
    id: 'clients',
    label: 'Cadastrar cliente',
    desc: 'Registre as empresas cujos ativos serão inspecionados.',
    done: false,
    route: '/clients',
    action: 'Cadastrar →',
  },
  {
    id: 'forms',
    label: 'Criar formulário',
    desc: 'Monte o checklist de inspeção com campos e pesos de conformidade.',
    done: formsStore.items.length > 0,
    route: '/forms',
    action: 'Criar formulário →',
  },
  {
    id: 'assets',
    label: 'Cadastrar ativo',
    desc: 'Registre os ativos e seus componentes vinculados ao cliente.',
    done: false,
    route: '/assets',
    action: 'Cadastrar ativo →',
  },
  {
    id: 'first-inspection',
    label: 'Iniciar primeira inspeção',
    desc: 'Tudo pronto! Execute a primeira inspeção e veja o score ao vivo.',
    done: (stats.value?.total_submissions ?? 0) > 0,
    route: '/submissions',
    action: 'Nova inspeção →',
  },
])

const onboardingProgress = computed(() => {
  const done = onboardingSteps.value.filter((s) => s.done).length
  return Math.round((done / onboardingSteps.value.length) * 100)
})

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

      <!-- ── ONBOARDING CHECKLIST (aparece quando a empresa é nova) — Sprint 3 ── -->
      <div v-if="showOnboarding" class="onb-card">
        <div class="onb-head">
          <div>
            <div class="onb-title">Configure o Smart Audit</div>
            <div class="onb-sub">Siga os passos abaixo para criar sua primeira inspeção.</div>
          </div>
          <div class="onb-progress-wrap">
            <div class="onb-progress-ring" :style="`--pct:${onboardingProgress}%`">
              <span class="onb-progress-val">{{ onboardingProgress }}%</span>
            </div>
          </div>
        </div>

        <div class="onb-steps">
          <div
            v-for="(step, i) in onboardingSteps"
            :key="step.id"
            class="onb-step"
            :class="{ 'onb-step--done': step.done }"
          >
            <div class="onb-step-n" :class="{ 'onb-step-n--done': step.done }">
              <span v-if="step.done">✓</span>
              <span v-else>{{ i + 1 }}</span>
            </div>
            <div class="onb-step-body">
              <div class="onb-step-label">{{ step.label }}</div>
              <div class="onb-step-desc">{{ step.desc }}</div>
            </div>
            <RouterLink v-if="!step.done" :to="step.route" class="onb-step-action">
              {{ step.action }}
            </RouterLink>
            <span v-else class="onb-step-done-badge">✓ Feito</span>
          </div>
        </div>
      </div>

      <!-- ── MÉTRICAS E PAINÉIS (ocultos durante o onboarding) ── -->
      <template v-if="!showOnboarding">
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

      <template v-if="stats?.score_by_form?.length">
        <div class="slabel" style="margin-bottom: 10px;">Score por formulário</div>
        <div class="dash-chart-card" style="margin-bottom: 20px;">
          <div
            v-for="item in stats.score_by_form"
            :key="item.form_id"
            class="dash-bar-row"
          >
            <div class="dash-bar-label" :title="item.form_name">{{ item.form_name }}</div>
            <div class="dash-bar-track">
              <div
                class="dash-bar-fill"
                :style="{ width: item.avg_score + '%' }"
                :class="`fill-${scoreClass(item.avg_score)}`"
              ></div>
            </div>
            <div class="dash-bar-pct" :class="`pct-${scoreClass(item.avg_score)}`">
              {{ item.avg_score }}%
            </div>
            <div class="dash-bar-count">{{ item.count }}x</div>
          </div>
        </div>
      </template>

      <template v-if="stats?.score_trend?.length">
        <div class="slabel" style="margin-bottom: 10px;">Tendência (30 dias)</div>
        <div class="dash-chart-card dash-sparkline-card" style="margin-bottom: 20px;">
          <svg
            class="dash-sparkline"
            viewBox="0 0 300 60"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <polyline
              :points="sparklinePoints"
              fill="none"
              stroke="var(--sa-brand)"
              stroke-width="2"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
          </svg>
          <div class="dash-spark-labels">
            <span>{{ stats.score_trend[0]?.date?.slice(5) }}</span>
            <span>{{ stats.score_trend[stats.score_trend.length - 1]?.date?.slice(5) }}</span>
          </div>
        </div>
      </template>

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
                :class="scoreClass(submission.score ?? 0)"
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
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
/* ── Onboarding card (Sprint 3) ── */
.onb-card {
  background: var(--sa-card, #fff);
  border: 1px solid var(--sa-border, #e5e7eb);
  border-radius: 14px;
  padding: 20px 22px;
  margin-bottom: 24px;
}

.onb-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.onb-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--sa-text, #111827);
  margin-bottom: 3px;
}

.onb-sub {
  font-size: 12px;
  color: var(--sa-muted, #6b7280);
}

/* Anel de progresso (CSS conic-gradient) */
.onb-progress-ring {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: conic-gradient(var(--sa-ok, #10b981) var(--pct), #e5e7eb 0);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  position: relative;
}

.onb-progress-ring::before {
  content: '';
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--sa-card, #fff);
  position: absolute;
}

.onb-progress-val {
  font-size: 12px;
  font-weight: 700;
  color: var(--sa-text, #111827);
  position: relative;
  z-index: 1;
}

/* Passos */
.onb-steps {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.onb-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--sa-surface, #f9fafb);
  border: 1px solid var(--sa-border, #e5e7eb);
  transition: border-color 0.15s;
}

.onb-step--done {
  background: #f0fdf4;
  border-color: #bbf7d0;
  opacity: 0.7;
}

.onb-step-n {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--sa-border, #e5e7eb);
  color: var(--sa-muted, #6b7280);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.onb-step-n--done {
  background: var(--sa-ok, #10b981);
  color: #fff;
}

.onb-step-body {
  flex: 1;
  min-width: 0;
}

.onb-step-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--sa-text, #111827);
}

.onb-step-desc {
  font-size: 11px;
  color: var(--sa-muted, #6b7280);
  margin-top: 1px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.onb-step-action {
  font-size: 11px;
  font-weight: 700;
  color: var(--sa-primary, #2563eb);
  text-decoration: none;
  padding: 4px 8px;
  background: #eff6ff;
  border-radius: 5px;
  white-space: nowrap;
  flex-shrink: 0;
  border: 1px solid #bfdbfe;
  transition: background 0.12s;
}

.onb-step-action:hover {
  background: #dbeafe;
}

.onb-step-done-badge {
  font-size: 11px;
  font-weight: 700;
  color: #15803d;
  background: #f0fdf4;
  padding: 4px 8px;
  border-radius: 5px;
  white-space: nowrap;
  flex-shrink: 0;
}
</style>
