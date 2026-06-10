import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import { http } from '@/services/api/http'
import {
  createAssetType,
  deactivateAssetType,
  fetchAssetType,
  fetchAssetTypes,
  updateAssetType,
} from '@/services/asset-types.service'

const mockType = {
  id: 'at1',
  name: 'Veículo',
  description: 'Frota',
  attributes_schema: { placa: 'string' },
  is_active: true,
}
const mockMeta = { page: 1, page_size: 20, total: 1, total_pages: 1, has_next: false }

beforeEach(() => vi.clearAllMocks())

describe('asset-types.service', () => {
  describe('fetchAssetTypes', () => {
    it('gets /asset-types with default pagination and returns envelope', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockType], meta: mockMeta } })
      const result = await fetchAssetTypes()
      expect(http.get).toHaveBeenCalledWith('/asset-types', {
        params: { page: 1, page_size: 20 },
      })
      expect(result.data).toEqual([mockType])
    })

    it('passes is_active filter when provided', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [], meta: mockMeta } })
      await fetchAssetTypes(2, 5, false)
      expect(http.get).toHaveBeenCalledWith('/asset-types', {
        params: { page: 2, page_size: 5, is_active: false },
      })
    })
  })

  describe('fetchAssetType', () => {
    it('gets /asset-types/:id and returns the type', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockType } })
      const result = await fetchAssetType('at1')
      expect(http.get).toHaveBeenCalledWith('/asset-types/at1')
      expect(result).toEqual(mockType)
    })
  })

  describe('createAssetType', () => {
    it('posts to /asset-types with payload and returns the type', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockType } })
      const payload = {
        name: 'Veículo',
        description: 'Frota',
        attributes_schema: { placa: 'string' },
      }
      const result = await createAssetType(payload)
      expect(http.post).toHaveBeenCalledWith('/asset-types', payload)
      expect(result).toEqual(mockType)
    })
  })

  describe('updateAssetType', () => {
    it('patches /asset-types/:id with payload and returns updated type', async () => {
      const updated = { ...mockType, name: 'Equipamento' }
      vi.mocked(http.patch).mockResolvedValue({ data: { data: updated } })
      const result = await updateAssetType('at1', { name: 'Equipamento' })
      expect(http.patch).toHaveBeenCalledWith('/asset-types/at1', { name: 'Equipamento' })
      expect(result).toEqual(updated)
    })
  })

  describe('deactivateAssetType', () => {
    it('deletes /asset-types/:id', async () => {
      vi.mocked(http.delete).mockResolvedValue({ data: {} })
      await deactivateAssetType('at1')
      expect(http.delete).toHaveBeenCalledWith('/asset-types/at1')
    })
  })
})
