import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type {
  SubmissionAnswersUpdatePayload,
  SubmissionCreatePayload,
  SubmissionDetail,
  SubmissionListItem,
} from '@/types/submissions'

import { http } from './api/http'

export async function fetchSubmissions(page = 1, pageSize = 20) {
  const response = await http.get<PaginatedEnvelope<SubmissionListItem>>('/submissions', {
    params: { page, page_size: pageSize },
  })
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

export async function finishSubmission(submissionId: string) {
  const response = await http.post<ApiEnvelope<SubmissionDetail>>(
    `/submissions/${submissionId}/finish`,
  )
  return response.data.data
}

export async function exportSubmissionPdf(submissionId: string): Promise<Blob> {
  const response = await http.get(`/submissions/${submissionId}/export`, {
    responseType: 'blob',
  })
  return response.data as Blob
}
