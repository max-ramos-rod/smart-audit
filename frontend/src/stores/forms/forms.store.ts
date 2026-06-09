import { ref } from 'vue'
import { defineStore } from 'pinia'

import { extractProblemMessage } from '@/services/api/problem'
import {
  createForm,
  fetchForms,
  fetchFormVersions,
  publishNewVersion,
} from '@/services/forms.service'
import type { PaginationMeta } from '@/types/api'
import type {
  FormCreatePayload,
  FormListItem,
  FormVersionListItem,
  FormVersionPublishPayload,
} from '@/types/forms'

export const useFormsStore = defineStore('forms', () => {
  const items = ref<FormListItem[]>([])
  const meta = ref<PaginationMeta | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const versions = ref<FormVersionListItem[]>([])
  const isLoadingVersions = ref(false)

  async function load(page = 1, pageSize = 20) {
    isLoading.value = true
    error.value = null
    try {
      const response = await fetchForms(page, pageSize)
      items.value = response.data
      meta.value = response.meta
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar formularios.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function create(payload: FormCreatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const created = await createForm(payload)
      await load(1, meta.value?.page_size ?? 20)
      return created
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel criar o formulario.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function publishVersion(formId: string, payload: FormVersionPublishPayload) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await publishNewVersion(formId, payload)
      await load(1, meta.value?.page_size ?? 20)
      return updated
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel publicar a nova versao.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function loadVersions(formId: string) {
    isLoadingVersions.value = true
    try {
      versions.value = await fetchFormVersions(formId)
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar versoes.')
      throw err
    } finally {
      isLoadingVersions.value = false
    }
  }

  function clearVersions() {
    versions.value = []
  }

  return {
    items,
    meta,
    isLoading,
    isSaving,
    error,
    load,
    create,
    publishVersion,
    versions,
    isLoadingVersions,
    loadVersions,
    clearVersions,
  }
})
