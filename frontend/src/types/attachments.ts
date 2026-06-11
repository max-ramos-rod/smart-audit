export interface AttachmentCreatePayload {
  // field_key ausente => evidência da inspeção; +asset_id => evidência por componente (DR-0017).
  field_key?: string | null
  asset_id?: string | null
  file_url: string
  mime_type: string
  file_size: number
  thumbnail_url?: string | null
  metadata_json?: Record<string, unknown> | null
}

export interface AttachmentItem {
  id: string
  submission_id: string | null
  scope: string
  field_key: string | null
  asset_id?: string | null
  component_label?: string | null
  file_url: string
  thumbnail_url: string | null
  mime_type: string
  file_size: number
  metadata_json?: Record<string, unknown> | null
  created_at: string
}
