import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), patch: vi.fn() },
}))

import { http } from '@/services/api/http'
import { fetchMyCompanies, fetchMyContext, fetchMyStats, updateMe } from '@/services/context.service'

const mockCompany = { id: 'c1', name: 'Acme', slug: 'acme', role: 'OWNER' }
const mockContext = { user: { id: 'u1', name: 'Alice', email: 'a@test.com' }, company: mockCompany }
const mockStats = { total_submissions: 10, completed: 8, in_progress: 2, avg_score: 92.5 }

beforeEach(() => vi.clearAllMocks())

describe('context.service', () => {
  describe('fetchMyCompanies', () => {
    it('gets /me/companies and returns array', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockCompany] } })
      const result = await fetchMyCompanies()
      expect(http.get).toHaveBeenCalledWith('/me/companies')
      expect(result).toEqual([mockCompany])
    })
  })

  describe('fetchMyContext', () => {
    it('gets /me/context without header when no companyId', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockContext } })
      const result = await fetchMyContext()
      expect(http.get).toHaveBeenCalledWith('/me/context', { headers: {} })
      expect(result).toEqual(mockContext)
    })

    it('gets /me/context with X-Company-Id header when companyId provided', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockContext } })
      await fetchMyContext('c1')
      expect(http.get).toHaveBeenCalledWith('/me/context', {
        headers: { 'X-Company-Id': 'c1' },
      })
    })
  })

  describe('fetchMyStats', () => {
    it('gets /me/stats without params when period is undefined', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockStats } })
      const result = await fetchMyStats()
      expect(http.get).toHaveBeenCalledWith('/me/stats', { params: {} })
      expect(result).toEqual(mockStats)
    })

    it('gets /me/stats without params when period is "all"', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockStats } })
      await fetchMyStats('all')
      expect(http.get).toHaveBeenCalledWith('/me/stats', { params: {} })
    })

    it('gets /me/stats with period param when a specific period is set', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockStats } })
      await fetchMyStats('7d')
      expect(http.get).toHaveBeenCalledWith('/me/stats', { params: { period: '7d' } })
    })
  })

  describe('updateMe', () => {
    it('patches /me with payload and returns updated user', async () => {
      const updated = { id: 'u1', name: 'Bob', email: 'a@test.com' }
      vi.mocked(http.patch).mockResolvedValue({ data: { data: updated } })
      const result = await updateMe({ name: 'Bob' })
      expect(http.patch).toHaveBeenCalledWith('/me', { name: 'Bob' })
      expect(result).toEqual(updated)
    })
  })
})
