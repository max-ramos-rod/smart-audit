import type { ApiEnvelope } from '@/types/api'
import type { AttachmentCreatePayload, AttachmentItem } from '@/types/attachments'

import { http } from './api/http'

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
