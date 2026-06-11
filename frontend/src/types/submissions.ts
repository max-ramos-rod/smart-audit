import type { FieldType } from '@/types/forms'

export interface SubmissionAnswer {
  field_key: string
  field_type: FieldType
  value: boolean | number | string | Record<string, unknown> | null
  // Componente respondido (DR-0002 T8). NULL = campo geral.
  asset_id?: string | null
}

// Identidade de um componente expandido (DR-0002 T3). Vinda da árvore viva do ativo.
export interface ComponentInstance {
  asset_id: string
  label: string
  type: string
  path: string
}

// Item do checklist expandido. `components` vazio = campo geral (uma instância). (DR-0002 T3/T8)
export interface ChecklistField {
  field_key: string
  field_type: FieldType
  component_type_id: string | null
  components: ComponentInstance[]
}

export interface SubmissionListItem {
  id: string
  form_id: string
  form_name: string
  asset_id: string | null
  asset_identifier: string | null
  status: string
  score: number | null
  started_at: string
  finished_at: string | null
}

export interface ScoreBreakdown {
  total_boolean: number
  conformes: number
  nao_conformes: number
  sem_resposta: number
  na_count: number
}

export interface ConformityItem {
  field_key: string
  status: 'conforme' | 'nao_conforme'
  justification: string | null
  // Componente avaliado (DR-0002 T8). NULL = campo geral.
  asset_id?: string | null
}

export interface ConformityInputItem {
  field_key: string
  status: 'conforme' | 'nao_conforme'
  justification?: string | null
  // Componente avaliado (DR-0002 T8). NULL/ausente = campo geral.
  asset_id?: string | null
}

export interface ConformityUpdatePayload {
  items: ConformityInputItem[]
}

export interface SubmissionDetail extends SubmissionListItem {
  form_version_id: string
  score_breakdown: ScoreBreakdown | null
  answers: SubmissionAnswer[]
  conformity: ConformityItem[]
  // Checklist expandido por componente (DR-0002 T3/T8). Ausente em respostas legadas/sem ativo.
  checklist?: ChecklistField[]
  // Avisos não-bloqueantes da expansão (Q2: sem componentes; Q3: campo escopado sem ativo).
  warnings?: string[]
}

export interface SubmissionCreatePayload {
  form_id: string
  asset_id?: string | null
}

export interface SubmissionAnswerPayload {
  field_key: string
  value: boolean | number | string | Record<string, unknown> | null
  // Componente respondido (DR-0002 T8). Omitido = campo geral.
  asset_id?: string | null
}

export interface SubmissionAnswersUpdatePayload {
  answers: SubmissionAnswerPayload[]
}
