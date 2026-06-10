import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type {
  AssetType,
  AssetTypeCreatePayload,
  AssetTypeUpdatePayload,
} from '@/types/asset-types'

import { http } from './api/http'

export async function fetchAssetTypes(page = 1, pageSize = 20, isActive?: boolean) {
  const params: Record<string, unknown> = { page, page_size: pageSize }
  if (isActive !== undefined) params.is_active = isActive
  const response = await http.get<PaginatedEnvelope<AssetType>>('/asset-types', { params })
  return response.data
}

export async function fetchAssetType(assetTypeId: string) {
  const response = await http.get<ApiEnvelope<AssetType>>(`/asset-types/${assetTypeId}`)
  return response.data.data
}

export async function createAssetType(payload: AssetTypeCreatePayload) {
  const response = await http.post<ApiEnvelope<AssetType>>('/asset-types', payload)
  return response.data.data
}

export async function updateAssetType(assetTypeId: string, payload: AssetTypeUpdatePayload) {
  const response = await http.patch<ApiEnvelope<AssetType>>(
    `/asset-types/${assetTypeId}`,
    payload,
  )
  return response.data.data
}

export async function deactivateAssetType(assetTypeId: string): Promise<void> {
  await http.delete(`/asset-types/${assetTypeId}`)
}
