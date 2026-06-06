import { ref } from 'vue'
import { defineStore } from 'pinia'

import { extractProblemMessage } from '@/services/api/problem'
import {
  createUser,
  fetchRevokedUsers,
  fetchUser,
  fetchUsers,
  inviteUser,
  reactivateUser,
  revokeUser,
  updateUser,
} from '@/services/users.service'
import type { PaginationMeta } from '@/types/api'
import type {
  UserCreatePayload,
  UserDetail,
  UserInvitePayload,
  UserListItem,
  UserRevokedItem,
  UserUpdatePayload,
} from '@/types/users'

export const useUsersStore = defineStore('users', () => {
  const items = ref<UserListItem[]>([])
  const revokedItems = ref<UserRevokedItem[]>([])
  const selectedUser = ref<UserDetail | null>(null)
  const meta = ref<PaginationMeta | null>(null)
  const revokedMeta = ref<PaginationMeta | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)

  async function load(page = 1, pageSize = 20) {
    isLoading.value = true
    error.value = null
    try {
      const response = await fetchUsers(page, pageSize)
      items.value = response.data
      meta.value = response.meta
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar usuarios.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function loadUser(userId: string) {
    isLoading.value = true
    error.value = null
    try {
      selectedUser.value = await fetchUser(userId)
      return selectedUser.value
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar o usuario.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function create(payload: UserCreatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const created = await createUser(payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      selectedUser.value = created
      return created
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel criar o usuario.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function invite(payload: UserInvitePayload) {
    isSaving.value = true
    error.value = null
    try {
      const invited = await inviteUser(payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      return invited
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel enviar o convite.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function update(userId: string, payload: UserUpdatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await updateUser(userId, payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      selectedUser.value = updated
      return updated
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel atualizar o usuario.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function revoke(userId: string) {
    isSaving.value = true
    error.value = null
    try {
      await revokeUser(userId)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      if (selectedUser.value?.id === userId) {
        selectedUser.value = null
      }
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel revogar o acesso do usuario.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function loadRevoked(page = 1, pageSize = 20) {
    isLoading.value = true
    error.value = null
    try {
      const response = await fetchRevokedUsers(page, pageSize)
      revokedItems.value = response.data
      revokedMeta.value = response.meta
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar usuarios revogados.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function reactivate(userId: string) {
    isSaving.value = true
    error.value = null
    try {
      await reactivateUser(userId)
      await loadRevoked(revokedMeta.value?.page ?? 1, revokedMeta.value?.page_size ?? 20)
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel reativar o usuario.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  function clearSelectedUser() {
    selectedUser.value = null
  }

  return {
    items,
    revokedItems,
    selectedUser,
    meta,
    revokedMeta,
    isLoading,
    isSaving,
    error,
    load,
    loadUser,
    loadRevoked,
    create,
    invite,
    update,
    revoke,
    reactivate,
    clearSelectedUser,
  }
})
