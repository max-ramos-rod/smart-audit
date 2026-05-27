<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { fetchMyCompany, updateMyCompany } from '@/services/companies.service'
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

const canEdit = computed(() =>
  ['OWNER', 'ADMIN'].includes(contextStore.context?.membership?.role ?? ''),
)

const form = reactive({
  name: '',
  cnpj: '',
  timezone: 'America/Sao_Paulo',
  contact_email: '',
  phone: '',
})

const isSaving = ref(false)
const savedOnce = ref(false)
const saveError = ref<string | null>(null)

onMounted(async () => {
  try {
    const data = await fetchMyCompany()
    form.name = data.name
    form.cnpj = data.cnpj ?? ''
    form.timezone = data.timezone ?? 'America/Sao_Paulo'
    form.contact_email = data.contact_email ?? ''
    form.phone = data.phone ?? ''
  } catch {
    form.name = company.value?.name ?? ''
  }
})

async function handleSave() {
  isSaving.value = true
  saveError.value = null
  savedOnce.value = false
  try {
    await updateMyCompany({
      name: form.name || undefined,
      cnpj: form.cnpj || undefined,
      timezone: form.timezone || undefined,
      contact_email: form.contact_email || undefined,
      phone: form.phone || undefined,
    })
    savedOnce.value = true
  } catch (err: any) {
    saveError.value = err.response?.data?.detail ?? 'Erro ao salvar configurações.'
  } finally {
    isSaving.value = false
  }
}

const planFeatures = [
  'Usuários ilimitados',
  'Formulários ilimitados',
  'Relatórios exportáveis (PDF/CSV)',
  'Evidências fotográficas',
  'API de integração',
  'Suporte prioritário',
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
    label: 'Usuários ativos',
    used: usersStore.meta?.total ?? usersStore.items.length,
    total: 50,
  },
  {
    label: 'Inspeções neste mês',
    used: stats.value?.total_submissions ?? submissionsStore.items.length,
    total: 500,
  },
  {
    label: 'Formulários',
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
          <div class="eyebrow">Administração</div>
          <h1 class="page-h1">Configurações da empresa</h1>
          <p class="page-desc">{{ company?.name }}</p>
        </div>
        <button class="btn-secondary" type="button" @click="router.back()">Voltar</button>
      </div>

      <div class="filter-tabs">
        <button class="filter-tab" :class="{ active: tab === 'general' }" type="button" @click="tab = 'general'">
          Geral
        </button>
        <button class="filter-tab" :class="{ active: tab === 'plan' }" type="button" @click="tab = 'plan'">
          Plano
        </button>
        <button class="filter-tab" :class="{ active: tab === 'usage' }" type="button" @click="tab = 'usage'">
          Utilização
        </button>
      </div>

      <!-- Geral -->
      <div v-if="tab === 'general'" class="card card-p">
        <div class="slabel" style="margin-bottom: 16px;">Informações da empresa</div>
        <div style="display: grid; gap: 12px;">
          <div class="field">
            <label class="flabel">Nome da empresa</label>
            <input v-model="form.name" :disabled="!canEdit" />
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <div class="field">
              <label class="flabel">CNPJ</label>
              <input v-model="form.cnpj" :disabled="!canEdit" placeholder="00.000.000/0000-00" />
            </div>
            <div class="field">
              <label class="flabel">Fuso horario</label>
              <select v-model="form.timezone" :disabled="!canEdit">
                <option value="America/Sao_Paulo">America/Sao_Paulo</option>
                <option value="America/Belem">America/Belem</option>
                <option value="America/Manaus">America/Manaus</option>
                <option value="America/Fortaleza">America/Fortaleza</option>
                <option value="America/Recife">America/Recife</option>
                <option value="America/Cuiaba">America/Cuiaba</option>
                <option value="America/Porto_Velho">America/Porto_Velho</option>
                <option value="America/Boa_Vista">America/Boa_Vista</option>
                <option value="America/Rio_Branco">America/Rio_Branco</option>
                <option value="America/Noronha">America/Noronha</option>
              </select>
            </div>
          </div>

          <div class="field">
            <label class="flabel">E-mail de contato</label>
            <input v-model="form.contact_email" type="email" :disabled="!canEdit" />
          </div>

          <div class="field">
            <label class="flabel">Telefone</label>
            <input v-model="form.phone" type="tel" :disabled="!canEdit" />
          </div>

          <div v-if="!canEdit" style="font-size: 12px; color: var(--sa-muted); padding: 8px 10px; background: var(--sa-warn-bg); border: 1px solid var(--sa-warn-bd, #fde68a); border-radius: 6px;">
            Apenas OWNER e ADMIN podem editar os dados da empresa.
          </div>

          <div v-if="canEdit" style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
            <button
              type="button"
              class="btn-primary btn-sm"
              :disabled="isSaving"
              @click="handleSave"
            >
              {{ isSaving ? 'Salvando...' : 'Salvar alterações' }}
            </button>
            <span v-if="savedOnce" style="font-size: 13px; font-weight: 600; color: var(--sa-ok);">
              ✓ Configurações salvas.
            </span>
            <span v-if="saveError" style="font-size: 13px; font-weight: 600; color: var(--sa-danger);">
              {{ saveError }}
            </span>
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
              Ação irreversível. Ainda não existe fluxo funcional exposto na interface.
            </div>
          </div>
          <button type="button" class="btn-secondary btn-sm" disabled>Indisponivel</button>
        </div>
      </div>

      <!-- Plano -->
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
                Visualização do plano atual. Gestão comercial e billing ainda não foram expostos na interface.
              </div>
            </div>
            <span class="status-chip">Ativo</span>
          </div>
        </div>

        <div class="card card-p">
          <div class="slabel" style="margin-bottom: 12px;">Funcionalidades incluídas</div>
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

      <!-- Utilização -->
      <div v-else-if="tab === 'usage'" class="card card-p">
        <div class="slabel" style="margin-bottom: 16px;">Utilização do plano</div>

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
