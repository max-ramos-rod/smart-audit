import type { PaginatedEnvelope } from '@/types/api'

import { http } from './api/http'

export interface AuditLogItem {
  id: string
  company_id: string
  actor_id: string
  target_user_id: string | null
  action: string
  meta: Record<string, unknown> | null
  created_at: string
}

export async function fetchAuditLogs(page = 1, pageSize = 30, action?: string) {
  const params: Record<string, unknown> = { page, page_size: pageSize }
  if (action) params.action = action
  const res = await http.get<PaginatedEnvelope<AuditLogItem>>('/audit-logs', { params })
  return res.data
}
