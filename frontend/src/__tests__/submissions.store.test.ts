import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/submissions.service', () => ({
  fetchSubmissions: vi.fn(),
  fetchSubmission: vi.fn(),
  createSubmission: vi.fn(),
  saveAnswers: vi.fn(),
  finishSubmission: vi.fn(),
}))

import {
  createSubmission,
  fetchSubmission,
  fetchSubmissions,
  finishSubmission,
  saveAnswers,
} from '@/services/submissions.service'
import { useSubmissionsStore } from '@/stores/submissions/submissions.store'
import type { SubmissionDetail, SubmissionListItem } from '@/types/submissions'

const mockListItem: SubmissionListItem = {
  id: 's1',
  form_id: 'f1',
  form_name: 'Checklist Segurança',
  status: 'in_progress',
  score: null,
  started_at: '2026-01-01T10:00:00Z',
  finished_at: null,
}

const mockDetail: SubmissionDetail = {
  ...mockListItem,
  form_version_id: 'v1',
  answers: [{ field_key: 'extintor_ok', field_type: 'boolean', value: true }],
}

const mockCompletedDetail: SubmissionDetail = {
  ...mockDetail,
  status: 'completed',
  score: 100,
  finished_at: '2026-01-01T11:00:00Z',
}

const mockPaginatedResponse = {
  data: [mockListItem],
  meta: { total: 1, page: 1, page_size: 20, has_next: false, total_pages: 1 },
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

describe('submissions.store', () => {
  it('starts with empty state', () => {
    const store = useSubmissionsStore()
    expect(store.items).toEqual([])
    expect(store.current).toBeNull()
    expect(store.meta).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.isSaving).toBe(false)
    expect(store.error).toBeNull()
  })

  describe('load', () => {
    it('populates items and meta on success', async () => {
      vi.mocked(fetchSubmissions).mockResolvedValue(mockPaginatedResponse)
      const store = useSubmissionsStore()

      await store.load()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].form_name).toBe('Checklist Segurança')
      expect(store.meta?.total).toBe(1)
      expect(store.isLoading).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Sem permissao.' } } }
      vi.mocked(fetchSubmissions).mockRejectedValue(err)
      const store = useSubmissionsStore()

      await expect(store.load()).rejects.toBe(err)
      expect(store.error).toBe('Sem permissao.')
      expect(store.isLoading).toBe(false)
    })
  })

  describe('loadOne', () => {
    it('sets current on success', async () => {
      vi.mocked(fetchSubmission).mockResolvedValue(mockDetail)
      const store = useSubmissionsStore()

      await store.loadOne('s1')

      expect(store.current).toEqual(mockDetail)
      expect(store.isLoading).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Nao encontrado.' } } }
      vi.mocked(fetchSubmission).mockRejectedValue(err)
      const store = useSubmissionsStore()

      await expect(store.loadOne('s1')).rejects.toBe(err)
      expect(store.error).toBe('Nao encontrado.')
    })
  })

  describe('create', () => {
    it('calls createSubmission, sets current, and returns created submission', async () => {
      vi.mocked(createSubmission).mockResolvedValue(mockDetail)
      const store = useSubmissionsStore()

      const result = await store.create({ form_id: 'f1' })

      expect(createSubmission).toHaveBeenCalledWith({ form_id: 'f1' })
      expect(store.current).toEqual(mockDetail)
      expect(result).toEqual(mockDetail)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Versao nao encontrada.' } } }
      vi.mocked(createSubmission).mockRejectedValue(err)
      const store = useSubmissionsStore()

      await expect(store.create({ form_id: 'f1' })).rejects.toBe(err)
      expect(store.error).toBe('Versao nao encontrada.')
    })
  })

  describe('updateAnswers', () => {
    it('calls saveAnswers and updates current', async () => {
      const updatedDetail = { ...mockDetail, answers: [{ field_key: 'extintor_ok', field_type: 'boolean', value: false }] }
      vi.mocked(saveAnswers).mockResolvedValue(updatedDetail)
      const store = useSubmissionsStore()
      store.current = mockDetail

      await store.updateAnswers('s1', { answers: [{ field_key: 'extintor_ok', value: false }] })

      expect(saveAnswers).toHaveBeenCalledWith('s1', { answers: [{ field_key: 'extintor_ok', value: false }] })
      expect(store.current?.answers[0].value).toBe(false)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Campo invalido.' } } }
      vi.mocked(saveAnswers).mockRejectedValue(err)
      const store = useSubmissionsStore()

      await expect(store.updateAnswers('s1', { answers: [] })).rejects.toBe(err)
      expect(store.error).toBe('Campo invalido.')
    })
  })

  describe('finish', () => {
    it('calls finishSubmission and updates current with completed status', async () => {
      vi.mocked(finishSubmission).mockResolvedValue(mockCompletedDetail)
      const store = useSubmissionsStore()
      store.current = mockDetail

      await store.finish('s1')

      expect(finishSubmission).toHaveBeenCalledWith('s1')
      expect(store.current?.status).toBe('completed')
      expect(store.current?.score).toBe(100)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Inspecao ja finalizada.' } } }
      vi.mocked(finishSubmission).mockRejectedValue(err)
      const store = useSubmissionsStore()

      await expect(store.finish('s1')).rejects.toBe(err)
      expect(store.error).toBe('Inspecao ja finalizada.')
    })
  })

  describe('reset', () => {
    it('clears all state', async () => {
      vi.mocked(fetchSubmissions).mockResolvedValue(mockPaginatedResponse)
      const store = useSubmissionsStore()
      await store.load()
      store.current = mockDetail

      store.reset()

      expect(store.items).toEqual([])
      expect(store.current).toBeNull()
      expect(store.meta).toBeNull()
      expect(store.error).toBeNull()
    })
  })
})
