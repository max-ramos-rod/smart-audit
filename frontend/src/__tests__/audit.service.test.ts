import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn() },
}))

import { http } from '@/services/api/http'
import { fetchAuditLogs } from '@/services/audit.service'

const envelope = {
  data: [
    {
      id: 'a1',
      company_id: 'c1',
      actor_id: 'u1',
      target_user_id: 'u2',
      action: 'user.created',
      meta: { user_name: 'Maria', role: 'VIEWER' },
      created_at: '2026-06-09T00:00:00Z',
    },
  ],
  meta: { total: 1, page: 1, page_size: 30, has_next: false, total_pages: 1 },
}

beforeEach(() => vi.clearAllMocks())

describe('audit.service', () => {
  describe('fetchAuditLogs', () => {
    it('gets /audit-logs with default pagination and returns the envelope', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: envelope })
      const result = await fetchAuditLogs()
      expect(http.get).toHaveBeenCalledWith('/audit-logs', {
        params: { page: 1, page_size: 30 },
      })
      expect(result).toEqual(envelope)
    })

    it('forwards custom page and page_size', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: envelope })
      await fetchAuditLogs(2, 50)
      expect(http.get).toHaveBeenCalledWith('/audit-logs', {
        params: { page: 2, page_size: 50 },
      })
    })

    it('includes the action filter when provided', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: envelope })
      await fetchAuditLogs(1, 30, 'membership.revoked')
      expect(http.get).toHaveBeenCalledWith('/audit-logs', {
        params: { page: 1, page_size: 30, action: 'membership.revoked' },
      })
    })
  })
})
