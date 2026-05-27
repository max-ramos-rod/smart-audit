<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import { fetchForm } from '@/services/forms.service'
import { useFormsStore } from '@/stores/forms/forms.store'
import type { FormDetail } from '@/types/forms'

const route = useRoute()
const router = useRouter()
const formsStore = useFormsStore()
const formId = computed(() => route.params.formId as string)
const formDetail = ref<FormDetail | null>(null)

onMounted(async () => {
  await formsStore.loadVersions(formId.value)
  formDetail.value = await fetchForm(formId.value)
})
</script>

<template>
  <AppShell>
    <div class="page">

      <div class="phdr">
        <div>
          <p class="eyebrow">Formulário</p>
          <h2 class="page-h1">{{ formDetail?.name ?? 'Carregando...' }}</h2>
          <p class="page-desc">Histórico de versões publicadas.</p>
        </div>
        <button type="button" class="btn-secondary btn-sm" @click="router.push({ name: 'forms' })">
          ← Voltar
        </button>
      </div>

      <p v-if="formsStore.isLoadingVersions" class="text-sm text-sa-muted">Carregando versões...</p>

      <div v-else-if="formsStore.versions.length" class="lstack">
        <div
          v-for="v in formsStore.versions"
          :key="v.id"
          class="lrow"
          style="cursor: default;"
          :style="v.status === 'published' && v.version === formsStore.versions[0]?.version
            ? 'border-color: var(--sa-brand);'
            : ''"
        >
          <div class="lrow-main">
            <div class="lrow-title" style="display: flex; align-items: center; gap: 8px;">
              <span class="ver-badge">v{{ v.version }}</span>
              <span>{{ v.fields_count }} campos</span>
            </div>
            <div class="lrow-sub">
              {{ v.published_at ? 'Publicada em ' + new Date(v.published_at).toLocaleDateString('pt-BR') : 'Não publicada' }}
            </div>
          </div>
          <div class="lrow-end">
            <span
              class="status-chip"
              :class="{ 'status-chip--inactive': v.status !== 'published' }"
            >
              {{ v.status === 'published' ? 'Publicada' : v.status }}
            </span>
          </div>
        </div>
      </div>

      <div v-else class="surface-panel p-6 text-center">
        <p class="eyebrow">Sem versões</p>
        <h3 class="mt-3 text-xl font-semibold text-sa-text">Nenhuma versão encontrada</h3>
      </div>

    </div>
  </AppShell>
</template>
