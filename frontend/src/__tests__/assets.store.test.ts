import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/assets.service', () => ({
  fetchAssets: vi.fn(),
  fetchAsset: vi.fn(),
  createAsset: vi.fn(),
  updateAsset: vi.fn(),
  deactivateAsset: vi.fn(),
}))

import {
  createAsset,
  deactivateAsset,
  fetchAsset,
  fetchAssets,
  updateAsset,
} from '@/services/assets.service'
import { useAssetsStore } from '@/stores/assets/assets.store'
import type { Asset, AssetDetail } from '@/types/assets'

const mockAsset: Asset = {
  id: 'a1',
  asset_type_id: 'at1',
  identifier: 'Caminhão 01',
  parent_asset_id: null,
  client_id: 'cl1',
  attributes_json: {},
  status: 'active',
}
const mockDetail: AssetDetail = { ...mockAsset, components: [] }
const mockPaginatedResponse = {
  data: [mockAsset],
  meta: { total: 1, page: 1, page_size: 20, has_next: false, total_pages: 1 },
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

describe('assets.store', () => {
  it('starts with empty state and default active filter', () => {
    const store = useAssetsStore()
    expect(store.items).toEqual([])
    expect(store.meta).toBeNull()
    expect(store.detail).toBeNull()
    expect(store.filters).toEqual({ status: 'active' })
    expect(store.isLoading).toBe(false)
  })

  describe('load', () => {
    it('populates items and meta on success', async () => {
      vi.mocked(fetchAssets).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetsStore()

      await store.load()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].identifier).toBe('Caminhão 01')
      expect(store.meta?.total).toBe(1)
    })

    it('stores override filters and forwards them to the service', async () => {
      vi.mocked(fetchAssets).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetsStore()

      await store.load(1, 20, { status: 'inactive', client_id: 'cl1' })

      expect(store.filters).toEqual({ status: 'inactive', client_id: 'cl1' })
      expect(fetchAssets).toHaveBeenCalledWith(1, 20, { status: 'inactive', client_id: 'cl1' })
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Acesso negado.' } } }
      vi.mocked(fetchAssets).mockRejectedValue(err)
      const store = useAssetsStore()

      await expect(store.load()).rejects.toBe(err)
      expect(store.error).toBe('Acesso negado.')
    })
  })

  describe('loadDetail / clearDetail', () => {
    it('loads detail with components and clears it', async () => {
      vi.mocked(fetchAsset).mockResolvedValue(mockDetail)
      const store = useAssetsStore()

      const result = await store.loadDetail('a1')

      expect(fetchAsset).toHaveBeenCalledWith('a1')
      expect(result).toEqual(mockDetail)
      expect(store.detail).toEqual(mockDetail)

      store.clearDetail()
      expect(store.detail).toBeNull()
    })
  })

  describe('create', () => {
    it('calls createAsset, reloads list, and returns created asset', async () => {
      vi.mocked(createAsset).mockResolvedValue(mockDetail)
      vi.mocked(fetchAssets).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetsStore()

      const result = await store.create({ asset_type_id: 'at1', identifier: 'Caminhão 01' })

      expect(createAsset).toHaveBeenCalledWith({ asset_type_id: 'at1', identifier: 'Caminhão 01' })
      expect(fetchAssets).toHaveBeenCalled()
      expect(result).toEqual(mockDetail)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'client_id so e permitido em ativo raiz.' } } }
      vi.mocked(createAsset).mockRejectedValue(err)
      const store = useAssetsStore()

      await expect(
        store.create({ asset_type_id: 'at1', identifier: 'X', parent_asset_id: 'a1', client_id: 'cl1' }),
      ).rejects.toBe(err)
      expect(store.error).toBe('client_id so e permitido em ativo raiz.')
    })
  })

  describe('update', () => {
    it('calls updateAsset, reloads list, and returns updated asset', async () => {
      const updated = { ...mockDetail, identifier: 'Caminhão 02' }
      vi.mocked(updateAsset).mockResolvedValue(updated)
      vi.mocked(fetchAssets).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetsStore()

      const result = await store.update('a1', { identifier: 'Caminhão 02' })

      expect(updateAsset).toHaveBeenCalledWith('a1', { identifier: 'Caminhão 02' })
      expect(result).toEqual(updated)
    })
  })

  describe('deactivate', () => {
    it('calls deactivateAsset and reloads list', async () => {
      vi.mocked(deactivateAsset).mockResolvedValue(undefined)
      vi.mocked(fetchAssets).mockResolvedValue(mockPaginatedResponse)
      const store = useAssetsStore()

      await store.deactivate('a1')

      expect(deactivateAsset).toHaveBeenCalledWith('a1')
      expect(fetchAssets).toHaveBeenCalled()
    })
  })
})
