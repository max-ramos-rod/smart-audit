import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

import { http } from '@/services/api/http'
import { createUser, fetchUser, fetchUsers, updateUser } from '@/services/users.service'

const mockListItem = {
  id: 'u1',
  name: 'Alice',
  email: 'alice@test.com',
  role: 'INSPECTOR',
  is_active: true,
}
const mockDetail = { ...mockListItem, created_at: '2024-01-01T00:00:00Z' }
const mockMeta = { page: 1, page_size: 20, total: 1, total_pages: 1, has_next: false }

beforeEach(() => vi.clearAllMocks())

describe('users.service', () => {
  describe('fetchUsers', () => {
    it('gets /users with default pagination and returns envelope', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockListItem], meta: mockMeta } })
      const result = await fetchUsers()
      expect(http.get).toHaveBeenCalledWith('/users', { params: { page: 1, page_size: 20 } })
      expect(result.data).toEqual([mockListItem])
    })

    it('passes custom page and pageSize', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [], meta: mockMeta } })
      await fetchUsers(2, 5)
      expect(http.get).toHaveBeenCalledWith('/users', { params: { page: 2, page_size: 5 } })
    })
  })

  describe('fetchUser', () => {
    it('gets /users/:id and returns user detail', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockDetail } })
      const result = await fetchUser('u1')
      expect(http.get).toHaveBeenCalledWith('/users/u1')
      expect(result).toEqual(mockDetail)
    })
  })

  describe('createUser', () => {
    it('posts to /users with payload and returns user detail', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockDetail } })
      const payload = {
        name: 'Alice',
        email: 'alice@test.com',
        password: 'pass1234',
        role: 'INSPECTOR',
      }
      const result = await createUser(payload as any)
      expect(http.post).toHaveBeenCalledWith('/users', payload)
      expect(result).toEqual(mockDetail)
    })
  })

  describe('updateUser', () => {
    it('patches /users/:id with payload and returns updated detail', async () => {
      const updated = { ...mockDetail, name: 'Alicia' }
      vi.mocked(http.patch).mockResolvedValue({ data: { data: updated } })
      const result = await updateUser('u1', { name: 'Alicia' })
      expect(http.patch).toHaveBeenCalledWith('/users/u1', { name: 'Alicia' })
      expect(result).toEqual(updated)
    })
  })
})
