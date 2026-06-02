// Smart Audit Types - Seguindo DER_Smart_Audit.md

// =========================================
// FORM FIELDS - Tipos de campo conforme DER
// =========================================

export type FieldType = 
  | 'boolean'   // value_boolean - Aceita true, false ou "na" (com allow_na)
  | 'text'      // value_text - String livre
  | 'number'    // value_number - Float
  | 'date'      // value_date - ISO 8601
  | 'select'    // value_json - { "option": "valor" }
  | 'photo'     // value_text - URL do arquivo
  | 'evidence'  // value_json - Metadados de múltiplos arquivos
  | 'section'   // Divisor visual - não gera submission_value

// Configuração de campo via config_json
export interface FieldConfigVisibleIf {
  field_key: string
  operator: 'eq' | 'neq'
  value: boolean | string | number
}

export interface FieldConfig {
  weight?: number          // Peso no cálculo do score (default 1.0)
  allow_na?: boolean       // Habilita resposta N/A em booleanos
  options?: string[]       // Opções do select
  visible_if?: FieldConfigVisibleIf // Regra de visibilidade condicional
}

// =========================================
// FORM STRUCTURE
// =========================================

export interface FormField {
  id: string
  form_version_id: string
  key: string
  label: string
  field_type: FieldType
  required: boolean
  position: number
  config_json: FieldConfig
  created_at: string
  updated_at: string
}

export interface FormVersion {
  id: string
  form_id: string
  version: number
  status: 'draft' | 'published' | 'archived'
  published_at: string | null
  created_by: string
  fields: FormField[]
  created_at: string
  updated_at: string
}

export interface Form {
  id: string
  company_id: string
  name: string
  description: string | null
  is_active: boolean
  created_by: string
  current_version?: FormVersion
  created_at: string
  updated_at: string
}

// =========================================
// SUBMISSION VALUES - Respostas tipadas
// =========================================

// Valor bruto de uma resposta (conforme tipo de campo)
export type FieldValue = 
  | boolean           // boolean field
  | 'na'              // boolean com allow_na
  | string            // text, photo
  | number            // number
  | { option: string } // select
  | Date | string     // date
  | EvidenceMetadata[] // evidence
  | null

export interface SubmissionValue {
  id: string
  submission_id: string
  form_field_id: string
  value_text: string | null
  value_number: number | null
  value_boolean: boolean | null
  value_date: string | null
  value_json: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

// =========================================
// ATTACHMENTS - Evidências
// =========================================

export type AttachmentMimeType = 
  | 'image/jpeg' 
  | 'image/png' 
  | 'image/webp'
  | 'video/mp4' 
  | 'video/quicktime' 
  | 'video/x-msvideo'
  | 'audio/mpeg' 
  | 'audio/wav' 
  | 'audio/ogg' 
  | 'audio/m4a'
  | 'application/pdf'

export interface Attachment {
  id: string
  submission_value_id: string
  field_key: string
  file_url: string
  thumbnail_url: string | null
  mime_type: AttachmentMimeType
  file_size: number
  uploaded_by: string
  created_at: string
  updated_at: string
}

// Metadados de evidência para campo tipo 'evidence'
export interface EvidenceMetadata {
  id: string
  type: 'photo' | 'video' | 'audio' | 'pdf' | 'note'
  url?: string
  content?: string // Para notas de texto
  filename?: string
  file_size?: number
  created_at: string
}

// =========================================
// SUBMISSION - Inspeção
// =========================================

export type SubmissionStatus = 'draft' | 'in_progress' | 'completed' | 'cancelled'

// Score breakdown conforme Arquitetura_Smart_Audit.md
export interface ScoreBreakdown {
  conformes: number
  nao_conformes: number
  sem_resposta: number
  na_count: number
  total_boolean: number
}

export interface Submission {
  id: string
  company_id: string
  form_version_id: string
  created_by: string
  status: SubmissionStatus
  score: number | null
  score_breakdown?: ScoreBreakdown
  started_at: string
  finished_at: string | null
  answers_json: Record<string, FieldValue> // Snapshot { field_key: value }
  created_at: string
  updated_at: string
}

// =========================================
// UI HELPERS - Para a interface
// =========================================

// Estado visual de um campo na UI
export type FieldStatus = 'pending' | 'compliant' | 'non_compliant' | 'na'

// Item achatado para lista virtualizada
export interface FlatListItem {
  type: 'section' | 'field'
  id: string
  field?: FormField
  sectionLabel?: string
  depth: number
  visible: boolean
}

// Respostas em draft (antes de salvar)
export type DraftAnswers = Record<string, FieldValue>

// Evidências pendentes de upload
export interface PendingEvidence {
  field_key: string
  type: EvidenceMetadata['type']
  file?: File
  content?: string
  tempId: string
}

// =========================================
// NAVIGATION
// =========================================

// Seção para navegação rápida
export interface SectionJump {
  fieldId: string
  label: string
  position: number
  answeredCount: number
  totalCount: number
}

// Progresso da inspeção
export interface InspectionProgress {
  total: number
  answered: number
  compliant: number
  nonCompliant: number
  na: number
  percentage: number
}
