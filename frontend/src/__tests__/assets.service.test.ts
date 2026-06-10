import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import { http } from '@/services/api/http'
import {
  createAsset,
  deactivateAsset,
  fetchAsset,
  fetchAssets,
  updateAsset,
} from '@/services/assets.service'

const mockAsset = {
  id: 'a1',
  asset_type_id: 'at1',
  identifier: 'Caminhão 01',
  parent_asset_id: null,
  client_id: 'cl1',
  attributes_json: {},
  status: 'active',
}
const mockMeta = { page: 1, page_size: 20, total: 1, total_pages: 1, has_next: false }

beforeEach(() => vi.clearAllMocks())

describe('assets.service', () => {
  describe('fetchAssets', () => {
    it('gets /assets with default pagination and returns envelope', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockAsset], meta: mockMeta } })
      const result = await fetchAssets()
      expect(http.get).toHaveBeenCalledWith('/assets', { params: { page: 1, page_size: 20 } })
      expect(result.data).toEqual([mockAsset])
    })

    it('forwards only the filters that are set', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [], meta: mockMeta } })
      await fetchAssets(2, 5, { status: 'inactive', client_id: 'cl1' })
      expect(http.get).toHaveBeenCalledWith('/assets', {
        params: { page: 2, page_size: 5, status: 'inactive', client_id: 'cl1' },
      })
    })
  })

  describe('fetchAsset', () => {
    it('gets /assets/:id and returns the detail', async () => {
      const detail = { ...mockAsset, components: [] }
      vi.mocked(http.get).mockResolvedValue({ data: { data: detail } })
      const result = await fetchAsset('a1')
      expect(http.get).toHaveBeenCalledWith('/assets/a1')
      expect(result).toEqual(detail)
    })
  })

  describe('createAsset', () => {
    it('posts to /assets with payload and returns the asset', async () => {
      const detail = { ...mockAsset, components: [] }
      vi.mocked(http.post).mockResolvedValue({ data: { data: detail } })
      const payload = { asset_type_id: 'at1', identifier: 'Caminhão 01', client_id: 'cl1' }
      const result = await createAsset(payload)
      expect(http.post).toHaveBeenCalledWith('/assets', payload)
      expect(result).toEqual(detail)
    })
  })

  describe('updateAsset', () => {
    it('patches /assets/:id with payload and returns updated asset', async () => {
      const detail = { ...mockAsset, identifier: 'Caminhão 02', components: [] }
      vi.mocked(http.patch).mockResolvedValue({ data: { data: detail } })
      const result = await updateAsset('a1', { identifier: 'Caminhão 02' })
      expect(http.patch).toHaveBeenCalledWith('/assets/a1', { identifier: 'Caminhão 02' })
      expect(result).toEqual(detail)
    })
  })

  describe('deactivateAsset', () => {
    it('deletes /assets/:id', async () => {
      vi.mocked(http.delete).mockResolvedValue({ data: {} })
      await deactivateAsset('a1')
      expect(http.delete).toHaveBeenCalledWith('/assets/a1')
    })
  })
})
