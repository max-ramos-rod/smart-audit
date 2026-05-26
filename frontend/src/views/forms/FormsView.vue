<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import AppShell from '@/components/layout/AppShell.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { extractProblemMessage } from '@/services/api/problem'
import { fetchForm } from '@/services/forms.service'
import { useFormsStore } from '@/stores/forms/forms.store'
import type { FormFieldCreatePayload } from '@/types/forms'

const router = useRouter()
const formsStore = useFormsStore()

// --- create form state ---
const showCreateComposer = ref(false)
const createError = ref<string | null>(null)
const createState = reactive({
  name: '',
  description: '',
  fields: [createEmptyField(1)],
})

// --- publish version state ---
const showVersionComposer = ref(false)
const versionFormId = ref<string | null>(null)
const versionFormName = ref('')
const versionError = ref<string | null>(null)
const versionFields = ref<FormFieldCreatePayload[]>([createEmptyField(1)])

const publishedCount = computed(
  () => formsStore.items.filter((f) => f.current_version_status === 'published').length,
)

const currentPage = ref(1)

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

// ---- create form ----
function openCreateComposer() {
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

// ---- publish new version ----
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
    <section class="flex flex-wrap items-center justify-between gap-3 px-1">
      <div>
        <p class="eyebrow">Templates</p>
        <h2 class="mt-2 text-2xl font-semibold tracking-tight text-sa-text">Formulários versionados</h2>
        <p class="mt-2 text-sm text-sa-muted">Base atual para construção e evolução dos checklists por empresa.</p>
      </div>
      <BaseButton type="button" @click="openCreateComposer">Novo formulário</BaseButton>
    </section>

    <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <article class="surface-panel p-4">
        <span class="eyebrow">Total</span>
        <strong class="mt-2 block text-2xl font-semibold text-sa-text">
          {{ formsStore.meta?.total ?? formsStore.items.length }}
        </strong>
      </article>
      <article class="surface-panel p-4">
        <span class="eyebrow">Publicados</span>
        <strong class="mt-2 block text-2xl font-semibold text-sa-text">{{ publishedCount }}</strong>
      </article>
      <article class="surface-panel p-4">
        <span class="eyebrow">Página</span>
        <strong class="mt-2 block text-2xl font-semibold text-sa-text">
          {{ currentPage }} / {{ formsStore.meta?.total_pages ?? 1 }}
        </strong>
      </article>
      <article class="surface-panel p-4">
        <span class="eyebrow">Mostrando</span>
        <strong class="mt-2 block text-2xl font-semibold text-sa-text">
          {{ formsStore.items.length }}
        </strong>
        <p class="mt-1 text-sm text-sa-muted">de {{ formsStore.meta?.total ?? formsStore.items.length }}</p>
      </article>
    </section>

    <!-- create composer -->
    <section v-if="showCreateComposer" class="surface-panel p-5 sm:p-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="eyebrow">Criação</p>
          <h3 class="mt-2 text-xl font-semibold text-sa-text">Novo formulário</h3>
        </div>
        <BaseButton type="button" variant="ghost" @click="closeCreateComposer">Fechar</BaseButton>
      </div>

      <form class="mt-5 grid gap-4" @submit.prevent="submitCreate">
        <label class="grid gap-2">
          <span>Nome</span>
          <input v-model="createState.name" type="text" required />
        </label>
        <label class="grid gap-2">
          <span>Descrição</span>
          <input v-model="createState.description" type="text" />
        </label>

        <div class="grid gap-4">
          <article
            v-for="(field, index) in createState.fields"
            :key="`c-${index}`"
            class="rounded-3xl border border-[color:var(--sa-line)] bg-white/70 p-4"
          >
            <div class="flex items-center justify-between gap-3">
              <p class="eyebrow">Campo {{ index + 1 }}</p>
              <BaseButton
                type="button"
                variant="ghost"
                :disabled="createState.fields.length === 1"
                @click="removeCreateField(index)"
              >
                Remover
              </BaseButton>
            </div>
            <div class="mt-4 grid gap-4 sm:grid-cols-2">
              <label class="grid gap-2">
                <span>Chave</span>
                <input v-model="field.key" type="text" required />
              </label>
              <label class="grid gap-2">
                <span>Label</span>
                <input v-model="field.label" type="text" required />
              </label>
              <label class="grid gap-2">
                <span>Tipo</span>
                <select v-model="field.field_type" @change="onFieldTypeChange(field)">
                  <option value="boolean">Boolean</option>
                  <option value="text">Texto</option>
                  <option value="number">Número</option>
                  <option value="select">Seleção</option>
                  <option value="date">Data</option>
                  <option value="photo">Foto</option>
                </select>
              </label>
              <label class="grid gap-2">
                <span>Obrigatório</span>
                <select v-model="field.required">
                  <option :value="true">Sim</option>
                  <option :value="false">Não</option>
                </select>
              </label>
              <label v-if="field.field_type === 'select'" class="grid gap-2 sm:col-span-2">
                <span>Opções (separadas por vírgula)</span>
                <input
                  :value="getOptionsString(field)"
                  type="text"
                  placeholder="Ex: Conforme, Não conforme, Parcial"
                  @input="setOptionsFromString(field, $event)"
                />
                <span class="text-xs text-sa-muted">Mínimo 1 opção obrigatória para campos do tipo seleção.</span>
              </label>
            </div>
          </article>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row">
          <BaseButton type="button" variant="ghost" @click="addCreateField">
            Adicionar campo
          </BaseButton>
          <BaseButton type="submit" :disabled="formsStore.isSaving">
            {{ formsStore.isSaving ? 'Criando...' : 'Criar formulário' }}
          </BaseButton>
        </div>
        <p v-if="createError" class="text-sm font-medium text-sa-danger">{{ createError }}</p>
      </form>
    </section>

    <!-- version composer -->
    <section v-if="showVersionComposer" class="surface-panel p-5 sm:p-6">
      <div class="flex items-center justify-between gap-3">
        <div>
          <p class="eyebrow">Nova versão</p>
          <h3 class="mt-2 text-xl font-semibold text-sa-text">{{ versionFormName }}</h3>
          <p class="mt-1 text-sm text-sa-muted">
            Edite os campos abaixo. Uma nova versão será publicada sem alterar as inspeções anteriores.
          </p>
        </div>
        <BaseButton type="button" variant="ghost" @click="closeVersionComposer">Fechar</BaseButton>
      </div>

      <form class="mt-5 grid gap-4" @submit.prevent="submitVersion">
        <div class="grid gap-4">
          <article
            v-for="(field, index) in versionFields"
            :key="`v-${index}`"
            class="rounded-3xl border border-[color:var(--sa-line)] bg-white/70 p-4"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="eyebrow">Campo {{ index + 1 }}</p>
              </div>
              <BaseButton
                type="button"
                variant="ghost"
                :disabled="versionFields.length === 1"
                @click="removeVersionField(index)"
              >
                Remover
              </BaseButton>
            </div>
            <div class="mt-4 grid gap-4 sm:grid-cols-2">
              <label class="grid gap-2">
                <span>Chave</span>
                <input v-model="field.key" type="text" required />
              </label>
              <label class="grid gap-2">
                <span>Label</span>
                <input v-model="field.label" type="text" required />
              </label>
              <label class="grid gap-2">
                <span>Tipo</span>
                <select v-model="field.field_type" @change="onFieldTypeChange(field)">
                  <option value="boolean">Boolean</option>
                  <option value="text">Texto</option>
                  <option value="number">Número</option>
                  <option value="select">Seleção</option>
                  <option value="date">Data</option>
                  <option value="photo">Foto</option>
                </select>
              </label>
              <label class="grid gap-2">
                <span>Obrigatório</span>
                <select v-model="field.required">
                  <option :value="true">Sim</option>
                  <option :value="false">Não</option>
                </select>
              </label>
              <label v-if="field.field_type === 'select'" class="grid gap-2 sm:col-span-2">
                <span>Opções (separadas por vírgula)</span>
                <input
                  :value="getOptionsString(field)"
                  type="text"
                  placeholder="Ex: Conforme, Não conforme, Parcial"
                  @input="setOptionsFromString(field, $event)"
                />
                <span class="text-xs text-sa-muted">Mínimo 1 opção obrigatória para campos do tipo seleção.</span>
              </label>
            </div>
          </article>
        </div>

        <div class="flex flex-col gap-3 sm:flex-row">
          <BaseButton type="button" variant="ghost" @click="addVersionField">
            Adicionar campo
          </BaseButton>
          <BaseButton type="submit" :disabled="formsStore.isSaving">
            {{ formsStore.isSaving ? 'Publicando...' : 'Publicar nova versão' }}
          </BaseButton>
        </div>
        <p v-if="versionError" class="text-sm font-medium text-sa-danger">{{ versionError }}</p>
      </form>
    </section>

    <p v-if="formsStore.error" class="text-sm font-medium text-sa-danger">{{ formsStore.error }}</p>
    <p v-else-if="formsStore.isLoading" class="text-sm font-medium text-sa-muted">Carregando formulários...</p>

    <section v-if="formsStore.items.length" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <article v-for="form in formsStore.items" :key="form.id" class="surface-panel p-5">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="eyebrow">Versão {{ form.current_version_number }}</p>
            <h3 class="mt-3 text-xl font-semibold text-sa-text">{{ form.name }}</h3>
          </div>
          <span class="status-chip" :class="{ 'status-chip--inactive': !form.is_active }">
            {{ form.is_active ? 'Ativo' : 'Inativo' }}
          </span>
        </div>
        <p class="mt-3 text-sm leading-6 text-sa-muted">
          {{ form.description || 'Sem descrição cadastrada.' }}
        </p>
        <footer class="mt-5 flex items-center justify-between gap-3">
          <span class="text-sm text-sa-muted">
            {{ form.published_at ? new Date(form.published_at).toLocaleDateString('pt-BR') : 'Não publicado' }}
          </span>
          <div class="flex items-center gap-3">
            <button
              class="inline-action"
              type="button"
              @click="router.push({ name: 'form-versions', params: { formId: form.id } })"
            >
              Histórico
            </button>
            <button
              class="inline-action"
              type="button"
              @click="openVersionComposer(form.id, form.name)"
            >
              Nova versão →
            </button>
          </div>
        </footer>
      </article>
    </section>

    <section v-else-if="!formsStore.isLoading" class="surface-panel p-6 text-center">
      <p class="eyebrow">Sem dados</p>
      <h3 class="mt-3 text-xl font-semibold text-sa-text">Nenhum formulário cadastrado</h3>
      <p class="mt-2 text-sm text-sa-muted">
        Use a criação acima para começar a montar seus modelos de inspeção.
      </p>
    </section>

    <nav
      v-if="formsStore.meta && formsStore.meta.total_pages > 1"
      class="flex items-center justify-center gap-4"
    >
      <BaseButton
        type="button"
        variant="ghost"
        :disabled="currentPage <= 1 || formsStore.isLoading"
        @click="loadPage(currentPage - 1)"
      >
        ← Anterior
      </BaseButton>
      <span class="text-sm text-sa-muted">
        Página {{ currentPage }} de {{ formsStore.meta.total_pages }}
      </span>
      <BaseButton
        type="button"
        variant="ghost"
        :disabled="!formsStore.meta.has_next || formsStore.isLoading"
        @click="loadPage(currentPage + 1)"
      >
        Próxima →
      </BaseButton>
    </nav>
  </AppShell>
</template>
