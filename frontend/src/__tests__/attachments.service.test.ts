import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { post: vi.fn() },
}))

import { http } from '@/services/api/http'
import { createAttachment } from '@/services/attachments.service'

const mockAttachment = {
  id: 'a1',
  submission_id: 's1',
  field_key: 'foto_extintor',
  file_url: 'https://files.example.com/extintor.jpg',
  thumbnail_url: null,
  mime_type: 'image/jpeg',
  file_size: 20480,
  created_at: '2024-01-01T00:00:00Z',
}

beforeEach(() => vi.clearAllMocks())

describe('attachments.service', () => {
  describe('createAttachment', () => {
    it('posts to /submissions/:id/attachments with payload and returns attachment', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockAttachment } })
      const payload = {
        field_key: 'foto_extintor',
        file_url: 'https://files.example.com/extintor.jpg',
        mime_type: 'image/jpeg',
        file_size: 20480,
      }
      const result = await createAttachment('s1', payload)
      expect(http.post).toHaveBeenCalledWith('/submissions/s1/attachments', payload)
      expect(result).toEqual(mockAttachment)
    })

    it('forwards asset_id for per-component evidence (DR-0017)', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockAttachment } })
      const payload = {
        field_key: 'pressao',
        asset_id: 'roda-dd',
        file_url: 'https://files.example.com/pneu.jpg',
        mime_type: 'image/jpeg',
        file_size: 1024,
      }
      await createAttachment('s1', payload)
      expect(http.post).toHaveBeenCalledWith('/submissions/s1/attachments', payload)
    })
  })
})
