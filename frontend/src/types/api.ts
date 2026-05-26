export interface ApiEnvelope<T> {
  data: T
  meta: Record<string, unknown>
}

export interface PaginationMeta {
  total: number
  page: number
  page_size: number
  has_next: boolean
  total_pages: number
}

export interface PaginatedEnvelope<T> {
  data: T[]
  meta: PaginationMeta
}

export interface ProblemDetails {
  type: string
  title: string
  status: number
  detail: string
  instance: string
}
