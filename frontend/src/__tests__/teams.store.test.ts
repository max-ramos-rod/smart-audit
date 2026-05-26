import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/teams.service', () => ({
  fetchTeams: vi.fn(),
  fetchTeam: vi.fn(),
  createTeam: vi.fn(),
  updateTeam: vi.fn(),
  deleteTeam: vi.fn(),
  addTeamMember: vi.fn(),
  removeTeamMember: vi.fn(),
}))

import {
  addTeamMember,
  createTeam,
  deleteTeam,
  fetchTeam,
  fetchTeams,
  removeTeamMember,
  updateTeam,
} from '@/services/teams.service'
import { useTeamsStore } from '@/stores/teams/teams.store'
import type { Team, TeamListItem } from '@/types/teams'

const mockListItem: TeamListItem = {
  id: 't1',
  company_id: 'c1',
  name: 'Auditoria Norte',
  member_count: 2,
}

const mockTeam: Team = {
  id: 't1',
  company_id: 'c1',
  name: 'Auditoria Norte',
  members: [
    { user_id: 'u1', name: 'Alice', email: 'alice@test.com' },
    { user_id: 'u2', name: 'Bob', email: 'bob@test.com' },
  ],
}

const mockPaginatedResponse = {
  data: [mockListItem],
  meta: { total: 1, page: 1, page_size: 20, has_next: false, total_pages: 1 },
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.clearAllMocks()
})

describe('teams.store', () => {
  it('starts with empty state', () => {
    const store = useTeamsStore()
    expect(store.items).toEqual([])
    expect(store.selectedTeam).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.isSaving).toBe(false)
    expect(store.error).toBeNull()
  })

  describe('load', () => {
    it('populates items and meta on success', async () => {
      vi.mocked(fetchTeams).mockResolvedValue(mockPaginatedResponse)
      const store = useTeamsStore()
      await store.load()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].name).toBe('Auditoria Norte')
      expect(store.meta?.total).toBe(1)
      expect(store.isLoading).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Erro ao carregar.' } } }
      vi.mocked(fetchTeams).mockRejectedValue(err)
      const store = useTeamsStore()

      await expect(store.load()).rejects.toBe(err)
      expect(store.error).toBe('Erro ao carregar.')
    })
  })

  describe('loadTeam', () => {
    it('sets selectedTeam on success', async () => {
      vi.mocked(fetchTeam).mockResolvedValue(mockTeam)
      const store = useTeamsStore()
      const result = await store.loadTeam('t1')

      expect(result).toEqual(mockTeam)
      expect(store.selectedTeam).toEqual(mockTeam)
    })
  })

  describe('create', () => {
    it('calls createTeam, reloads list, and sets selectedTeam', async () => {
      vi.mocked(createTeam).mockResolvedValue(mockTeam)
      vi.mocked(fetchTeams).mockResolvedValue(mockPaginatedResponse)
      const store = useTeamsStore()

      const result = await store.create({ name: 'Auditoria Norte' })

      expect(createTeam).toHaveBeenCalledWith({ name: 'Auditoria Norte' })
      expect(store.selectedTeam).toEqual(mockTeam)
      expect(store.items).toHaveLength(1)
      expect(result).toEqual(mockTeam)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Nome duplicado.' } } }
      vi.mocked(createTeam).mockRejectedValue(err)
      vi.mocked(fetchTeams).mockResolvedValue(mockPaginatedResponse)
      const store = useTeamsStore()

      await expect(store.create({ name: 'X' })).rejects.toBe(err)
      expect(store.error).toBe('Nome duplicado.')
    })
  })

  describe('update', () => {
    it('calls updateTeam, reloads list, and sets selectedTeam', async () => {
      const updated = { ...mockTeam, name: 'Auditoria Sul' }
      vi.mocked(updateTeam).mockResolvedValue(updated)
      vi.mocked(fetchTeams).mockResolvedValue(mockPaginatedResponse)
      const store = useTeamsStore()

      await store.update('t1', { name: 'Auditoria Sul' })

      expect(updateTeam).toHaveBeenCalledWith('t1', { name: 'Auditoria Sul' })
      expect(store.selectedTeam?.name).toBe('Auditoria Sul')
    })
  })

  describe('remove', () => {
    it('calls deleteTeam and reloads list', async () => {
      vi.mocked(deleteTeam).mockResolvedValue(undefined)
      vi.mocked(fetchTeams).mockResolvedValue({ ...mockPaginatedResponse, data: [] })
      const store = useTeamsStore()
      store.selectedTeam = mockTeam

      await store.remove('t1')

      expect(deleteTeam).toHaveBeenCalledWith('t1')
      expect(store.items).toHaveLength(0)
      expect(store.selectedTeam).toBeNull()
    })

    it('does not clear selectedTeam when removing a different team', async () => {
      vi.mocked(deleteTeam).mockResolvedValue(undefined)
      vi.mocked(fetchTeams).mockResolvedValue(mockPaginatedResponse)
      const store = useTeamsStore()
      store.selectedTeam = { ...mockTeam, id: 't2' }

      await store.remove('t1')

      expect(store.selectedTeam?.id).toBe('t2')
    })
  })

  describe('addMember', () => {
    it('calls addTeamMember and updates selectedTeam', async () => {
      const teamWithNew: Team = {
        ...mockTeam,
        members: [...mockTeam.members, { user_id: 'u3', name: 'Carol', email: 'carol@test.com' }],
      }
      vi.mocked(addTeamMember).mockResolvedValue(teamWithNew)
      const store = useTeamsStore()

      await store.addMember('t1', 'u3')

      expect(addTeamMember).toHaveBeenCalledWith('t1', 'u3')
      expect(store.selectedTeam?.members).toHaveLength(3)
    })
  })

  describe('removeMember', () => {
    it('calls removeTeamMember and updates selectedTeam', async () => {
      const teamWithout: Team = {
        ...mockTeam,
        members: [{ user_id: 'u1', name: 'Alice', email: 'alice@test.com' }],
      }
      vi.mocked(removeTeamMember).mockResolvedValue(teamWithout)
      const store = useTeamsStore()
      store.selectedTeam = mockTeam

      await store.removeMember('t1', 'u2')

      expect(removeTeamMember).toHaveBeenCalledWith('t1', 'u2')
      expect(store.selectedTeam?.members).toHaveLength(1)
    })
  })

  describe('clearSelectedTeam', () => {
    it('sets selectedTeam to null', () => {
      const store = useTeamsStore()
      store.selectedTeam = mockTeam
      store.clearSelectedTeam()
      expect(store.selectedTeam).toBeNull()
    })
  })
})
