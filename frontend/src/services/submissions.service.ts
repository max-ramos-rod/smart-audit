import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type {
  ConformityUpdatePayload,
  SubmissionAnswersUpdatePayload,
  SubmissionCreatePayload,
  SubmissionDetail,
  SubmissionListItem,
} from '@/types/submissions'

import { http } from './api/http'

export async function fetchSubmissions(
  page = 1,
  pageSize = 20,
  status?: string,
  formId?: string,
  createdBy?: string,
) {
  const params: Record<string, unknown> = { page, page_size: pageSize }
  if (status) params.status = status
  if (formId) params.form_id = formId
  if (createdBy) params.created_by = createdBy
  const response = await http.get<PaginatedEnvelope<SubmissionListItem>>('/submissions', { params })
  return response.data
}

export async function fetchSubmission(submissionId: string) {
  const response = await http.get<ApiEnvelope<SubmissionDetail>>(`/submissions/${submissionId}`)
  return response.data.data
}

export async function createSubmission(payload: SubmissionCreatePayload) {
  const response = await http.post<ApiEnvelope<SubmissionDetail>>('/submissions', payload)
  return response.data.data
}

export async function saveAnswers(submissionId: string, payload: SubmissionAnswersUpdatePayload) {
  const response = await http.put<ApiEnvelope<SubmissionDetail>>(
    `/submissions/${submissionId}/answers`,
    payload,
  )
  return response.data.data
}

export async function saveConformity(submissionId: string, payload: ConformityUpdatePayload) {
  const response = await http.put<ApiEnvelope<SubmissionDetail>>(
    `/submissions/${submissionId}/conformity`,
    payload,
  )
  return response.data.data
}

export async function finishSubmission(submissionId: string) {
  const response = await http.post<ApiEnvelope<SubmissionDetail>>(
    `/submissions/${submissionId}/finish`,
  )
  return response.data.data
}

export async function exportSubmissionPdf(
  submissionId: string,
  inline = false,
): Promise<Blob> {
  const response = await http.get(`/submissions/${submissionId}/export`, {
    params: inline ? { inline: 'true' } : {},
    responseType: 'blob',
  })
  return response.data as Blob
}

export async function exportSubmissionsCSV(status?: string, formId?: string): Promise<void> {
  const params: Record<string, string> = {}
  if (status) params.status = status
  if (formId) params.form_id = formId
  const response = await http.get('/submissions/export', { params, responseType: 'blob' })
  const url = URL.createObjectURL(response.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `inspecoes_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
