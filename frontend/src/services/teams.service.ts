import type { ApiEnvelope, PaginatedEnvelope } from '@/types/api'
import type { Team, TeamCreatePayload, TeamListItem, TeamUpdatePayload } from '@/types/teams'

import { http } from './api/http'

export async function fetchTeams(page = 1, pageSize = 20) {
  const response = await http.get<PaginatedEnvelope<TeamListItem>>('/teams', {
    params: { page, page_size: pageSize },
  })
  return response.data
}

export async function fetchTeam(teamId: string) {
  const response = await http.get<ApiEnvelope<Team>>(`/teams/${teamId}`)
  return response.data.data
}

export async function createTeam(payload: TeamCreatePayload) {
  const response = await http.post<ApiEnvelope<Team>>('/teams', payload)
  return response.data.data
}

export async function updateTeam(teamId: string, payload: TeamUpdatePayload) {
  const response = await http.patch<ApiEnvelope<Team>>(`/teams/${teamId}`, payload)
  return response.data.data
}

export async function deleteTeam(teamId: string) {
  await http.delete(`/teams/${teamId}`)
}

export async function addTeamMember(teamId: string, userId: string) {
  const response = await http.post<ApiEnvelope<Team>>(`/teams/${teamId}/members`, {
    user_id: userId,
  })
  return response.data.data
}

export async function removeTeamMember(teamId: string, userId: string) {
  const response = await http.delete<ApiEnvelope<Team>>(`/teams/${teamId}/members/${userId}`)
  return response.data.data
}
