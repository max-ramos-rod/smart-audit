import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn() },
}))

import { http } from '@/services/api/http'
import {
  createForm,
  fetchForm,
  fetchFormVersion,
  fetchFormVersions,
  fetchForms,
  publishNewVersion,
} from '@/services/forms.service'

const mockFormListItem = {
  id: 'f1',
  name: 'Safety Check',
  current_version_number: 2,
  status: 'published',
  created_at: '2024-01-01T00:00:00Z',
}
const mockFormDetail = { ...mockFormListItem, versions: [] }
const mockVersion = { id: 'v1', version_number: 2, fields: [], created_at: '2024-01-01T00:00:00Z' }
const mockMeta = { page: 1, page_size: 20, total: 1, total_pages: 1, has_next: false }

beforeEach(() => vi.clearAllMocks())

describe('forms.service', () => {
  describe('fetchForms', () => {
    it('gets /forms with default pagination params and returns full envelope', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockFormListItem], meta: mockMeta } })
      const result = await fetchForms()
      expect(http.get).toHaveBeenCalledWith('/forms', { params: { page: 1, page_size: 20 } })
      expect(result.data).toEqual([mockFormListItem])
      expect(result.meta).toEqual(mockMeta)
    })

    it('passes custom page and pageSize', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [], meta: mockMeta } })
      await fetchForms(3, 10)
      expect(http.get).toHaveBeenCalledWith('/forms', { params: { page: 3, page_size: 10 } })
    })
  })

  describe('fetchForm', () => {
    it('gets /forms/:id and returns form detail', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockFormDetail } })
      const result = await fetchForm('f1')
      expect(http.get).toHaveBeenCalledWith('/forms/f1')
      expect(result).toEqual(mockFormDetail)
    })
  })

  describe('createForm', () => {
    it('posts to /forms with payload and returns form detail', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockFormDetail } })
      const payload = { name: 'Safety Check', fields: [] }
      const result = await createForm(payload as any)
      expect(http.post).toHaveBeenCalledWith('/forms', payload)
      expect(result).toEqual(mockFormDetail)
    })
  })

  describe('fetchFormVersion', () => {
    it('gets /forms/:formId/versions/:versionId and returns version', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockVersion } })
      const result = await fetchFormVersion('f1', 'v1')
      expect(http.get).toHaveBeenCalledWith('/forms/f1/versions/v1')
      expect(result).toEqual(mockVersion)
    })
  })

  describe('fetchFormVersions', () => {
    it('gets /forms/:formId/versions and returns array', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockVersion] } })
      const result = await fetchFormVersions('f1')
      expect(http.get).toHaveBeenCalledWith('/forms/f1/versions')
      expect(result).toEqual([mockVersion])
    })
  })

  describe('publishNewVersion', () => {
    it('posts to /forms/:formId/versions with payload and returns form detail', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockFormDetail } })
      const payload = { fields: [] }
      const result = await publishNewVersion('f1', payload as any)
      expect(http.post).toHaveBeenCalledWith('/forms/f1/versions', payload)
      expect(result).toEqual(mockFormDetail)
    })
  })
})
