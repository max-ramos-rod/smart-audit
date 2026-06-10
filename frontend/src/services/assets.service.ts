import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type {
  Asset,
  AssetCreatePayload,
  AssetDetail,
  AssetListFilters,
  AssetUpdatePayload,
} from '@/types/assets'

import { http } from './api/http'

export async function fetchAssets(page = 1, pageSize = 20, filters: AssetListFilters = {}) {
  const params: Record<string, unknown> = { page, page_size: pageSize }
  if (filters.asset_type_id) params.asset_type_id = filters.asset_type_id
  if (filters.client_id) params.client_id = filters.client_id
  if (filters.parent_asset_id) params.parent_asset_id = filters.parent_asset_id
  if (filters.status) params.status = filters.status
  const response = await http.get<PaginatedEnvelope<Asset>>('/assets', { params })
  return response.data
}

export async function fetchAsset(assetId: string) {
  const response = await http.get<ApiEnvelope<AssetDetail>>(`/assets/${assetId}`)
  return response.data.data
}

export async function createAsset(payload: AssetCreatePayload) {
  const response = await http.post<ApiEnvelope<AssetDetail>>('/assets', payload)
  return response.data.data
}

export async function updateAsset(assetId: string, payload: AssetUpdatePayload) {
  const response = await http.patch<ApiEnvelope<AssetDetail>>(`/assets/${assetId}`, payload)
  return response.data.data
}

export async function deactivateAsset(assetId: string): Promise<void> {
  await http.delete(`/assets/${assetId}`)
}
