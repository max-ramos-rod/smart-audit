import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/api/http', () => ({
  http: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}))

import { http } from '@/services/api/http'
import {
  addTeamMember,
  createTeam,
  deleteTeam,
  fetchTeam,
  fetchTeams,
  removeTeamMember,
  updateTeam,
} from '@/services/teams.service'

const mockListItem = { id: 't1', name: 'Alpha Team', member_count: 3 }
const mockTeam = { id: 't1', name: 'Alpha Team', members: [], created_at: '2024-01-01T00:00:00Z' }
const mockMeta = { page: 1, page_size: 20, total: 1, total_pages: 1, has_next: false }

beforeEach(() => vi.clearAllMocks())

describe('teams.service', () => {
  describe('fetchTeams', () => {
    it('gets /teams with default pagination and returns envelope', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [mockListItem], meta: mockMeta } })
      const result = await fetchTeams()
      expect(http.get).toHaveBeenCalledWith('/teams', { params: { page: 1, page_size: 20 } })
      expect(result.data).toEqual([mockListItem])
    })

    it('passes custom pagination params', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: [], meta: mockMeta } })
      await fetchTeams(2, 5)
      expect(http.get).toHaveBeenCalledWith('/teams', { params: { page: 2, page_size: 5 } })
    })
  })

  describe('fetchTeam', () => {
    it('gets /teams/:id and returns team', async () => {
      vi.mocked(http.get).mockResolvedValue({ data: { data: mockTeam } })
      const result = await fetchTeam('t1')
      expect(http.get).toHaveBeenCalledWith('/teams/t1')
      expect(result).toEqual(mockTeam)
    })
  })

  describe('createTeam', () => {
    it('posts to /teams with payload and returns team', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockTeam } })
      const result = await createTeam({ name: 'Alpha Team' })
      expect(http.post).toHaveBeenCalledWith('/teams', { name: 'Alpha Team' })
      expect(result).toEqual(mockTeam)
    })
  })

  describe('updateTeam', () => {
    it('patches /teams/:id with payload and returns updated team', async () => {
      const updated = { ...mockTeam, name: 'Beta Team' }
      vi.mocked(http.patch).mockResolvedValue({ data: { data: updated } })
      const result = await updateTeam('t1', { name: 'Beta Team' })
      expect(http.patch).toHaveBeenCalledWith('/teams/t1', { name: 'Beta Team' })
      expect(result).toEqual(updated)
    })
  })

  describe('deleteTeam', () => {
    it('deletes /teams/:id', async () => {
      vi.mocked(http.delete).mockResolvedValue({ data: {} })
      await deleteTeam('t1')
      expect(http.delete).toHaveBeenCalledWith('/teams/t1')
    })
  })

  describe('addTeamMember', () => {
    it('posts to /teams/:teamId/members with user_id and returns updated team', async () => {
      vi.mocked(http.post).mockResolvedValue({ data: { data: mockTeam } })
      const result = await addTeamMember('t1', 'u1')
      expect(http.post).toHaveBeenCalledWith('/teams/t1/members', { user_id: 'u1' })
      expect(result).toEqual(mockTeam)
    })
  })

  describe('removeTeamMember', () => {
    it('deletes /teams/:teamId/members/:userId and returns updated team', async () => {
      vi.mocked(http.delete).mockResolvedValue({ data: { data: mockTeam } })
      const result = await removeTeamMember('t1', 'u1')
      expect(http.delete).toHaveBeenCalledWith('/teams/t1/members/u1')
      expect(result).toEqual(mockTeam)
    })
  })
})
