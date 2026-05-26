import { ref } from 'vue'
import { defineStore } from 'pinia'

import { extractProblemMessage } from '@/services/api/problem'
import {
  addTeamMember,
  createTeam,
  deleteTeam,
  fetchTeam,
  fetchTeams,
  removeTeamMember,
  updateTeam,
} from '@/services/teams.service'
import type { PaginationMeta } from '@/types/api'
import type { Team, TeamCreatePayload, TeamListItem, TeamUpdatePayload } from '@/types/teams'

export const useTeamsStore = defineStore('teams', () => {
  const items = ref<TeamListItem[]>([])
  const selectedTeam = ref<Team | null>(null)
  const meta = ref<PaginationMeta | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)

  async function load(page = 1, pageSize = 20) {
    isLoading.value = true
    error.value = null
    try {
      const response = await fetchTeams(page, pageSize)
      items.value = response.data
      meta.value = response.meta
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar equipes.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function loadTeam(teamId: string) {
    isLoading.value = true
    error.value = null
    try {
      selectedTeam.value = await fetchTeam(teamId)
      return selectedTeam.value
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar a equipe.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function create(payload: TeamCreatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const created = await createTeam(payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      selectedTeam.value = created
      return created
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel criar a equipe.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function update(teamId: string, payload: TeamUpdatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await updateTeam(teamId, payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      selectedTeam.value = updated
      return updated
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel atualizar a equipe.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function remove(teamId: string) {
    isSaving.value = true
    error.value = null
    try {
      await deleteTeam(teamId)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      if (selectedTeam.value?.id === teamId) {
        selectedTeam.value = null
      }
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel excluir a equipe.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function addMember(teamId: string, userId: string) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await addTeamMember(teamId, userId)
      selectedTeam.value = updated
      return updated
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel adicionar membro.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function removeMember(teamId: string, userId: string) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await removeTeamMember(teamId, userId)
      selectedTeam.value = updated
      return updated
    } catch (err: any) {
      error.value = extractProblemMessage(err, 'Nao foi possivel remover membro.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  function clearSelectedTeam() {
    selectedTeam.value = null
  }

  return {
    items,
    selectedTeam,
    meta,
    isLoading,
    isSaving,
    error,
    load,
    loadTeam,
    create,
    update,
    remove,
    addMember,
    removeMember,
    clearSelectedTeam,
  }
})
