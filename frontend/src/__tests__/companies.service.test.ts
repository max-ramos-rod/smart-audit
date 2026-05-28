import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), patch: vi.fn() },
}))

import { http } from '@/services/api/http'
import { fetchMyCompany, updateMyCompany } from '@/services/companies.service'

const mockCompany = {
  id: 'c1',
  name: 'Acme',
  slug: 'acme',
  plan: 'starter',
  is_active: true,
  cnpj: null,
  timezone: null,
  contact_email: null,
  phone: null,
}

beforeEach(() => vi.clearAllMocks())

describe('companies.service', () => {
  describe('fetchMyCompany', () => {
    it('gets /companies/me and returns company data', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockCompany } })
      const result = await fetchMyCompany()
      expect(http.get).toHaveBeenCalledWith('/companies/me')
      expect(result).toEqual(mockCompany)
    })
  })

  describe('updateMyCompany', () => {
    it('patches /companies/me with payload and returns updated company', async () => {
      const updated = { ...mockCompany, name: 'Acme Corp' }
      vi.mocked(http.patch).mockResolvedValue({ data: { data: updated } })
      const result = await updateMyCompany({ name: 'Acme Corp' })
      expect(http.patch).toHaveBeenCalledWith('/companies/me', { name: 'Acme Corp' })
      expect(result).toEqual(updated)
    })
  })
})
