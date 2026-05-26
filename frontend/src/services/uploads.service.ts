import type { ApiEnvelope } from '@/types/api'

import { http } from './api/http'

export interface UploadResult {
  url: string
  mime_type: string
  file_size: number
}

export async function uploadFile(file: File): Promise<UploadResult> {
  const form = new FormData()
  form.append('file', file)
  const response = await http.post<ApiEnvelope<UploadResult>>('/uploads', form)
  return response.data.data
}
