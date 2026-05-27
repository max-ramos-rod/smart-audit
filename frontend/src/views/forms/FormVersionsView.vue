<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { fetchForm, fetchFormVersion } from '@/services/forms.service'
import { useFormsStore } from '@/stores/forms/forms.store'
import type { FormDetail, FormField, FormVersionListItem } from '@/types/forms'

const route = useRoute()
const router = useRouter()
const formsStore = useFormsStore()
const formId = computed(() => route.params.formId as string)

const formDetail = ref<FormDetail | null>(null)
const isLoading = ref(true)

const expandedVersionIds = ref<Set<string>>(new Set())
const loadingVersionIds = ref<Set<string>>(new Set())
const versionFields = ref<Record<string, FormField[]>>({})

const TYPE_LABEL: Record<string, string> = {
  boolean: 'Sim/Não', text: 'Texto', number: 'Número',
  date: 'Data', photo: 'Foto', select: 'Seleção',
}

onMounted(async () => {
  try {
    await formsStore.loadVersions(formId.value)
    formDetail.value = await fetchForm(formId.value)
  } finally {
    isLoading.value = false
  }
})

async function toggleFields(version: FormVersionListItem) {
  if (expandedVersionIds.value.has(version.id)) {
    expandedVersionIds.value.delete(version.id)
    return
  }
  if (!versionFields.value[version.id]) {
    loadingVersionIds.value.add(version.id)
    try {
      const v = await fetchFormVersion(formId.value, version.id)
      versionFields.value[version.id] = v.fields
    } finally {
      loadingVersionIds.value.delete(version.id)
    }
  }
  expandedVersionIds.value.add(version.id)
}

function isCurrent(index: number) {
  return index === 0
}
</script>

<template>
  <AppShell>
    <div class="page">

      <div v-if="isLoading" style="font-size:13px;color:var(--sa-muted);">Carregando...</div>

      <template v-else>

        <!-- Back header -->
        <div class="back-hdr">
          <button
            type="button"
            class="back-btn"
            @click="router.push({ name: 'form-detail', params: { formId } })"
          >
            <SvgIcon name="back" :size="16" />
          </button>
          <div style="flex:1;min-width:0;">
            <div class="eyebrow">Histórico de versões</div>
            <h1 style="font-size:18px;font-weight:700;letter-spacing:-.01em;color:var(--sa-text);margin-top:2px;">
              {{ formDetail?.name ?? '—' }}
            </h1>
          </div>
        </div>

        <!-- Info box -->
        <div class="info-box" style="margin-bottom:24px;">
          Versões são imutáveis. Inspeções associadas a versões anteriores permanecem legíveis com os campos originais.
        </div>

        <!-- Timeline -->
        <div v-if="formsStore.versions.length" style="position:relative;">

          <!-- Vertical connecting line (behind dots) -->
          <div style="
            position:absolute;
            left:19px;
            top:38px;
            bottom:19px;
            width:2px;
            background:var(--sa-line);
            border-radius:1px;
          "></div>

          <div
            v-for="(version, index) in formsStore.versions"
            :key="version.id"
            style="display:flex;align-items:flex-start;gap:16px;margin-bottom:16px;position:relative;"
          >
            <!-- Timeline dot (38×38, centered at left:19px) -->
            <div
              :style="{
                flexShrink: 0,
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: isCurrent(index) ? 'var(--sa-brand)' : 'var(--sa-line)',
                zIndex: 1,
              }"
            >
              <span :style="{
                fontSize: '10px',
                fontWeight: 800,
                color: isCurrent(index) ? '#fff' : 'var(--sa-muted)',
                fontFamily: '\'DM Mono\', monospace',
                letterSpacing: '.02em',
              }">v{{ version.version }}</span>
            </div>

            <!-- Version card -->
            <div
              class="card card-p"
              style="flex:1;min-width:0;"
              :style="isCurrent(index)
                ? 'border-color:var(--sa-brand);background:var(--sa-brand-soft);'
                : ''"
            >
              <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
                <div style="min-width:0;">
                  <div style="font-size:15px;font-weight:700;color:var(--sa-text);">
                    Versão {{ version.version }}
                  </div>
                  <div style="font-size:12px;color:var(--sa-muted);margin-top:3px;">
                    {{ version.fields_count }} campo{{ version.fields_count !== 1 ? 's' : '' }}
                    <template v-if="version.published_at">
                      · publicada {{ new Date(version.published_at).toLocaleDateString('pt-BR') }}
                    </template>
                  </div>
                </div>
                <span
                  class="status-chip"
                  :class="{ 'status-chip--neu': !isCurrent(index) }"
                  style="flex-shrink:0;"
                >
                  {{ isCurrent(index) ? 'Atual' : 'Arquivada' }}
                </span>
              </div>

              <!-- Toggle fields button -->
              <button
                type="button"
                class="btn-secondary btn-sm"
                style="font-size:12px;"
                :disabled="loadingVersionIds.has(version.id)"
                @click="toggleFields(version)"
              >
                {{ loadingVersionIds.has(version.id)
                  ? 'Carregando...'
                  : expandedVersionIds.has(version.id)
                    ? '▲ Fechar'
                    : '▼ Campos' }}
              </button>

              <!-- Fields chips -->
              <div
                v-if="expandedVersionIds.has(version.id) && versionFields[version.id]"
                style="margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;"
              >
                <div
                  v-for="field in versionFields[version.id]"
                  :key="field.id"
                  style="
                    display:inline-flex;align-items:center;gap:0;
                    border-radius:6px;
                    border:1px solid var(--sa-line);
                    background:var(--sa-bg);
                    overflow:hidden;
                  "
                >
                  <span style="
                    font-family:'DM Mono',monospace;font-size:11px;font-weight:600;
                    color:var(--sa-text);padding:3px 7px;
                  ">{{ field.key }}</span>
                  <span style="
                    font-size:10px;font-weight:600;
                    color:var(--sa-muted);padding:3px 7px;
                    background:var(--sa-line);
                    text-transform:uppercase;letter-spacing:.04em;
                    border-left:1px solid var(--sa-line);
                  ">{{ (TYPE_LABEL[field.field_type] ?? field.field_type).slice(0,3) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty">
          <div class="empty-h">Nenhuma versão encontrada</div>
          <p class="empty-p">Publique uma nova versão a partir da tela de detalhes.</p>
        </div>

      </template>

    </div>
  </AppShell>
</template>
