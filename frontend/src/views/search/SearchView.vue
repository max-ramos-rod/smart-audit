<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { useFormsStore } from '@/stores/forms/forms.store'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'

const router = useRouter()
const formsStore = useFormsStore()
const submissionsStore = useSubmissionsStore()
const query = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

onMounted(async () => {
  inputRef.value?.focus()

  if (!formsStore.items.length) await formsStore.load(1, 100)
  if (!submissionsStore.items.length) await submissionsStore.load(1, 100)
})

const q = computed(() => query.value.toLowerCase().trim())

const matchedForms = computed(() =>
  q.value.length < 2
    ? []
    : formsStore.items.filter(
        (form) =>
          form.name.toLowerCase().includes(q.value) ||
          (form.description ?? '').toLowerCase().includes(q.value),
      ),
)

const matchedSubmissions = computed(() =>
  q.value.length < 2
    ? []
    : submissionsStore.items.filter((submission) => submission.form_name.toLowerCase().includes(q.value)),
)

const hasResults = computed(
  () => matchedForms.value.length > 0 || matchedSubmissions.value.length > 0,
)
const noResults = computed(() => q.value.length >= 2 && !hasResults.value)
const isEmpty = computed(() => q.value.length < 2)

const inProgressCount = computed(
  () => submissionsStore.items.filter((submission) => submission.status === 'in_progress').length,
)
const publishedFormsCount = computed(
  () => formsStore.items.filter((form) => form.is_active).length,
)

const recentSearches = ['Checklist NR-10', 'Auditoria ISO 9001', 'Inspecoes concluidas']

function applyRecent(term: string) {
  query.value = term
  inputRef.value?.focus()
}

function statusLabel(status: string) {
  return {
    in_progress: 'Em andamento',
    completed: 'Concluida',
    draft: 'Rascunho',
    cancelled: 'Cancelada',
  }[status] ?? status
}

function hoverIn(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement
  el.style.boxShadow = '0 4px 12px rgb(0 0 0/.1)'
  el.style.transform = 'translateY(-1px)'
}

function hoverOut(event: MouseEvent) {
  const el = event.currentTarget as HTMLElement
  el.style.boxShadow = ''
  el.style.transform = ''
}

function recentHoverIn(event: MouseEvent) {
  ;(event.currentTarget as HTMLElement).style.background = 'var(--sa-line)'
}

function recentHoverOut(event: MouseEvent) {
  ;(event.currentTarget as HTMLElement).style.background = 'var(--sa-bg)'
}
</script>

<template>
  <AppShell>
    <div class="page">
      <div class="phdr">
        <div>
          <p class="eyebrow">Ferramenta</p>
          <h1 class="page-h1">Busca rapida</h1>
          <p class="page-desc">Encontre formularios e inspecoes a partir dos dados ja carregados na sessao atual.</p>
        </div>
      </div>

      <div class="card card-p" style="position: sticky; top: 16px; z-index: 20; margin-bottom: 20px;">
        <div class="sbar" style="margin-bottom: 0;">
          <SvgIcon name="search" :size="16" style="color: var(--sa-muted); flex-shrink: 0;" />
          <input
            ref="inputRef"
            v-model="query"
            type="text"
            placeholder="Buscar formularios e inspecoes"
            style="border: none; outline: none; flex: 1; min-width: 0; padding: 0; box-shadow: none; font-size: 14px; background: transparent;"
          />
          <button
            v-if="query"
            type="button"
            @click="query = ''"
            style="border: none; background: none; cursor: pointer; color: var(--sa-muted); padding: 0; display: flex; align-items: center; justify-content: center;"
          >
            <SvgIcon name="close" :size="16" />
          </button>
        </div>
        <p class="page-desc" style="margin-top: 10px;">
          A busca atual e local e prioriza velocidade operacional. Uma busca indexada no backend fica para a proxima fase.
        </p>
      </div>

      <template v-if="isEmpty">
        <div class="users-layout">
          <div class="card card-p">
            <div class="slabel" style="margin-bottom: 12px;">Buscas recentes</div>
            <div style="display: flex; flex-direction: column; gap: 6px;">
              <button
                v-for="term in recentSearches"
                :key="term"
                type="button"
                @click="applyRecent(term)"
                style="display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: 8px; border: 1px solid var(--sa-line); background: var(--sa-bg); cursor: pointer; text-align: left; transition: background .15s;"
                @mouseenter="recentHoverIn"
                @mouseleave="recentHoverOut"
              >
                <SvgIcon name="search" :size="15" style="color: var(--sa-muted); flex-shrink: 0;" />
                <span style="font-size: 14px; color: var(--sa-text);">{{ term }}</span>
              </button>
            </div>
          </div>

          <div class="card card-p">
            <div class="slabel" style="margin-bottom: 12px;">Atalhos uteis</div>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
              <div
                class="card card-p"
                style="cursor: pointer; transition: box-shadow .15s, transform .1s;"
                @click="router.push({ name: 'submissions' })"
                @mouseenter="hoverIn"
                @mouseleave="hoverOut"
              >
                <div
                  style="font-size: 24px; font-weight: 800; color: var(--sa-brand); font-variant-numeric: tabular-nums; line-height: 1; margin-bottom: 4px;"
                >
                  {{ inProgressCount }}
                </div>
                <div style="font-size: 12px; font-weight: 600; color: var(--sa-muted);">Em andamento</div>
              </div>
              <div
                class="card card-p"
                style="cursor: pointer; transition: box-shadow .15s, transform .1s;"
                @click="router.push({ name: 'forms' })"
                @mouseenter="hoverIn"
                @mouseleave="hoverOut"
              >
                <div
                  style="font-size: 24px; font-weight: 800; color: var(--sa-brand); font-variant-numeric: tabular-nums; line-height: 1; margin-bottom: 4px;"
                >
                  {{ publishedFormsCount }}
                </div>
                <div style="font-size: 12px; font-weight: 600; color: var(--sa-muted);">Formularios ativos</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <div v-else-if="noResults" class="empty">
        <div class="empty-icon">
          <SvgIcon name="search" :size="36" />
        </div>
        <div class="empty-h">Nenhum resultado para "{{ query }}"</div>
        <p class="empty-p">Tente outro termo ou navegue pelos modulos para refinar a busca.</p>
      </div>

      <template v-else-if="hasResults">
        <div v-if="matchedForms.length" style="margin-bottom: 24px;">
          <div class="slabel" style="margin-bottom: 10px;">Formularios ({{ matchedForms.length }})</div>
          <div class="lstack">
            <div
              v-for="form in matchedForms"
              :key="form.id"
              class="lrow"
              @click="router.push({ name: 'form-detail', params: { formId: form.id } })"
            >
              <div class="lrow-main">
                <div class="lrow-title">{{ form.name }}</div>
                <div class="lrow-sub">v{{ form.current_version_number }} | {{ form.is_active ? 'Ativo' : 'Inativo' }}</div>
              </div>
              <div class="lrow-end">
                <span style="font-size: 18px; color: var(--sa-muted);">&gt;</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="matchedSubmissions.length">
          <div class="slabel" style="margin-bottom: 10px;">Inspecoes ({{ matchedSubmissions.length }})</div>
          <div class="lstack">
            <div
              v-for="submission in matchedSubmissions"
              :key="submission.id"
              class="lrow"
              @click="router.push({ name: 'submission-detail', params: { id: submission.id } })"
            >
              <div class="lrow-main">
                <div class="lrow-title">{{ submission.form_name }}</div>
                <div class="lrow-sub">
                  {{ statusLabel(submission.status) }} | {{ new Date(submission.started_at).toLocaleDateString('pt-BR') }}
                </div>
              </div>
              <div class="lrow-end">
                <span
                  v-if="submission.score !== null"
                  class="score-val"
                  :class="submission.score >= 85 ? 'ok' : submission.score >= 65 ? 'warn' : 'err'"
                  style="margin-right: 6px;"
                >
                  {{ submission.score }}%
                </span>
                <span style="font-size: 18px; color: var(--sa-muted);">&gt;</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  </AppShell>
</template>
