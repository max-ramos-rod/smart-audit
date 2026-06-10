import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type { Client, ClientCreatePayload, ClientUpdatePayload } from '@/types/clients'

import { http } from './api/http'

export async function fetchClients(page = 1, pageSize = 20, isActive?: boolean) {
  const params: Record<string, unknown> = { page, page_size: pageSize }
  if (isActive !== undefined) params.is_active = isActive
  const response = await http.get<PaginatedEnvelope<Client>>('/clients', { params })
  return response.data
}

export async function fetchClient(clientId: string) {
  const response = await http.get<ApiEnvelope<Client>>(`/clients/${clientId}`)
  return response.data.data
}

export async function createClient(payload: ClientCreatePayload) {
  const response = await http.post<ApiEnvelope<Client>>('/clients', payload)
  return response.data.data
}

export async function updateClient(clientId: string, payload: ClientUpdatePayload) {
  const response = await http.patch<ApiEnvelope<Client>>(`/clients/${clientId}`, payload)
  return response.data.data
}

export async function deactivateClient(clientId: string): Promise<void> {
  await http.delete(`/clients/${clientId}`)
}
