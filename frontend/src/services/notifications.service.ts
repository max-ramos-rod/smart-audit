import { http } from '@/services/api/http'

export interface NotificationItem {
  id: string
  type: 'pending' | 'low_score' | 'excellent'
  title: string
  description: string
  created_at: string
  read: boolean
}

export async function fetchNotifications(): Promise<NotificationItem[]> {
  const res = await http.get('/me/notifications')
  return res.data.data
}

export async function markNotificationRead(key: string): Promise<void> {
  await http.post('/me/notifications/read', { key })
}

export async function markAllNotificationsRead(keys: string[]): Promise<void> {
  if (!keys.length) return
  await http.post('/me/notifications/read-all', { keys })
}

export async function dismissNotification(key: string): Promise<void> {
  await http.post('/me/notifications/dismiss', { key })
}

export async function dismissAllNotifications(keys: string[]): Promise<void> {
  if (!keys.length) return
  await http.post('/me/notifications/dismiss-all', { keys })
}
