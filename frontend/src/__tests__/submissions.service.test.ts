import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn(), put: vi.fn() },
}))

const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')
const mockRevokeObjectURL = vi.fn()
global.URL.createObjectURL = mockCreateObjectURL
global.URL.revokeObjectURL = mockRevokeObjectURL

import { http } from '@/services/api/http'
import {
  createSubmission,
  exportSubmissionsCSV,
  fetchSubmission,
  fetchSubmissions,
  finishSubmission,
  saveAnswers,
} from '@/services/submissions.service'

const mockListItem = {
  id: 's1',
  form_name: 'Safety Check',
  status: 'in_progress',
  score: null,
  started_at: '2024-01-01T00:00:00Z',
  finished_at: null,
}
const mockDetail = { ...mockListItem, form_version_id: 'v1', answers_json: [] }
const mockMeta = { page: 1, page_size: 20, total: 1, total_pages: 1, has_next: false }

beforeEach(() => {
  vi.clearAllMocks()
  mockCreateObjectURL.mockReturnValue('blob:mock-url')
})

describe('submissions.service', () => {
  describe('fetchSubmissions', () => {
    it('gets /submissions with default params and returns paginated envelope', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockListItem], meta: mockMeta } })
      const result = await fetchSubmissions()
      expect(http.get).toHaveBeenCalledWith('/submissions', {
        params: { page: 1, page_size: 20 },
      })
      expect(result.data).toEqual([mockListItem])
    })

    it('includes status filter when provided', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [], meta: mockMeta } })
      await fetchSubmissions(1, 20, 'completed')
      expect(http.get).toHaveBeenCalledWith('/submissions', {
        params: { page: 1, page_size: 20, status: 'completed' },
      })
    })

    it('includes form_id and created_by filters when provided', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [], meta: mockMeta } })
      await fetchSubmissions(2, 10, undefined, 'f1', 'u1')
      expect(http.get).toHaveBeenCalledWith('/submissions', {
        params: { page: 2, page_size: 10, form_id: 'f1', created_by: 'u1' },
      })
    })
  })

  describe('fetchSubmission', () => {
    it('gets /submissions/:id and returns detail', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockDetail } })
      const result = await fetchSubmission('s1')
      expect(http.get).toHaveBeenCalledWith('/submissions/s1')
      expect(result).toEqual(mockDetail)
    })
  })

  describe('createSubmission', () => {
    it('posts to /submissions and returns detail', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockDetail } })
      const result = await createSubmission({ form_id: 'f1' })
      expect(http.post).toHaveBeenCalledWith('/submissions', { form_id: 'f1' })
      expect(result).toEqual(mockDetail)
    })
  })

  describe('saveAnswers', () => {
    it('puts to /submissions/:id/answers with payload and returns detail', async () => {
      vi.mocked(http.put).mockResolvedValue({ data: { data: mockDetail } })
      const payload = { answers: [{ field_key: 'ok', value: true }] }
      const result = await saveAnswers('s1', payload)
      expect(http.put).toHaveBeenCalledWith('/submissions/s1/answers', payload)
      expect(result).toEqual(mockDetail)
    })
  })

  describe('finishSubmission', () => {
    it('posts to /submissions/:id/finish and returns detail', async () => {
      const finished = { ...mockDetail, status: 'completed', score: 100 }
      vi.mocked(http.post).mockResolvedValue({ data: { data: finished } })
      const result = await finishSubmission('s1')
      expect(http.post).toHaveBeenCalledWith('/submissions/s1/finish')
      expect(result).toEqual(finished)
    })
  })

  describe('exportSubmissionsCSV', () => {
    it('gets /submissions/export as blob and triggers download', async () => {
      const mockBlob = new Blob(['csv content'], { type: 'text/csv' })
      vi.mocked(http.get).mockResolvedValue({ data: mockBlob })

      const appendSpy = vi.spyOn(document.body, 'appendChild').mockImplementation((el) => el)
      const removeSpy = vi.spyOn(document.body, 'removeChild').mockImplementation((el) => el)
      const clickSpy = vi.fn()
      vi.spyOn(document, 'createElement').mockReturnValue({ href: '', download: '', click: clickSpy } as any)

      await exportSubmissionsCSV()

      expect(http.get).toHaveBeenCalledWith('/submissions/export', {
        params: {},
        responseType: 'blob',
      })
      expect(mockCreateObjectURL).toHaveBeenCalledWith(mockBlob)
      expect(clickSpy).toHaveBeenCalled()
      expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url')

      appendSpy.mockRestore()
      removeSpy.mockRestore()
    })

    it('passes status and form_id params when provided', async () => {
      const mockBlob = new Blob(['csv'], { type: 'text/csv' })
      vi.mocked(http.get).mockResolvedValue({ data: mockBlob })
      vi.spyOn(document.body, 'appendChild').mockImplementation((el) => el)
      vi.spyOn(document.body, 'removeChild').mockImplementation((el) => el)
      vi.spyOn(document, 'createElement').mockReturnValue({ href: '', download: '', click: vi.fn() } as any)

      await exportSubmissionsCSV('completed', 'f1')

      expect(http.get).toHaveBeenCalledWith('/submissions/export', {
        params: { status: 'completed', form_id: 'f1' },
        responseType: 'blob',
      })
    })
  })
})
