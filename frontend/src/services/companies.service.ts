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
