import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn() },
}))

import { http } from '@/services/api/http'
import {
  fetchNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '@/services/notifications.service'

const mockNotifications = [
  {
    id: 'excellent-s1',
    type: 'excellent' as const,
    title: 'Inspeção concluída com excelência',
    description: 'Safety Check: score 100%.',
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

  describe('markNotificationRead', () => {
    it('posts to /me/notifications/read with the key', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: { key: 'excellent-s1', read: true } } })
      await markNotificationRead('excellent-s1')
      expect(http.post).toHaveBeenCalledWith('/me/notifications/read', { key: 'excellent-s1' })
    })
  })

  describe('markAllNotificationsRead', () => {
    it('posts to /me/notifications/read-all with keys array', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: { marked: 2 } } })
      await markAllNotificationsRead(['excellent-s1', 'low-score-s2'])
      expect(http.post).toHaveBeenCalledWith('/me/notifications/read-all', {
        keys: ['excellent-s1', 'low-score-s2'],
      })
    })

    it('does not call API when keys array is empty', async () => {
      await markAllNotificationsRead([])
      expect(http.post).not.toHaveBeenCalled()
    })
  })
})
