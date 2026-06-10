import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/asset-types.service', () => ({
  fetchAssetTypes: vi.fn(),
  createAssetType: vi.fn(),
  updateAssetType: vi.fn(),
  deactivateAssetType: vi.fn(),
}))

import {
  createAssetType,
  deactivateAssetType,
  fetchAssetTypes,
  updateAssetType,
} from '@/services/asset-types.service'
import { useAssetTypesStore } from '@/stores/asset-types/asset-types.store'
import type { AssetType } from '@/types/asset-types'

const mockType: AssetType = {
  id: 'at1',
  name: 'Veículo',
  description: 'Frota',
  attributes_schema: { placa: 'string' },
  is_active: true,
}
const mockPaginatedResponse = {
  data: [mockType],
  meta: { total: 1, page: 1, page_size: 20, has_next: false, total_pages: 1 },
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

describe('asset-types.store', () => {
  it('starts with empty state', () => {
    const store = useAssetTypesStore()
    expect(store.items).toEqual([])
    expect(store.meta).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.isSaving).toBe(false)
    expect(store.error).toBeNull()
  })

  describe('load', () => {
    it('populates items and meta on success', async () => {
      vi.mocked(fetchAssetTypes).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetTypesStore()

      await store.load()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].name).toBe('Veículo')
      expect(store.meta?.total).toBe(1)
      expect(store.isLoading).toBe(false)
    })

    it('passes page, pageSize and is_active to service', async () => {
      vi.mocked(fetchAssetTypes).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetTypesStore()

      await store.load(3, 10, true)

      expect(fetchAssetTypes).toHaveBeenCalledWith(3, 10, true)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Acesso negado.' } } }
      vi.mocked(fetchAssetTypes).mockRejectedValue(err)
      const store = useAssetTypesStore()

      await expect(store.load()).rejects.toBe(err)
      expect(store.error).toBe('Acesso negado.')
      expect(store.isLoading).toBe(false)
    })
  })

  describe('create', () => {
    it('calls createAssetType, reloads list, and returns created type', async () => {
      vi.mocked(createAssetType).mockResolvedValue(mockType)
      vi.mocked(fetchAssetTypes).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetTypesStore()

      const result = await store.create({ name: 'Veículo' })

      expect(createAssetType).toHaveBeenCalledWith({ name: 'Veículo' })
      expect(fetchAssetTypes).toHaveBeenCalled()
      expect(result).toEqual(mockType)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Nome invalido.' } } }
      vi.mocked(createAssetType).mockRejectedValue(err)
      const store = useAssetTypesStore()

      await expect(store.create({ name: 'X' })).rejects.toBe(err)
      expect(store.error).toBe('Nome invalido.')
      expect(store.isSaving).toBe(false)
    })
  })

  describe('update', () => {
    it('calls updateAssetType, reloads list, and returns updated type', async () => {
      const updated: AssetType = { ...mockType, name: 'Equipamento' }
      vi.mocked(updateAssetType).mockResolvedValue(updated)
      vi.mocked(fetchAssetTypes).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetTypesStore()

      const result = await store.update('at1', { name: 'Equipamento' })

      expect(updateAssetType).toHaveBeenCalledWith('at1', { name: 'Equipamento' })
      expect(result).toEqual(updated)
      expect(store.isSaving).toBe(false)
    })
  })

  describe('deactivate', () => {
    it('calls deactivateAssetType and reloads list', async () => {
      vi.mocked(deactivateAssetType).mockResolvedValue(undefined)
      vi.mocked(fetchAssetTypes).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetTypesStore()

      await store.deactivate('at1')

      expect(deactivateAssetType).toHaveBeenCalledWith('at1')
      expect(fetchAssetTypes).toHaveBeenCalled()
      expect(store.isSaving).toBe(false)
    })
  })
})
