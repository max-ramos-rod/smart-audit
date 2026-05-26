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

export async function fetchMyStats() {
  const response = await http.get<ApiEnvelope<CompanyStats>>('/me/stats')
  return response.data.data
}
