<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
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
    <section class="flex flex-wrap items-center justify-between gap-3 px-1">
      <div>
        <p class="eyebrow">Formulário</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-sa-text">
          {{ formDetail?.name ?? 'Carregando...' }}
        </h2>
        <p class="mt-2 text-sm text-sa-muted">Histórico de versões publicadas.</p>
      </div>
      <BaseButton type="button" variant="ghost" @click="router.push({ name: 'forms' })">
        Voltar
      </BaseButton>
    </section>

    <p v-if="formsStore.isLoadingVersions" class="text-sm text-sa-muted">Carregando versões...</p>

    <div v-else-if="formsStore.versions.length" class="surface-panel overflow-hidden">
      <table>
        <thead>
          <tr>
            <th>Versão</th>
            <th>Status</th>
            <th>Campos</th>
            <th>Publicado em</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="v in formsStore.versions" :key="v.id">
            <td class="font-semibold text-sa-text">v{{ v.version }}</td>
            <td>
              <span class="status-chip" :class="{ 'status-chip--inactive': v.status !== 'published' }">
                {{ v.status === 'published' ? 'Publicada' : v.status }}
              </span>
            </td>
            <td class="text-sa-muted">{{ v.fields_count }} campos</td>
            <td class="text-sa-muted">
              {{ v.published_at ? new Date(v.published_at).toLocaleDateString('pt-BR') : '—' }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="surface-panel p-6 text-center">
      <p class="eyebrow">Sem versões</p>
      <h3 class="mt-3 text-xl font-semibold text-sa-text">Nenhuma versão encontrada</h3>
    </div>
  </AppShell>
</template>
