<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

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
  q.value.length < 2 ? [] :
  formsStore.items.filter(f =>
    f.name.toLowerCase().includes(q.value) ||
    (f.description ?? '').toLowerCase().includes(q.value)
  )
)

const matchedSubmissions = computed(() =>
  q.value.length < 2 ? [] :
  submissionsStore.items.filter(s =>
    s.form_name.toLowerCase().includes(q.value)
  )
)

const hasResults = computed(() => matchedForms.value.length > 0 || matchedSubmissions.value.length > 0)
const noResults  = computed(() => q.value.length >= 2 && !hasResults.value)
const isEmpty    = computed(() => q.value.length < 2)

const inProgressCount = computed(() =>
  submissionsStore.items.filter(s => s.status === 'in_progress').length
)
const publishedFormsCount = computed(() =>
  formsStore.items.filter(f => f.is_active).length
)

const recentSearches = ['Checklist NR-10', 'Auditoria ISO 9001', 'Inspeções concluídas']

function applyRecent(term: string) {
  query.value = term
  inputRef.value?.focus()
}

function statusLabel(status: string) {
  return { in_progress: 'Em andamento', completed: 'Concluída', draft: 'Rascunho', cancelled: 'Cancelada' }[status] ?? status
}

function hoverIn(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement
  el.style.boxShadow = '0 4px 12px rgb(0 0 0/.1)'
  el.style.transform = 'translateY(-1px)'
}
function hoverOut(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement
  el.style.boxShadow = ''
  el.style.transform = ''
}
function recentHoverIn(e: MouseEvent) {
  (e.currentTarget as HTMLElement).style.background = 'var(--sa-line)'
}
function recentHoverOut(e: MouseEvent) {
  (e.currentTarget as HTMLElement).style.background = 'var(--sa-surface, var(--sa-bg))'
}
</script>

<template>
  <div style="min-height:100dvh;background:var(--sa-bg);display:flex;flex-direction:column;">

    <!-- Sticky header -->
    <div style="position:sticky;top:0;z-index:100;background:var(--sa-bg);border-bottom:1px solid var(--sa-line);padding:10px 16px;display:flex;align-items:center;gap:10px;">
      <button
        type="button"
        @click="router.back()"
        style="width:34px;height:34px;border-radius:8px;border:1px solid var(--sa-line);background:var(--sa-surface, var(--sa-bg));display:flex;align-items:center;justify-content:center;cursor:pointer;color:var(--sa-text);flex-shrink:0;"
      >
        <SvgIcon name="back" :size="18" />
      </button>

      <div class="sbar" style="flex:1;margin-bottom:0;">
        <SvgIcon name="search" :size="16" style="color:var(--sa-muted);flex-shrink:0;" />
        <input
          ref="inputRef"
          v-model="query"
          type="text"
          placeholder="Buscar formulários, inspeções..."
          style="border:none;outline:none;flex:1;min-width:0;padding:0;box-shadow:none;font-size:14px;background:transparent;"
        />
        <button
          v-if="query"
          type="button"
          @click="query = ''"
          style="border:none;background:none;cursor:pointer;color:var(--sa-muted);padding:0;display:flex;align-items:center;justify-content:center;"
        >
          <SvgIcon name="close" :size="16" />
        </button>
      </div>
    </div>

    <!-- Body -->
    <div style="flex:1;padding:20px 16px;max-width:720px;width:100%;margin:0 auto;box-sizing:border-box;">

      <!-- Empty state: recent + quick access -->
      <template v-if="isEmpty">
        <!-- Buscas recentes -->
        <div style="margin-bottom:28px;">
          <div class="slabel" style="margin-bottom:12px;">Buscas recentes</div>
          <div style="display:flex;flex-direction:column;gap:6px;">
            <button
              v-for="term in recentSearches"
              :key="term"
              type="button"
              @click="applyRecent(term)"
              style="display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:8px;border:1px solid var(--sa-line);background:var(--sa-surface, var(--sa-bg));cursor:pointer;text-align:left;transition:background .15s;"
              @mouseenter="recentHoverIn"
              @mouseleave="recentHoverOut"
            >
              <SvgIcon name="search" :size="15" style="color:var(--sa-muted);flex-shrink:0;" />
              <span style="font-size:14px;color:var(--sa-text);">{{ term }}</span>
            </button>
          </div>
        </div>

        <!-- Acesso rápido -->
        <div>
          <div class="slabel" style="margin-bottom:12px;">Acesso rápido</div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div
              class="card card-p"
              style="cursor:pointer;transition:box-shadow .15s,transform .1s;"
              @click="router.push({ name: 'submissions' })"
              @mouseenter="hoverIn"
              @mouseleave="hoverOut"
            >
              <div style="font-size:24px;font-weight:800;color:var(--sa-brand);font-variant-numeric:tabular-nums;line-height:1;margin-bottom:4px;">
                {{ inProgressCount }}
              </div>
              <div style="font-size:12px;font-weight:600;color:var(--sa-muted);">Em andamento</div>
            </div>
            <div
              class="card card-p"
              style="cursor:pointer;transition:box-shadow .15s,transform .1s;"
              @click="router.push({ name: 'forms' })"
              @mouseenter="hoverIn"
              @mouseleave="hoverOut"
            >
              <div style="font-size:24px;font-weight:800;color:var(--sa-brand);font-variant-numeric:tabular-nums;line-height:1;margin-bottom:4px;">
                {{ publishedFormsCount }}
              </div>
              <div style="font-size:12px;font-weight:600;color:var(--sa-muted);">Formulários ativos</div>
            </div>
          </div>
        </div>
      </template>

      <!-- No results -->
      <div v-else-if="noResults" style="text-align:center;padding:48px 0;">
        <div style="width:48px;height:48px;margin:0 auto 16px;color:var(--sa-muted);">
          <SvgIcon name="search" :size="48" />
        </div>
        <div style="font-size:15px;font-weight:600;color:var(--sa-text);margin-bottom:6px;">Nenhum resultado para "{{ query }}"</div>
        <div style="font-size:13px;color:var(--sa-muted);">Tente outros termos</div>
      </div>

      <!-- Results -->
      <template v-else-if="hasResults">

        <!-- Forms -->
        <div v-if="matchedForms.length" style="margin-bottom:24px;">
          <div class="slabel" style="margin-bottom:10px;">Formulários ({{ matchedForms.length }})</div>
          <div class="lstack">
            <div
              v-for="form in matchedForms"
              :key="form.id"
              class="lrow"
              @click="router.push({ name: 'forms' })"
            >
              <div class="lrow-main">
                <div class="lrow-title">{{ form.name }}</div>
                <div class="lrow-sub">v{{ form.current_version_number }} · {{ form.is_active ? 'Ativo' : 'Inativo' }}</div>
              </div>
              <div class="lrow-end">
                <span style="font-size:18px;color:var(--sa-muted);">›</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Submissions -->
        <div v-if="matchedSubmissions.length">
          <div class="slabel" style="margin-bottom:10px;">Inspeções ({{ matchedSubmissions.length }})</div>
          <div class="lstack">
            <div
              v-for="s in matchedSubmissions"
              :key="s.id"
              class="lrow"
              @click="router.push({ name: 'submission-detail', params: { id: s.id } })"
            >
              <div class="lrow-main">
                <div class="lrow-title">{{ s.form_name }}</div>
                <div class="lrow-sub">{{ statusLabel(s.status) }} · {{ new Date(s.started_at).toLocaleDateString('pt-BR') }}</div>
              </div>
              <div class="lrow-end">
                <span v-if="s.score !== null" class="score-val" :class="s.score >= 85 ? 'ok' : s.score >= 65 ? 'warn' : 'err'" style="margin-right:6px;">{{ s.score }}%</span>
                <span style="font-size:18px;color:var(--sa-muted);">›</span>
              </div>
            </div>
          </div>
        </div>

      </template>

    </div>
  </div>
</template>
