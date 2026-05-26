import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type {
  FormCreatePayload,
  FormDetail,
  FormListItem,
  FormVersion,
  FormVersionPublishPayload,
} from '@/types/forms'

import { http } from './api/http'

export async function fetchForms(page = 1, pageSize = 20) {
  const response = await http.get<PaginatedEnvelope<FormListItem>>('/forms', {
    params: { page, page_size: pageSize },
  })
  return response.data
}

export async function fetchForm(formId: string) {
  const response = await http.get<ApiEnvelope<FormDetail>>(`/forms/${formId}`)
  return response.data.data
}

export async function createForm(payload: FormCreatePayload) {
  const response = await http.post<ApiEnvelope<FormDetail>>('/forms', payload)
  return response.data.data
}

export async function fetchFormVersion(formId: string, versionId: string) {
  const response = await http.get<ApiEnvelope<FormVersion>>(`/forms/${formId}/versions/${versionId}`)
  return response.data.data
}

export async function publishNewVersion(formId: string, payload: FormVersionPublishPayload) {
  const response = await http.post<ApiEnvelope<FormDetail>>(`/forms/${formId}/versions`, payload)
  return response.data.data
}
