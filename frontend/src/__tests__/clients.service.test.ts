import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import { http } from '@/services/api/http'
import {
  createClient,
  deactivateClient,
  fetchClient,
  fetchClients,
  updateClient,
} from '@/services/clients.service'

const mockClient = { id: 'cl1', name: 'Transportadora Alfa', is_active: true }
const mockMeta = { page: 1, page_size: 20, total: 1, total_pages: 1, has_next: false }

beforeEach(() => vi.clearAllMocks())

describe('clients.service', () => {
  describe('fetchClients', () => {
    it('gets /clients with default pagination and returns envelope', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockClient], meta: mockMeta } })
      const result = await fetchClients()
      expect(http.get).toHaveBeenCalledWith('/clients', { params: { page: 1, page_size: 20 } })
      expect(result.data).toEqual([mockClient])
    })

    it('passes is_active filter when provided', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [], meta: mockMeta } })
      await fetchClients(2, 5, false)
      expect(http.get).toHaveBeenCalledWith('/clients', {
        params: { page: 2, page_size: 5, is_active: false },
      })
    })
  })

  describe('fetchClient', () => {
    it('gets /clients/:id and returns client', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockClient } })
      const result = await fetchClient('cl1')
      expect(http.get).toHaveBeenCalledWith('/clients/cl1')
      expect(result).toEqual(mockClient)
    })
  })

  describe('createClient', () => {
    it('posts to /clients with payload and returns client', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockClient } })
      const result = await createClient({ name: 'Transportadora Alfa' })
      expect(http.post).toHaveBeenCalledWith('/clients', { name: 'Transportadora Alfa' })
      expect(result).toEqual(mockClient)
    })
  })

  describe('updateClient', () => {
    it('patches /clients/:id with payload and returns updated client', async () => {
      const updated = { ...mockClient, name: 'Transportadora Beta' }
      vi.mocked(http.patch).mockResolvedValue({ data: { data: updated } })
      const result = await updateClient('cl1', { name: 'Transportadora Beta' })
      expect(http.patch).toHaveBeenCalledWith('/clients/cl1', { name: 'Transportadora Beta' })
      expect(result).toEqual(updated)
    })
  })

  describe('deactivateClient', () => {
    it('deletes /clients/:id', async () => {
      vi.mocked(http.delete).mockResolvedValue({ data: {} })
      await deactivateClient('cl1')
      expect(http.delete).toHaveBeenCalledWith('/clients/cl1')
    })
  })
})
