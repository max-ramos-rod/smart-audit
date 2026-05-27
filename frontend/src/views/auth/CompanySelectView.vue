<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import SvgIcon from '@/components/ui/SvgIcon.vue'
import { useContextStore } from '@/stores/context/context.store'

const router = useRouter()
const contextStore = useContextStore()

const selecting = ref<string | null>(null)
const error = ref<string | null>(null)

const companies = computed(() => contextStore.context?.available_companies ?? [])
const activeCompanyId = computed(
  () => contextStore.context?.active_company?.id ?? contextStore.selectedCompanyId,
)
const stats = computed(() => contextStore.stats)

onMounted(async () => {
  if (!contextStore.stats) await contextStore.loadStats()
})

function cardHoverIn(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement
  el.style.boxShadow = '0 4px 12px rgb(0 0 0/.12)'
  el.style.transform = 'translateY(-1px)'
}

function cardHoverOut(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement
  el.style.boxShadow = ''
  el.style.transform = ''
}

async function handleSelect(companyId: string) {
  selecting.value = companyId
  error.value = null

  try {
    await contextStore.selectCompany(companyId)
    await contextStore.loadStats()
    router.push({ name: 'home' })
  } catch {
    error.value = 'Nao foi possivel selecionar a empresa. Tente novamente.'
    selecting.value = null
  }
}
</script>

<template>
  <div style="min-height: 100dvh; background: var(--sa-bg); display: flex; flex-direction: column;">
    <div
      style="background: var(--sa-nav); padding: 18px 24px; display: flex; align-items: center; justify-content: space-between;"
    >
      <div style="display: flex; align-items: center; gap: 10px;">
        <div
          style="width: 30px; height: 30px; background: var(--sa-brand); border-radius: 7px; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; color: #fff;"
        >
          SA
        </div>
        <div style="font-size: 14px; font-weight: 700; color: #fff;">Smart Audit</div>
      </div>
      <RouterLink
        to="/login"
        style="font-size: 12px; font-weight: 600; color: rgba(255,255,255,.4); text-decoration: none; display: flex; align-items: center; gap: 6px;"
        @click.prevent="() => { contextStore.reset(); router.push({ name: 'login' }) }"
      >
        <SvgIcon name="logout" />Sair
      </RouterLink>
    </div>

    <div style="flex: 1; display: flex; align-items: flex-start; justify-content: center; padding: 40px 16px;">
      <div style="width: 100%; max-width: 560px;">
        <div style="margin-bottom: 28px;">
          <div class="eyebrow" style="margin-bottom: 4px;">Acesso multiempresa</div>
          <h1
            style="font-size: clamp(1.4rem, 3vw, 2rem); font-weight: 700; letter-spacing: -.02em; color: var(--sa-text); margin-bottom: 6px;"
          >
            Selecione a empresa
          </h1>
          <p style="font-size: 13px; color: var(--sa-muted);">
            Voce tem acesso a {{ companies.length }} empresa{{ companies.length !== 1 ? 's' : '' }}.
            Escolha com qual deseja operar.
          </p>
        </div>

        <div style="display: flex; flex-direction: column; gap: 10px;">
          <div
            v-for="company in companies"
            :key="company.id"
            class="card"
            style="padding: 18px 20px; cursor: pointer; transition: box-shadow .15s, transform .1s; position: relative;"
            :style="{
              opacity: selecting !== null && selecting !== company.id ? 0.6 : 1,
              borderColor: company.id === activeCompanyId ? 'var(--sa-brand)' : 'var(--sa-line)',
              borderWidth: company.id === activeCompanyId ? '2px' : '1px',
            }"
            @click="handleSelect(company.id)"
            @mouseenter="cardHoverIn"
            @mouseleave="cardHoverOut"
          >
            <div style="display: flex; align-items: flex-start; gap: 14px;">
              <div
                style="width: 42px; height: 42px; border-radius: 10px; flex-shrink: 0; background: var(--sa-brand-soft); display: flex; align-items: center; justify-content: center; color: var(--sa-brand); font-weight: 800; font-size: 16px;"
              >
                SA
              </div>

              <div style="flex: 1; min-width: 0;">
                <div style="font-size: 15px; font-weight: 700; color: var(--sa-text); margin-bottom: 6px;">
                  {{ company.name }}
                </div>
                <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px;">
                  <span class="role-badge" :class="'role-' + company.role.toLowerCase()">{{ company.role }}</span>
                  <span
                    style="font-size: 10px; font-weight: 600; color: var(--sa-muted); background: var(--sa-bg); padding: 2px 7px; border-radius: 4px; text-transform: uppercase; letter-spacing: .06em;"
                  >
                    {{ company.plan }}
                  </span>
                </div>
                <div style="display: flex; gap: 20px; font-size: 12px; color: var(--sa-muted);">
                  <span>
                    <strong style="color: var(--sa-text); font-variant-numeric: tabular-nums;">
                      {{ company.id === activeCompanyId && stats ? stats.total_submissions : '-' }}
                    </strong>
                    inspecoes
                  </span>
                </div>
              </div>

              <div style="flex-shrink: 0; display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
                <div
                  v-if="company.id === activeCompanyId"
                  style="font-size: 10px; font-weight: 700; color: var(--sa-brand); background: var(--sa-brand-soft); padding: 2px 7px; border-radius: 4px; letter-spacing: .06em; text-transform: uppercase;"
                >
                  Ativa
                </div>
                <div style="color: var(--sa-muted); font-size: 18px; line-height: 1;">
                  {{ selecting === company.id ? '...' : '>' }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <p v-if="error" style="margin-top: 16px; font-size: 13px; font-weight: 600; color: var(--sa-danger); text-align: center;">
          {{ error }}
        </p>

        <p style="margin-top: 24px; font-size: 12px; color: var(--sa-muted); text-align: center;">
          Para solicitar acesso a uma nova empresa, contate o administrador.
        </p>
      </div>
    </div>
  </div>
</template>
