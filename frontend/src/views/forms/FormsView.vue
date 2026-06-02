<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import SvgIcon from '@/components/ui/SvgIcon.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchForm } from '@/services/forms.service'
import { useFormsStore } from '@/stores/forms/forms.store'
import type { FormFieldCreatePayload } from '@/types/forms'

const router = useRouter()
const formsStore = useFormsStore()

const search = ref('')

const showCreateComposer = ref(false)
const createError = ref<string | null>(null)
const createState = reactive({
  name: '',
  description: '',
  fields: [createEmptyField(1)],
})

const showVersionComposer = ref(false)
const versionFormId = ref<string | null>(null)
const versionFormName = ref('')
const versionError = ref<string | null>(null)
const versionFields = ref<FormFieldCreatePayload[]>([createEmptyField(1)])

const currentPage = ref(1)

const publishedCount = computed(
  () => formsStore.items.filter((f) => f.current_version_status === 'published').length,
)
const draftCount = computed(
  () => formsStore.items.filter((f) => f.current_version_status !== 'published').length,
)

const filteredForms = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return formsStore.items
  return formsStore.items.filter(
    (f) =>
      f.name.toLowerCase().includes(q) ||
      (f.description ?? '').toLowerCase().includes(q),
  )
})

async function loadPage(page: number) {
  currentPage.value = page
  await formsStore.load(page)
}

onMounted(() => {
  loadPage(1)
})

function createEmptyField(position: number): FormFieldCreatePayload {
  return { key: '', label: '', field_type: 'boolean', required: false, position, config_json: {} }
}

function onFieldTypeChange(field: FormFieldCreatePayload) {
  if (field.field_type !== 'select') field.config_json = {}
}

function getOptionsString(field: FormFieldCreatePayload): string {
  return Array.isArray(field.config_json.options)
    ? (field.config_json.options as string[]).join(', ')
    : ''
}

function setOptionsFromString(field: FormFieldCreatePayload, event: Event) {
  const opts = (event.target as HTMLInputElement).value
    .split(',')
    .map((o) => o.trim())
    .filter(Boolean)
  field.config_json = opts.length ? { options: opts } : {}
}

function openCreateComposer() {
  showVersionComposer.value = false
  showCreateComposer.value = true
}

function closeCreateComposer() {
  showCreateComposer.value = false
  createState.name = ''
  createState.description = ''
  createState.fields = [createEmptyField(1)]
  createError.value = null
}

function addCreateField() {
  createState.fields.push(createEmptyField(createState.fields.length + 1))
}

function removeCreateField(index: number) {
  if (createState.fields.length === 1) return
  createState.fields.splice(index, 1)
  createState.fields.forEach((f, i) => { f.position = i + 1 })
}

async function submitCreate() {
  createError.value = null
  try {
    await formsStore.create({
      name: createState.name,
      description: createState.description || null,
      fields: createState.fields.map((f, i) => ({ ...f, position: i + 1 })),
    })
    closeCreateComposer()
  } catch (err: any) {
    createError.value = extractProblemMessage(err, 'Não foi possível criar o formulário.')
  }
}

async function openVersionComposer(formId: string, formName: string) {
  versionError.value = null
  versionFormId.value = formId
  versionFormName.value = formName
  try {
    const detail = await fetchForm(formId)
    versionFields.value = detail.current_version.fields.map((f) => ({
      key: f.key,
      label: f.label,
      field_type: f.field_type,
      required: f.required,
      position: f.position,
      config_json: f.config_json,
    }))
  } catch {
    versionFields.value = [createEmptyField(1)]
  }
  showCreateComposer.value = false
  showVersionComposer.value = true
}

function closeVersionComposer() {
  showVersionComposer.value = false
  versionFormId.value = null
  versionFormName.value = ''
  versionFields.value = [createEmptyField(1)]
  versionError.value = null
}

function addVersionField() {
  versionFields.value.push(createEmptyField(versionFields.value.length + 1))
}

function removeVersionField(index: number) {
  if (versionFields.value.length === 1) return
  versionFields.value.splice(index, 1)
  versionFields.value.forEach((f, i) => { f.position = i + 1 })
}

async function submitVersion() {
  if (!versionFormId.value) return
  versionError.value = null
  try {
    await formsStore.publishVersion(versionFormId.value, {
      fields: versionFields.value.map((f, i) => ({ ...f, position: i + 1 })),
    })
    closeVersionComposer()
  } catch (err: any) {
    versionError.value = extractProblemMessage(err, 'Não foi possível publicar a nova versão.')
  }
}
</script>

<template>
  <AppShell>
    <div class="page">

      <!-- Header -->
      <div class="phdr">
        <div>
          <p class="eyebrow">Templates</p>
          <h2 class="page-h1">Formulários versionados</h2>
          <p class="page-desc">Checklists e auditorias da empresa ativa.</p>
        </div>
        <button type="button" class="btn-primary btn-sm" @click="openCreateComposer">
          + Novo formulário
        </button>
      </div>

      <!-- Stats -->
      <div class="stats-grid" style="margin-bottom:20px;">
        <div class="scard">
          <div class="sc-label">Total</div>
          <div class="sc-value">{{ formsStore.meta?.total ?? formsStore.items.length }}</div>
        </div>
        <div class="scard sc-ok">
          <div class="sc-label">Publicados</div>
          <div class="sc-value">{{ publishedCount }}</div>
        </div>
        <div class="scard">
          <div class="sc-label">Rascunhos</div>
          <div class="sc-value">{{ draftCount }}</div>
        </div>
        <div class="scard">
          <div class="sc-label">Campos (média)</div>
          <div class="sc-value">—</div>
          <div class="sc-desc">por formulário</div>
        </div>
      </div>

      <!-- Create composer -->
      <div v-if="showCreateComposer" class="card card-p" style="margin-bottom:20px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
          <div>
            <div class="eyebrow">Criação</div>
            <div style="font-size:17px;font-weight:700;color:var(--sa-text);margin-top:3px;">Novo formulário</div>
          </div>
          <button type="button" class="btn-secondary btn-sm" @click="closeCreateComposer">Fechar</button>
        </div>

        <form style="display:grid;gap:12px;" @submit.prevent="submitCreate">
          <div style="display:grid;gap:12px;margin-bottom:4px;">
            <label style="display:grid;gap:6px;">
              <span>Nome do formulário</span>
              <input v-model="createState.name" type="text" required placeholder="Ex: Checklist NR-35 Trabalho em Altura" />
            </label>
            <label style="display:grid;gap:6px;">
              <span>Descrição (opcional)</span>
              <input v-model="createState.description" type="text" placeholder="Breve descrição do formulário" />
            </label>
          </div>

          <div class="slabel">Campos</div>

          <div style="display:grid;gap:10px;">
            <div
              v-for="(field, index) in createState.fields"
              :key="`c-${index}`"
              class="card card-p"
            >
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <span style="font-size:11px;font-weight:700;color:var(--sa-muted);text-transform:uppercase;letter-spacing:.08em;">Campo {{ index + 1 }}</span>
                <button
                  v-if="createState.fields.length > 1"
                  type="button"
                  class="btn-secondary btn-sm"
                  @click="removeCreateField(index)"
                >
                  Remover
                </button>
              </div>
              <div style="display:grid;gap:10px;grid-template-columns:1fr 1fr;">
                <label style="display:grid;gap:6px;">
                  <span>Chave</span>
                  <input v-model="field.key" type="text" required />
                </label>
                <label style="display:grid;gap:6px;">
                  <span>Label</span>
                  <input v-model="field.label" type="text" required />
                </label>
                <label style="display:grid;gap:6px;">
                  <span>Tipo</span>
                  <select v-model="field.field_type" @change="onFieldTypeChange(field)">
                    <option value="boolean">Sim / Não</option>
                    <option value="text">Texto</option>
                    <option value="number">Número</option>
                    <option value="select">Seleção</option>
                    <option value="date">Data</option>

                  </select>
                </label>
                <label style="display:grid;gap:6px;">
                  <span>Obrigatório</span>
                  <select v-model="field.required">
                    <option :value="true">Sim</option>
                    <option :value="false">Não</option>
                  </select>
                </label>
                <label v-if="field.field_type === 'select'" style="display:grid;gap:6px;grid-column:1/-1;">
                  <span>Opções (separadas por vírgula)</span>
                  <input
                    :value="getOptionsString(field)"
                    type="text"
                    placeholder="Ex: Conforme, Não conforme, Parcial"
                    @input="setOptionsFromString(field, $event)"
                  />
                </label>
              </div>
            </div>
          </div>

          <p v-if="createError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ createError }}</p>

          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button type="button" class="btn-secondary btn-sm" @click="addCreateField">+ Adicionar campo</button>
            <button type="submit" class="btn-primary" :disabled="formsStore.isSaving">
              {{ formsStore.isSaving ? 'Criando...' : 'Criar formulário' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Version composer -->
      <div v-if="showVersionComposer" class="card card-p" style="margin-bottom:20px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
          <div>
            <div class="eyebrow">Nova versão</div>
            <div style="font-size:17px;font-weight:700;color:var(--sa-text);margin-top:3px;">{{ versionFormName }}</div>
            <div style="font-size:12px;color:var(--sa-muted);margin-top:4px;">
              Edite os campos abaixo. Uma nova versão será publicada sem alterar as inspeções anteriores.
            </div>
          </div>
          <button type="button" class="btn-secondary btn-sm" @click="closeVersionComposer">Fechar</button>
        </div>

        <form style="display:grid;gap:12px;" @submit.prevent="submitVersion">
          <div class="slabel">Campos</div>

          <div style="display:grid;gap:10px;">
            <div
              v-for="(field, index) in versionFields"
              :key="`v-${index}`"
              class="card card-p"
            >
              <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
                <span style="font-size:11px;font-weight:700;color:var(--sa-muted);text-transform:uppercase;letter-spacing:.08em;">Campo {{ index + 1 }}</span>
                <button
                  v-if="versionFields.length > 1"
                  type="button"
                  class="btn-secondary btn-sm"
                  @click="removeVersionField(index)"
                >
                  Remover
                </button>
              </div>
              <div style="display:grid;gap:10px;grid-template-columns:1fr 1fr;">
                <label style="display:grid;gap:6px;">
                  <span>Chave</span>
                  <input v-model="field.key" type="text" required />
                </label>
                <label style="display:grid;gap:6px;">
                  <span>Label</span>
                  <input v-model="field.label" type="text" required />
                </label>
                <label style="display:grid;gap:6px;">
                  <span>Tipo</span>
                  <select v-model="field.field_type" @change="onFieldTypeChange(field)">
                    <option value="boolean">Sim / Não</option>
                    <option value="text">Texto</option>
                    <option value="number">Número</option>
                    <option value="select">Seleção</option>
                    <option value="date">Data</option>

                  </select>
                </label>
                <label style="display:grid;gap:6px;">
                  <span>Obrigatório</span>
                  <select v-model="field.required">
                    <option :value="true">Sim</option>
                    <option :value="false">Não</option>
                  </select>
                </label>
                <label v-if="field.field_type === 'select'" style="display:grid;gap:6px;grid-column:1/-1;">
                  <span>Opções (separadas por vírgula)</span>
                  <input
                    :value="getOptionsString(field)"
                    type="text"
                    placeholder="Ex: Conforme, Não conforme, Parcial"
                    @input="setOptionsFromString(field, $event)"
                  />
                </label>
              </div>
            </div>
          </div>

          <p v-if="versionError" style="font-size:13px;font-weight:600;color:var(--sa-danger);">{{ versionError }}</p>

          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button type="button" class="btn-secondary btn-sm" @click="addVersionField">+ Adicionar campo</button>
            <button type="submit" class="btn-primary" :disabled="formsStore.isSaving">
              {{ formsStore.isSaving ? 'Publicando...' : 'Publicar nova versão' }}
            </button>
          </div>
        </form>
      </div>

      <!-- Search bar -->
      <div class="sbar" style="margin-bottom:16px;">
        <SvgIcon name="search" :size="16" style="color:var(--sa-muted);flex-shrink:0;" />
        <input
          v-model="search"
          type="text"
          placeholder="Buscar formulário..."
          style="border:none;outline:none;flex:1;min-width:0;padding:0;box-shadow:none;font-size:14px;background:transparent;"
        />
        <button
          v-if="search"
          type="button"
          style="border:none;background:none;cursor:pointer;padding:0;display:flex;align-items:center;color:var(--sa-muted);"
          @click="search = ''"
        >
          <SvgIcon name="close" :size="15" />
        </button>
      </div>

      <p v-if="formsStore.error" style="font-size:13px;font-weight:600;color:var(--sa-danger);margin-bottom:12px;">{{ formsStore.error }}</p>
      <p v-else-if="formsStore.isLoading" style="font-size:13px;color:var(--sa-muted);margin-bottom:12px;">Carregando formulários...</p>

      <!-- Forms list -->
      <div v-if="filteredForms.length" class="lstack">
        <div
          v-for="form in filteredForms"
          :key="form.id"
          class="lrow"
          style="align-items:flex-start;cursor:pointer;"
          @click="router.push({ name: 'form-detail', params: { formId: form.id } })"
        >
          <div class="lrow-main">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;">
              <div class="lrow-title">{{ form.name }}</div>
              <span
                class="status-chip"
                :class="{ 'status-chip--neu': form.current_version_status !== 'published' }"
              >
                {{ form.current_version_status === 'published' ? 'Publicado' : 'Rascunho' }}
              </span>
              <span class="ver-badge">v{{ form.current_version_number }}</span>
            </div>
            <div class="lrow-sub">
              {{ form.description || 'Sem descrição cadastrada.' }}
              · {{ form.published_at ? new Date(form.published_at).toLocaleDateString('pt-BR') : 'Não publicado' }}
            </div>
          </div>
          <div style="display:flex;gap:6px;flex-shrink:0;align-items:center;" @click.stop>
            <button
              type="button"
              class="btn-secondary btn-sm"
              @click="openVersionComposer(form.id, form.name)"
            >
              Nova versão
            </button>
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div v-else-if="!formsStore.isLoading" class="empty">
        <div class="empty-icon">
          <SvgIcon name="forms" :size="36" />
        </div>
        <div class="empty-h">
          {{ search ? 'Nenhum formulário encontrado' : 'Nenhum formulário cadastrado' }}
        </div>
        <p class="empty-p">
          {{ search ? 'Tente outro termo de busca.' : 'Use o botão acima para criar seu primeiro formulário.' }}
        </p>
      </div>

      <!-- Pagination -->
      <nav
        v-if="formsStore.meta && formsStore.meta.total_pages > 1"
        style="display:flex;align-items:center;justify-content:center;gap:12px;margin-top:16px;"
      >
        <button
          type="button"
          class="btn-secondary btn-sm"
          :disabled="currentPage <= 1 || formsStore.isLoading"
          @click="loadPage(currentPage - 1)"
        >
          ← Anterior
        </button>
        <span style="font-size:13px;color:var(--sa-muted);">
          Página {{ currentPage }} de {{ formsStore.meta.total_pages }}
        </span>
        <button
          type="button"
          class="btn-secondary btn-sm"
          :disabled="!formsStore.meta.has_next || formsStore.isLoading"
          @click="loadPage(currentPage + 1)"
        >
          Próxima →
        </button>
      </nav>

    </div>
  </AppShell>
</template>
