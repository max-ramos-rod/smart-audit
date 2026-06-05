import type { ApiEnvelope } from '@/types/api'

import { http } from '@/services/api/http'

export interface CompanyData {
  id: string
  name: string
  slug: string
  plan: string
  is_active: boolean
  cnpj: string | null
  timezone: string | null
  contact_email: string | null
  phone: string | null
}

export interface CompanyUpdatePayload {
  name?: string
  cnpj?: string
  timezone?: string
  contact_email?: string
  phone?: string
}

export async function fetchMyCompany(): Promise<CompanyData> {
  const res = await http.get('/companies/me')
  return res.data.data
}

export async function updateMyCompany(payload: CompanyUpdatePayload): Promise<CompanyData> {
  const res = await http.patch('/companies/me', payload)
  return res.data.data
}

export interface UsageStat {
  used:  number
  limit: number
}

export interface UsageData {
  users:                 UsageStat
  forms:                 UsageStat
  submissions_this_month: UsageStat
}

export async function deactivateCompany(): Promise<void> {
  await http.delete('/companies/me')
}

export async function fetchUsage(): Promise<UsageData> {
  const res = await http.get<ApiEnvelope<UsageData>>('/me/usage')
  return res.data.data
}
