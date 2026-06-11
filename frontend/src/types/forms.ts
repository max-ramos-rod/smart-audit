export type FieldType = 'boolean' | 'text' | 'number' | 'date' | 'select' | 'section'

export interface FormField {
  id: string
  key: string
  label: string
  field_type: FieldType
  required: boolean
  position: number
  config_json: Record<string, unknown>
  instruction: string | null
  // Escopo de componente (DR-0002). NULL = campo geral; preenchido = repete por componente.
  component_type_id?: string | null
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
  field_type: FieldType
  required: boolean
  position: number
  config_json: Record<string, unknown>
  instruction?: string | null
  // Escopo de componente (DR-0002). NULL/ausente = campo geral.
  component_type_id?: string | null
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
