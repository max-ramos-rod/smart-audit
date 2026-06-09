import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn() },
}))

import { http } from '@/services/api/http'
import { fetchSearch } from '@/services/search.service'

const mockResult = {
  forms: [
    {
      id: 'f1',
      name: 'Safety Check',
      current_version_number: 1,
      status: 'published',
      created_at: '',
    },
  ],
  submissions: [],
}

beforeEach(() => vi.clearAllMocks())

describe('search.service', () => {
  describe('fetchSearch', () => {
    it('gets /search with q param and returns search result', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockResult } })
      const result = await fetchSearch('safety')
      expect(http.get).toHaveBeenCalledWith('/search', { params: { q: 'safety' } })
      expect(result).toEqual(mockResult)
    })

    it('returns empty arrays when no results found', async () => {
      const emptyResult = { forms: [], submissions: [] }
      vi.mocked(http.get).mockResolvedValue({ data: { data: emptyResult } })
      const result = await fetchSearch('xyz')
      expect(result.forms).toHaveLength(0)
      expect(result.submissions).toHaveLength(0)
    })
  })
})
