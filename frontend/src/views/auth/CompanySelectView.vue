<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import BaseButton from '@/components/ui/BaseButton.vue'
import { useContextStore } from '@/stores/context/context.store'

const router = useRouter()
const contextStore = useContextStore()

const selecting = ref<string | null>(null)
const error = ref<string | null>(null)

const companies = computed(() => contextStore.context?.available_companies ?? [])

async function handleSelect(companyId: string) {
  selecting.value = companyId
  error.value = null
  try {
    await contextStore.selectCompany(companyId)
    await contextStore.loadStats()
    router.push({ name: 'home' })
  } catch {
    error.value = 'Não foi possível selecionar a empresa. Tente novamente.'
    selecting.value = null
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-[color:var(--sa-bg)] p-4">
    <div class="w-full max-w-lg space-y-6">
      <div class="space-y-2 text-center">
        <p class="eyebrow">Smart Audit</p>
        <h1 class="text-2xl font-semibold tracking-tight text-sa-text sm:text-3xl">
          Selecione uma empresa
        </h1>
        <p class="muted-copy text-base">
          Sua conta está vinculada a mais de uma empresa. Escolha com qual deseja operar.
        </p>
      </div>

      <div class="grid gap-3">
        <article
          v-for="company in companies"
          :key="company.id"
          class="surface-panel flex items-center justify-between gap-4 p-4"
        >
          <div class="min-w-0">
            <p class="truncate font-semibold text-sa-text">{{ company.name }}</p>
            <p class="mt-0.5 text-sm text-sa-muted">
              {{ company.role }} &middot; plano {{ company.plan }}
            </p>
          </div>
          <BaseButton
            type="button"
            :disabled="selecting !== null"
            @click="handleSelect(company.id)"
          >
            {{ selecting === company.id ? 'Selecionando...' : 'Selecionar' }}
          </BaseButton>
        </article>
      </div>

      <p v-if="error" class="text-center text-sm font-medium text-sa-danger">{{ error }}</p>
    </div>
  </div>
</template>
