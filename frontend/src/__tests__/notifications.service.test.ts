import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn() },
}))

import { http } from '@/services/api/http'
import { fetchNotifications } from '@/services/notifications.service'

const mockNotifications = [
  {
    id: 'n1',
    type: 'pending' as const,
    title: 'Inspeção pendente',
    description: 'Você tem 1 inspeção em andamento',
    created_at: '2024-01-01T00:00:00Z',
    read: false,
  },
]

beforeEach(() => vi.clearAllMocks())

describe('notifications.service', () => {
  describe('fetchNotifications', () => {
    it('gets /me/notifications and returns array', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockNotifications } })
      const result = await fetchNotifications()
      expect(http.get).toHaveBeenCalledWith('/me/notifications')
      expect(result).toEqual(mockNotifications)
    })

    it('returns empty array when there are no notifications', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [] } })
      const result = await fetchNotifications()
      expect(result).toEqual([])
    })
  })
})
