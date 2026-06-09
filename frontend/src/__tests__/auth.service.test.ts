import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn() },
}))

import { http } from '@/services/api/http'
import { fetchMe, login, requestPasswordReset, resetPassword } from '@/services/auth.service'

const mockUser = { id: 'u1', name: 'Alice', email: 'alice@test.com' }
const mockTokenResponse = {
  access_token: 'tok',
  token_type: 'bearer',
  expires_in: 3600,
  user: mockUser,
}

beforeEach(() => vi.clearAllMocks())

describe('auth.service', () => {
  describe('login', () => {
    it('posts to /auth/login and returns token response', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockTokenResponse } })
      const result = await login({ email: 'alice@test.com', password: 'secret' })
      expect(http.post).toHaveBeenCalledWith('/auth/login', {
        email: 'alice@test.com',
        password: 'secret',
      })
      expect(result).toEqual(mockTokenResponse)
    })
  })

  describe('fetchMe', () => {
    it('gets /auth/me and returns user', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockUser } })
      const result = await fetchMe()
      expect(http.get).toHaveBeenCalledWith('/auth/me')
      expect(result).toEqual(mockUser)
    })
  })

  describe('requestPasswordReset', () => {
    it('posts to /auth/forgot-password with email', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: {} })
      await requestPasswordReset('alice@test.com')
      expect(http.post).toHaveBeenCalledWith('/auth/forgot-password', { email: 'alice@test.com' })
    })
  })

  describe('resetPassword', () => {
    it('posts to /auth/reset-password with token and new_password', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: {} })
      await resetPassword('tkn123', 'newpass99')
      expect(http.post).toHaveBeenCalledWith('/auth/reset-password', {
        token: 'tkn123',
        new_password: 'newpass99',
      })
    })
  })
})
