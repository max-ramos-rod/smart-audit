import type { ApiEnvelope } from '@/types/api'
import type { CompanyStats, UserCompany, UserContext } from '@/types/context'

import { http } from './api/http'

export async function fetchMyCompanies() {
  const response = await http.get<ApiEnvelope<UserCompany[]>>('/me/companies')
  return response.data.data
}

export async function fetchMyContext(companyId?: string | null) {
  const response = await http.get<ApiEnvelope<UserContext>>('/me/context', {
    headers: companyId ? { 'X-Company-Id': companyId } : {},
  })
  return response.data.data
}

export async function fetchMyStats(period?: string) {
  const params = period && period !== 'all' ? { period } : {}
  const response = await http.get<ApiEnvelope<CompanyStats>>('/me/stats', { params })
  return response.data.data
}

export interface MeUpdatePayload {
  name?: string
  password?: string
}

export async function updateMe(payload: MeUpdatePayload) {
  const response = await http.patch<ApiEnvelope<{ id: string; name: string; email: string }>>(
    '/me',
    payload,
  )
  return response.data.data
}
