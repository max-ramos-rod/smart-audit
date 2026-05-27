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
const membership = computed(() => contextStore.context?.membership)
const stats = computed(() => contextStore.stats)

const PLAN_FEATURES: Record<string, string[]> = {
  starter:      ['Até 5 usuários', 'Até 10 formulários', 'Até 100 inspeções/mês', 'Suporte por email'],
  professional: ['Até 20 usuários', 'Formulários ilimitados', 'Até 500 inspeções/mês', 'Exportação PDF', 'Suporte prioritário'],
  enterprise:   ['Usuários ilimitados', 'Formulários ilimitados', 'Inspeções ilimitadas', 'API de integração', 'SLA garantido', 'Suporte dedicado'],
}

const features = computed(() => PLAN_FEATURES[company.value?.plan ?? 'starter'] ?? PLAN_FEATURES['starter'])
</script>

<template>
  <AppShell>
    <div class="page">

      <div class="phdr">
        <div>
          <div class="eyebrow">Administração</div>
          <h1 class="page-h1">Configurações da empresa</h1>
          <p class="page-desc">{{ company?.name }}</p>
        </div>
        <button class="btn-secondary" type="button" @click="router.back()">Voltar</button>
      </div>

      <!-- Tabs -->
      <div class="filter-tabs">
        <button class="filter-tab" :class="{ active: tab === 'general' }" @click="tab = 'general'" type="button">Geral</button>
        <button class="filter-tab" :class="{ active: tab === 'plan' }"    @click="tab = 'plan'"    type="button">Plano</button>
        <button class="filter-tab" :class="{ active: tab === 'usage' }"   @click="tab = 'usage'"   type="button">Utilização</button>
      </div>

      <!-- Geral -->
      <div v-if="tab === 'general'" class="card card-p">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--sa-muted);margin-bottom:16px;">Informações da empresa</div>
        <div style="display:grid;gap:14px;">
          <div class="field">
            <label class="flabel">Nome da empresa</label>
            <input :value="company?.name" disabled />
            <span style="font-size:11px;color:var(--sa-muted);">Para alterar o nome, entre em contato com o suporte.</span>
          </div>
          <div class="field">
            <label class="flabel">Plano</label>
            <input :value="company?.plan" disabled />
          </div>
          <div class="field">
            <label class="flabel">Seu papel</label>
            <input :value="membership?.role" disabled />
          </div>
        </div>
        <div style="margin-top:20px;height:1px;background:var(--sa-line);"></div>
        <div style="margin-top:16px;">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--sa-muted);margin-bottom:12px;">Trocar empresa</div>
          <button class="btn-secondary" type="button" @click="router.push({ name: 'select-company' })">
            Ir para seleção de empresa
          </button>
        </div>
      </div>

      <!-- Plano -->
      <div v-else-if="tab === 'plan'" style="display:flex;flex-direction:column;gap:12px;">
        <div class="card card-p" style="border-color:rgba(37,99,235,.3);background:var(--sa-brand-soft);">
          <div class="eyebrow" style="margin-bottom:4px;">Plano atual</div>
          <div style="font-size:24px;font-weight:800;color:var(--sa-text);letter-spacing:-.02em;text-transform:capitalize;">{{ company?.plan }}</div>
          <div style="font-size:13px;color:var(--sa-muted);margin-top:4px;">Renovação gerenciada pelo administrador da conta.</div>
        </div>
        <div class="card card-p">
          <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--sa-muted);margin-bottom:12px;">Funcionalidades incluídas</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div v-for="f in features" :key="f" style="display:flex;align-items:center;gap:8px;font-size:13px;color:var(--sa-text);">
              <span style="color:var(--sa-ok);font-weight:700;">✓</span>{{ f }}
            </div>
          </div>
        </div>
        <div style="text-align:center;padding:12px;font-size:13px;color:var(--sa-muted);">
          Para upgrade de plano, entre em contato com o suporte.
        </div>
      </div>

      <!-- Utilização -->
      <div v-else-if="tab === 'usage'" class="card card-p">
        <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--sa-muted);margin-bottom:16px;">Utilização atual</div>
        <div style="display:grid;gap:16px;">

          <div v-for="item in [
            { label: 'Total de inspeções', value: stats?.total_submissions ?? '—', desc: 'todas as inspeções criadas' },
            { label: 'Inspeções concluídas', value: stats?.completed ?? '—', desc: 'status completed' },
            { label: 'Formulários', value: formsStore.meta?.total ?? formsStore.items.length, desc: 'formulários cadastrados' },
            { label: 'Usuários ativos', value: usersStore.meta?.total ?? usersStore.items.length, desc: 'membros da empresa' },
          ]" :key="item.label">
            <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;">
              <span style="font-weight:600;color:var(--sa-text);">{{ item.label }}</span>
              <span style="color:var(--sa-muted);">{{ item.value }}</span>
            </div>
            <div style="height:4px;background:var(--sa-line);border-radius:99px;overflow:hidden;">
              <div style="height:100%;background:var(--sa-brand);border-radius:99px;width:40%;"></div>
            </div>
            <div style="font-size:11px;color:var(--sa-muted);margin-top:4px;">{{ item.desc }}</div>
          </div>

        </div>
      </div>

    </div>
  </AppShell>
</template>
