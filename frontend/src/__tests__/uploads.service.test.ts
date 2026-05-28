import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { post: vi.fn() },
}))

import { http } from '@/services/api/http'
import { uploadFile } from '@/services/uploads.service'

const mockUploadResult = {
  url: '/uploads/c1/abc.jpg',
  mime_type: 'image/jpeg',
  file_size: 10240,
}

beforeEach(() => vi.clearAllMocks())

describe('uploads.service', () => {
  describe('uploadFile', () => {
    it('posts to /uploads with FormData and returns upload result', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockUploadResult } })
      const file = new File(['content'], 'photo.jpg', { type: 'image/jpeg' })

      const result = await uploadFile(file)

      expect(http.post).toHaveBeenCalledOnce()
      const [url, body] = vi.mocked(http.post).mock.calls[0]
      expect(url).toBe('/uploads')
      expect(body).toBeInstanceOf(FormData)
      expect((body as FormData).get('file')).toBe(file)
      expect(result).toEqual(mockUploadResult)
    })
  })
})
