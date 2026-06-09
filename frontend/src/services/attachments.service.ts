import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type { AttachmentCreatePayload, AttachmentItem } from '@/types/attachments'

import { http } from './api/http'

export async function listAttachments(submissionId: string): Promise<AttachmentItem[]> {
  const response = await http.get<PaginatedEnvelope<AttachmentItem>>(
    `/submissions/${submissionId}/attachments`,
    { params: { page: 1, page_size: 100 } },
  )
  return response.data.data
}

export async function createAttachment(
  submissionId: string,
  payload: AttachmentCreatePayload,
): Promise<AttachmentItem> {
  const response = await http.post<ApiEnvelope<AttachmentItem>>(
    `/submissions/${submissionId}/attachments`,
    payload,
  )
  return response.data.data
}

export async function deleteAttachment(submissionId: string, attachmentId: string): Promise<void> {
  await http.delete(`/submissions/${submissionId}/attachments/${attachmentId}`)
}
