import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/clients.service', () => ({
  fetchClients: vi.fn(),
  createClient: vi.fn(),
  updateClient: vi.fn(),
  deactivateClient: vi.fn(),
}))

import {
  createClient,
  deactivateClient,
  fetchClients,
  updateClient,
} from '@/services/clients.service'
import { useClientsStore } from '@/stores/clients/clients.store'
import type { Client } from '@/types/clients'

const mockClient: Client = { id: 'cl1', name: 'Transportadora Alfa', is_active: true }
const mockPaginatedResponse = {
  data: [mockClient],
  meta: { total: 1, page: 1, page_size: 20, has_next: false, total_pages: 1 },
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

describe('clients.store', () => {
  it('starts with empty state', () => {
    const store = useClientsStore()
    expect(store.items).toEqual([])
    expect(store.meta).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.isSaving).toBe(false)
    expect(store.error).toBeNull()
  })

  describe('load', () => {
    it('populates items and meta on success', async () => {
      vi.mocked(fetchClients).mockResolvedValue(mockPaginatedResponse)
      const store = useClientsStore()

      await store.load()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].name).toBe('Transportadora Alfa')
      expect(store.meta?.total).toBe(1)
      expect(store.isLoading).toBe(false)
    })

    it('passes page, pageSize and is_active to service', async () => {
      vi.mocked(fetchClients).mockResolvedValue(mockPaginatedResponse)
      const store = useClientsStore()

      await store.load(3, 10, true)

      expect(fetchClients).toHaveBeenCalledWith(3, 10, true)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Acesso negado.' } } }
      vi.mocked(fetchClients).mockRejectedValue(err)
      const store = useClientsStore()

      await expect(store.load()).rejects.toBe(err)
      expect(store.error).toBe('Acesso negado.')
      expect(store.isLoading).toBe(false)
    })
  })

  describe('create', () => {
    it('calls createClient, reloads list, and returns created client', async () => {
      vi.mocked(createClient).mockResolvedValue(mockClient)
      vi.mocked(fetchClients).mockResolvedValue(mockPaginatedResponse)
      const store = useClientsStore()

      const result = await store.create({ name: 'Transportadora Alfa' })

      expect(createClient).toHaveBeenCalledWith({ name: 'Transportadora Alfa' })
      expect(fetchClients).toHaveBeenCalled()
      expect(result).toEqual(mockClient)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Nome invalido.' } } }
      vi.mocked(createClient).mockRejectedValue(err)
      const store = useClientsStore()

      await expect(store.create({ name: 'X' })).rejects.toBe(err)
      expect(store.error).toBe('Nome invalido.')
      expect(store.isSaving).toBe(false)
    })
  })

  describe('update', () => {
    it('calls updateClient, reloads list, and returns updated client', async () => {
      const updated: Client = { ...mockClient, name: 'Transportadora Beta' }
      vi.mocked(updateClient).mockResolvedValue(updated)
      vi.mocked(fetchClients).mockResolvedValue(mockPaginatedResponse)
      const store = useClientsStore()

      const result = await store.update('cl1', { name: 'Transportadora Beta' })

      expect(updateClient).toHaveBeenCalledWith('cl1', { name: 'Transportadora Beta' })
      expect(result).toEqual(updated)
      expect(store.isSaving).toBe(false)
    })
  })

  describe('deactivate', () => {
    it('calls deactivateClient and reloads list', async () => {
      vi.mocked(deactivateClient).mockResolvedValue(undefined)
      vi.mocked(fetchClients).mockResolvedValue(mockPaginatedResponse)
      const store = useClientsStore()

      await store.deactivate('cl1')

      expect(deactivateClient).toHaveBeenCalledWith('cl1')
      expect(fetchClients).toHaveBeenCalled()
      expect(store.isSaving).toBe(false)
    })
  })
})
