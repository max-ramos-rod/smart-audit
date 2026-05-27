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
