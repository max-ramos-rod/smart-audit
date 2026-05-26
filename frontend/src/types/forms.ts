export interface FormField {
  id: string
  key: string
  label: string
  field_type: string
  required: boolean
  position: number
  config_json: Record<string, unknown>
}

export interface FormVersion {
  id: string
  version: number
  status: string
  published_at: string | null
  fields: FormField[]
}

export interface FormListItem {
  id: string
  company_id: string
  name: string
  description: string | null
  is_active: boolean
  current_version_number: number
  current_version_status: string
  published_at: string | null
}

export interface FormDetail {
  id: string
  company_id: string
  name: string
  description: string | null
  is_active: boolean
  current_version: FormVersion
}

export interface FormFieldCreatePayload {
  key: string
  label: string
  field_type: string
  required: boolean
  position: number
  config_json: Record<string, unknown>
}

export interface FormCreatePayload {
  name: string
  description?: string | null
  fields: FormFieldCreatePayload[]
}

export interface FormVersionPublishPayload {
  fields: FormFieldCreatePayload[]
}

export interface FormVersionListItem {
  id: string
  version: number
  status: string
  published_at: string | null
  fields_count: number
}
