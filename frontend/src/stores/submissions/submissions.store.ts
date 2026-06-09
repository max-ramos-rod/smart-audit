import { ref } from 'vue'
import { defineStore } from 'pinia'

import { extractProblemMessage } from '@/services/api/problem'
import {
  createSubmission,
  fetchSubmission,
  fetchSubmissions,
  finishSubmission,
  saveAnswers,
} from '@/services/submissions.service'
import type { PaginationMeta } from '@/types/api'
import type {
  SubmissionAnswersUpdatePayload,
  SubmissionCreatePayload,
  SubmissionDetail,
  SubmissionListItem,
} from '@/types/submissions'

export const useSubmissionsStore = defineStore('submissions', () => {
  const items = ref<SubmissionListItem[]>([])
  const current = ref<SubmissionDetail | null>(null)
  const meta = ref<PaginationMeta | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)
  const status = ref<string | undefined>(undefined)
  const formId = ref<string | undefined>(undefined)

  async function load(page = 1, pageSize = 20, statusFilter?: string, formIdFilter?: string) {
    status.value = statusFilter
    formId.value = formIdFilter
    isLoading.value = true
    error.value = null
    try {
      const response = await fetchSubmissions(page, pageSize, statusFilter, formIdFilter)
      items.value = response.data
      meta.value = response.meta
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar inspecoes.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function loadOne(submissionId: string) {
    isLoading.value = true
    error.value = null
    try {
      current.value = await fetchSubmission(submissionId)
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar a inspecao.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function create(payload: SubmissionCreatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const created = await createSubmission(payload)
      current.value = created
      return created
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel criar a inspecao.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function updateAnswers(submissionId: string, payload: SubmissionAnswersUpdatePayload) {
    isSaving.value = true
    error.value = null
    try {
      current.value = await saveAnswers(submissionId, payload)
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel salvar as respostas.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function finish(submissionId: string) {
    isSaving.value = true
    error.value = null
    try {
      current.value = await finishSubmission(submissionId)
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel finalizar a inspecao.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  function reset() {
    items.value = []
    current.value = null
    meta.value = null
    error.value = null
  }

  return {
    items,
    current,
    meta,
    isLoading,
    isSaving,
    error,
    load,
    loadOne,
    create,
    updateAnswers,
    finish,
    reset,
    status,
    formId,
  }
})
