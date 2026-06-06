import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type {
  UserCreatePayload,
  UserDetail,
  UserInvitePayload,
  UserListItem,
  UserRevokedItem,
  UserUpdatePayload,
} from '@/types/users'

import { http } from './api/http'

export async function fetchUsers(page = 1, pageSize = 20) {
  const response = await http.get<PaginatedEnvelope<UserListItem>>('/users', {
    params: { page, page_size: pageSize },
  })
  return response.data
}

export async function fetchUser(userId: string) {
  const response = await http.get<ApiEnvelope<UserDetail>>(`/users/${userId}`)
  return response.data.data
}

export async function createUser(payload: UserCreatePayload) {
  const response = await http.post<ApiEnvelope<UserDetail>>('/users', payload)
  return response.data.data
}

export async function inviteUser(payload: UserInvitePayload) {
  const response = await http.post<ApiEnvelope<UserDetail>>('/users/invite', payload)
  return response.data.data
}

export async function updateUser(userId: string, payload: UserUpdatePayload) {
  const response = await http.patch<ApiEnvelope<UserDetail>>(`/users/${userId}`, payload)
  return response.data.data
}

export async function revokeUser(userId: string): Promise<void> {
  await http.delete(`/users/${userId}`)
}

export async function fetchRevokedUsers(page = 1, pageSize = 20) {
  const response = await http.get<PaginatedEnvelope<UserRevokedItem>>('/users/revoked', {
    params: { page, page_size: pageSize },
  })
  return response.data
}

export async function reactivateUser(userId: string): Promise<void> {
  await http.post(`/users/${userId}/reactivate`)
}
