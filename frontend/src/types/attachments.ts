export interface AttachmentCreatePayload {
  field_key: string
  file_url: string
  mime_type: string
  file_size: number
  thumbnail_url?: string | null
}

export interface AttachmentItem {
  id: string
  submission_id: string
  field_key: string
  file_url: string
  thumbnail_url: string | null
  mime_type: string
  file_size: number
  created_at: string
}
