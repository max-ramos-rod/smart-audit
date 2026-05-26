export interface SubmissionAnswer {
  field_key: string
  field_type: string
  value: boolean | number | string | Record<string, unknown> | null
}

export interface SubmissionListItem {
  id: string
  form_id: string
  form_name: string
  status: string
  score: number | null
  started_at: string
  finished_at: string | null
}

export interface SubmissionDetail extends SubmissionListItem {
  form_version_id: string
  answers: SubmissionAnswer[]
}

export interface SubmissionCreatePayload {
  form_id: string
}

export interface SubmissionAnswerPayload {
  field_key: string
  value: boolean | number | string | Record<string, unknown> | null
}

export interface SubmissionAnswersUpdatePayload {
  answers: SubmissionAnswerPayload[]
}
