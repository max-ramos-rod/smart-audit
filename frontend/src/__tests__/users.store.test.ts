import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/users.service', () => ({
  fetchUsers: vi.fn(),
  fetchUser: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
}))

import { createUser, fetchUser, fetchUsers, updateUser } from '@/services/users.service'
import { useUsersStore } from '@/stores/users/users.store'
import type { UserDetail, UserListItem } from '@/types/users'

const mockListItem: UserListItem = {
  id: 'u1',
  name: 'Alice',
  email: 'alice@test.com',
  is_active: true,
  role: 'INSPECTOR',
}

const mockDetail: UserDetail = {
  ...mockListItem,
  company_id: 'c1',
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

describe('users.store', () => {
  it('starts with empty state', () => {
    const store = useUsersStore()
    expect(store.items).toEqual([])
    expect(store.selectedUser).toBeNull()
    expect(store.meta).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.isSaving).toBe(false)
    expect(store.error).toBeNull()
  })

  describe('load', () => {
    it('populates items and meta on success', async () => {
      vi.mocked(fetchUsers).mockResolvedValue(mockPaginatedResponse)
      const store = useUsersStore()

      await store.load()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].name).toBe('Alice')
      expect(store.meta?.total).toBe(1)
      expect(store.isLoading).toBe(false)
    })

    it('passes page and pageSize to service', async () => {
      vi.mocked(fetchUsers).mockResolvedValue(mockPaginatedResponse)
      const store = useUsersStore()

      await store.load(3, 10)

      expect(fetchUsers).toHaveBeenCalledWith(3, 10)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Acesso negado.' } } }
      vi.mocked(fetchUsers).mockRejectedValue(err)
      const store = useUsersStore()

      await expect(store.load()).rejects.toBe(err)
      expect(store.error).toBe('Acesso negado.')
      expect(store.isLoading).toBe(false)
    })
  })

  describe('loadUser', () => {
    it('sets selectedUser and returns it', async () => {
      vi.mocked(fetchUser).mockResolvedValue(mockDetail)
      const store = useUsersStore()

      const result = await store.loadUser('u1')

      expect(fetchUser).toHaveBeenCalledWith('u1')
      expect(store.selectedUser).toEqual(mockDetail)
      expect(result).toEqual(mockDetail)
      expect(store.isLoading).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Usuario nao encontrado.' } } }
      vi.mocked(fetchUser).mockRejectedValue(err)
      const store = useUsersStore()

      await expect(store.loadUser('u1')).rejects.toBe(err)
      expect(store.error).toBe('Usuario nao encontrado.')
    })
  })

  describe('create', () => {
    it('calls createUser, reloads list, sets selectedUser, and returns created user', async () => {
      vi.mocked(createUser).mockResolvedValue(mockDetail)
      vi.mocked(fetchUsers).mockResolvedValue(mockPaginatedResponse)
      const store = useUsersStore()

      const payload = {
        name: 'Alice',
        email: 'alice@test.com',
        password: 'senha123',
        role: 'INSPECTOR',
        is_active: true,
      }
      const result = await store.create(payload)

      expect(createUser).toHaveBeenCalledWith(payload)
      expect(fetchUsers).toHaveBeenCalled()
      expect(store.selectedUser).toEqual(mockDetail)
      expect(result).toEqual(mockDetail)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Email ja cadastrado.' } } }
      vi.mocked(createUser).mockRejectedValue(err)
      vi.mocked(fetchUsers).mockResolvedValue(mockPaginatedResponse)
      const store = useUsersStore()

      await expect(
        store.create({
          name: 'X',
          email: 'x@x.com',
          password: '12345678',
          role: 'VIEWER',
          is_active: true,
        }),
      ).rejects.toBe(err)
      expect(store.error).toBe('Email ja cadastrado.')
      expect(store.isSaving).toBe(false)
    })
  })

  describe('update', () => {
    it('calls updateUser, reloads list, sets selectedUser, and returns updated user', async () => {
      const updated: UserDetail = { ...mockDetail, role: 'MANAGER' }
      vi.mocked(updateUser).mockResolvedValue(updated)
      vi.mocked(fetchUsers).mockResolvedValue(mockPaginatedResponse)
      const store = useUsersStore()

      const result = await store.update('u1', { role: 'MANAGER' })

      expect(updateUser).toHaveBeenCalledWith('u1', { role: 'MANAGER' })
      expect(store.selectedUser?.role).toBe('MANAGER')
      expect(result).toEqual(updated)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Permissao insuficiente.' } } }
      vi.mocked(updateUser).mockRejectedValue(err)
      vi.mocked(fetchUsers).mockResolvedValue(mockPaginatedResponse)
      const store = useUsersStore()

      await expect(store.update('u1', { role: 'OWNER' })).rejects.toBe(err)
      expect(store.error).toBe('Permissao insuficiente.')
    })
  })

  describe('clearSelectedUser', () => {
    it('sets selectedUser to null', async () => {
      vi.mocked(fetchUser).mockResolvedValue(mockDetail)
      const store = useUsersStore()
      await store.loadUser('u1')
      expect(store.selectedUser).not.toBeNull()

      store.clearSelectedUser()

      expect(store.selectedUser).toBeNull()
    })
  })
})
