<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { useContextStore } from '@/stores/context/context.store'
import { useFormsStore } from '@/stores/forms/forms.store'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
import { useUsersStore } from '@/stores/users/users.store'

const router = useRouter()
const contextStore = useContextStore()
const formsStore = useFormsStore()
const submissionsStore = useSubmissionsStore()
const usersStore = useUsersStore()

const tab = ref<'general' | 'plan' | 'usage'>('general')

const company = computed(() => contextStore.activeCompany)
const stats = computed(() => contextStore.stats)

const planFeatures = [
  'Usuarios ilimitados',
  'Formularios ilimitados',
  'Relatorios exportaveis (PDF/CSV)',
  'Evidencias fotograficas',
  'API de integracao',
  'Suporte prioritario',
  'Multiempresa',
  'SLA garantido',
]

interface UsageItem {
  label: string
  used: number
  total: number
  unit?: string
}

const usageItems = computed<UsageItem[]>(() => [
  {
    label: 'Usuarios ativos',
    used: usersStore.meta?.total ?? usersStore.items.length,
    total: 50,
  },
  {
    label: 'Inspecoes neste mes',
    used: stats.value?.total_submissions ?? submissionsStore.items.length,
    total: 500,
  },
  {
    label: 'Formularios',
    used: formsStore.meta?.total ?? formsStore.items.length,
    total: 100,
  },
])

function usagePct(item: UsageItem) {
  return Math.min(100, Math.round((item.used / item.total) * 100))
}

function usageColor(pct: number) {
  return pct >= 90 ? 'var(--sa-danger)' : pct >= 70 ? 'var(--sa-warn)' : 'var(--sa-ok)'
}
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="phdr">
        <div>
          <div class="eyebrow">Administracao</div>
          <h1 class="page-h1">Configuracoes da empresa</h1>
          <p class="page-desc">{{ company?.name }}</p>
        </div>
        <button class="btn-secondary" type="button" @click="router.back()">Voltar</button>
      </div>

      <div class="info-box" style="margin-bottom: 16px;">
        Esta area ja ajuda na operacao, mas ainda nao representa um modulo administrativo completo da empresa.
        Os blocos abaixo deixam claro o que ja e informativo hoje e o que ainda depende de backend dedicado.
      </div>

      <div class="filter-tabs">
        <button class="filter-tab" :class="{ active: tab === 'general' }" type="button" @click="tab = 'general'">
          Geral
        </button>
        <button class="filter-tab" :class="{ active: tab === 'plan' }" type="button" @click="tab = 'plan'">
          Plano
        </button>
        <button class="filter-tab" :class="{ active: tab === 'usage' }" type="button" @click="tab = 'usage'">
          Utilizacao
        </button>
      </div>

      <div v-if="tab === 'general'" class="card card-p">
        <div class="slabel" style="margin-bottom: 16px;">Informacoes da empresa</div>
        <div style="display: grid; gap: 12px;">
          <div class="field">
            <label class="flabel">Nome da empresa</label>
            <input :value="company?.name" disabled />
            <span style="font-size: 11px; color: var(--sa-muted);">
              Dado exibido a partir do contexto ativo. A edicao administrativa ainda nao esta disponivel nesta tela.
            </span>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div class="field">
              <label class="flabel">CNPJ</label>
              <input value="Disponivel em breve" disabled />
            </div>
            <div class="field">
              <label class="flabel">Fuso horario</label>
              <select disabled>
                <option>America/Sao_Paulo</option>
                <option>America/Belem</option>
                <option>America/Manaus</option>
              </select>
            </div>
          </div>

          <div class="field">
            <label class="flabel">E-mail de contato</label>
            <input type="email" value="Disponivel em breve" disabled />
          </div>

          <div class="field">
            <label class="flabel">Telefone</label>
            <input type="tel" value="Disponivel em breve" disabled />
          </div>

          <div
            style="font-size: 12px; color: var(--sa-muted); padding: 8px 10px; background: var(--sa-warn-bg); border: 1px solid var(--sa-warn-bd, #fde68a); border-radius: 6px;"
          >
            A edicao dos dados institucionais sera habilitada junto do modulo administrativo completo.
          </div>
        </div>

        <div style="height: 1px; background: var(--sa-line); margin: 20px 0;"></div>

        <div class="slabel" style="margin-bottom: 12px;">Zona de risco</div>
        <div
          style="display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; background: var(--sa-err-bg); border: 1px solid var(--sa-err-bd, #fecaca); border-radius: 8px;"
        >
          <div>
            <div style="font-size: 13px; font-weight: 700; color: var(--sa-danger);">Excluir empresa</div>
            <div style="font-size: 12px; color: var(--sa-danger); opacity: .7;">
              Acao irreversivel. Ainda nao existe fluxo funcional exposto na interface.
            </div>
          </div>
          <button type="button" class="btn-secondary btn-sm" disabled>Indisponivel</button>
        </div>
      </div>

      <div v-else-if="tab === 'plan'" style="display: flex; flex-direction: column; gap: 12px;">
        <div class="card card-p" style="border-color: rgba(37,99,235,.3); background: var(--sa-brand-soft);">
          <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;">
            <div>
              <div class="eyebrow" style="margin-bottom: 4px;">Plano atual</div>
              <div
                style="font-size: 24px; font-weight: 800; color: var(--sa-text); letter-spacing: -.02em; text-transform: capitalize;"
              >
                {{ company?.plan ?? 'starter' }}
              </div>
              <div style="font-size: 13px; color: var(--sa-muted); margin-top: 4px;">
                Visualizacao do plano atual. Gestao comercial e billing ainda nao foram expostos na interface.
              </div>
            </div>
            <span class="status-chip">Ativo</span>
          </div>
        </div>

        <div class="card card-p">
          <div class="slabel" style="margin-bottom: 12px;">Funcionalidades incluidas</div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <div
              v-for="feature in planFeatures"
              :key="feature"
              style="display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--sa-text);"
            >
              <span style="color: var(--sa-ok); font-weight: 700;">OK</span>{{ feature }}
            </div>
          </div>
        </div>

        <div
          style="padding: 14px 16px; background: var(--sa-bg); border: 1px solid var(--sa-line); border-radius: 12px; text-align: center;"
        >
          <div style="font-size: 13px; color: var(--sa-muted); margin-bottom: 10px;">
            Precisa de mais recursos ou usuarios?
          </div>
          <button type="button" class="btn-secondary">Falar com o comercial</button>
        </div>
      </div>

      <div v-else-if="tab === 'usage'" class="card card-p">
        <div class="slabel" style="margin-bottom: 16px;">Utilizacao do plano</div>

        <div v-for="item in usageItems" :key="item.label" style="margin-bottom: 16px;">
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 6px;">
            <span style="font-weight: 600; color: var(--sa-text);">{{ item.label }}</span>
            <span style="color: var(--sa-muted); font-variant-numeric: tabular-nums;">
              {{ item.used }}{{ item.unit ?? '' }}
              <span style="opacity: .6;">/ {{ item.total }}{{ item.unit ?? '' }}</span>
            </span>
          </div>
          <div style="height: 4px; background: var(--sa-line); border-radius: 99px; overflow: hidden;">
            <div
              :style="{
                height: '100%',
                borderRadius: '99px',
                width: usagePct(item) + '%',
                background: usageColor(usagePct(item)),
                transition: 'width .4s',
              }"
            ></div>
          </div>
          <div style="font-size: 11px; color: var(--sa-muted); margin-top: 4px;">
            {{ usagePct(item) }}% utilizado
          </div>
        </div>

        <div style="font-size: 12px; color: var(--sa-muted); margin-top: 8px;">
          Dados exibidos a partir da sessao atual e atualizados conforme os modulos carregados.
        </div>
      </div>
    </div>
  </AppShell>
</template>
