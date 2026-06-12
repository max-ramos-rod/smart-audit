<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import InspectionComposer from '@/components/submissions/InspectionComposer.vue'
import { exportSubmissionsCSV } from '@/services/submissions.service'
import { scoreClass } from '@/utils/score'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'

const router = useRouter()
const submissionsStore = useSubmissionsStore()

const showComposer = ref(false)

const currentPage = ref(1)
const activeStatus = ref<string | undefined>(undefined)
const isExporting = ref(false)

async function handleExportCSV() {
  isExporting.value = true
  try {
    await exportSubmissionsCSV(activeStatus.value)
  } finally {
    isExporting.value = false
  }
}

const STATUS_OPTIONS = [
  { label: 'Todas', value: undefined },
  { label: 'Em andamento', value: 'in_progress' },
  { label: 'Concluídas', value: 'completed' },
] as const

async function loadPage(page: number, status?: string) {
  currentPage.value = page
  await submissionsStore.load(page, 20, status)
}

async function setStatus(status: string | undefined) {
  activeStatus.value = status
  await loadPage(1, status)
}

onMounted(() => {
  loadPage(1)
})

function openComposer() {
  showComposer.value = true
}

function closeComposer() {
  showComposer.value = false
}

async function onInspectionCreated(submissionId: string) {
  closeComposer()
  await loadPage(1)
  router.push({ name: 'submission-detail', params: { id: submissionId } })
}

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
          <p class="eyebrow">Execução</p>
          <h2 class="page-h1">Inspeções</h2>
          <p class="page-desc">Acompanhe status, início de execução e score operacional.</p>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <button
            type="button"
            class="btn-secondary btn-sm"
            :disabled="isExporting"
            @click="handleExportCSV"
          >
            {{ isExporting ? 'Exportando...' : 'Exportar CSV' }}
          </button>
          <button type="button" class="btn-primary" @click="openComposer">Nova inspeção</button>
        </div>
      </div>

      <!-- composer (wizard extraído — Sprint 2) -->
      <div v-if="showComposer" class="card card-p" style="margin-bottom:16px;">
        <InspectionComposer @created="onInspectionCreated" @close="closeComposer" />
      </div>

      <p v-if="submissionsStore.error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:8px;">
        {{ submissionsStore.error }}
      </p>
      <p v-else-if="submissionsStore.isLoading" style="font-size:13px;color:var(--sa-muted);margin-bottom:8px;">
        Carregando inspeções...
      </p>

      <!-- filter tabs -->
      <div class="filter-tabs">
        <button
          v-for="opt in STATUS_OPTIONS"
          :key="String(opt.value)"
          type="button"
          class="filter-tab"
          :class="{ active: activeStatus === opt.value }"
          @click="setStatus(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>

      <!-- list -->
      <div v-if="submissionsStore.items.length" class="lstack">
        <div
          v-for="submission in submissionsStore.items"
          :key="submission.id"
          class="lrow"
          @click="router.push({ name: 'submission-detail', params: { id: submission.id } })"
        >
          <div class="lrow-main">
            <div class="lrow-title">{{ submission.form_name }}</div>
            <div class="lrow-sub">
              <span v-if="submission.asset_identifier">🏷 {{ submission.asset_identifier }} · </span>
              {{ submission.finished_at
                ? 'Concluída ' + new Date(submission.finished_at).toLocaleString('pt-BR')
                : 'Início ' + new Date(submission.started_at).toLocaleString('pt-BR') }}
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

      <div v-else-if="!submissionsStore.isLoading" class="empty">
        <div class="empty-h">Nenhuma inspeção registrada</div>
        <p class="empty-p">Clique em "Nova inspeção" para iniciar a partir de um formulário cadastrado.</p>
      </div>

      <nav
        v-if="submissionsStore.meta && submissionsStore.meta.total_pages > 1"
        style="display:flex;align-items:center;justify-content:center;gap:16px;margin-top:16px;"
      >
        <button
          type="button"
          class="btn-secondary btn-sm"
          :disabled="currentPage <= 1 || submissionsStore.isLoading"
          @click="loadPage(currentPage - 1, activeStatus)"
        >
          ← Anterior
        </button>
        <span style="font-size:13px;color:var(--sa-muted);">
          Página {{ currentPage }} de {{ submissionsStore.meta.total_pages }}
        </span>
        <button
          type="button"
          class="btn-secondary btn-sm"
          :disabled="!submissionsStore.meta.has_next || submissionsStore.isLoading"
          @click="loadPage(currentPage + 1, activeStatus)"
        >
          Próxima →
        </button>
      </nav>

    </div>
  </AppShell>
</template>
