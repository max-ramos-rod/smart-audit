import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { extractProblemMessage } from '@/services/api/problem'
import {
  fetchMyCompanies,
  fetchMyContext,
  fetchMyStats,
  updateMe,
  type MeUpdatePayload,
} from '@/services/context.service'
import { clearCompanyId, readCompanyId, writeCompanyId } from '@/services/api/storage'
import type { CompanyStats, UserCompany, UserContext } from '@/types/context'

export const useContextStore = defineStore('context', () => {
  const companies = ref<UserCompany[]>([])
  const context = ref<UserContext | null>(null)
  const stats = ref<CompanyStats | null>(null)
  const selectedCompanyId = ref<string | null>(readCompanyId())
  const isLoading = ref(false)
  const isLoadingStats = ref(false)
  const isUpdatingProfile = ref(false)
  const error = ref<string | null>(null)
  const updateProfileError = ref<string | null>(null)

  const activeCompany = computed(() => context.value?.active_company ?? null)

  async function bootstrap() {
    isLoading.value = true
    error.value = null
    try {
      companies.value = await fetchMyCompanies()
      context.value = await fetchMyContext(selectedCompanyId.value)
      if (context.value?.active_company?.id) {
        selectedCompanyId.value = context.value.active_company.id
        writeCompanyId(context.value.active_company.id)
      }
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar o contexto.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function loadStats(period?: string) {
    isLoadingStats.value = true
    try {
      stats.value = await fetchMyStats(period)
    } catch {
      // stats são best-effort — não bloqueia a UI
    } finally {
      isLoadingStats.value = false
    }
  }

  async function selectCompany(companyId: string) {
    selectedCompanyId.value = companyId
    writeCompanyId(companyId)
    context.value = await fetchMyContext(companyId)
    stats.value = null
    loadStats()
  }

  async function updateProfile(payload: MeUpdatePayload) {
    isUpdatingProfile.value = true
    updateProfileError.value = null
    try {
      const updated = await updateMe(payload)
      if (context.value?.user) {
        context.value = { ...context.value, user: { ...context.value.user, name: updated.name } }
      }
      return updated
    } catch (err) {
      updateProfileError.value = extractProblemMessage(err, 'Não foi possível atualizar o perfil.')
      throw err
    } finally {
      isUpdatingProfile.value = false
    }
  }

  function reset() {
    companies.value = []
    context.value = null
    stats.value = null
    selectedCompanyId.value = null
    error.value = null
    clearCompanyId()
  }

  return {
    companies,
    context,
    stats,
    selectedCompanyId,
    activeCompany,
    isLoading,
    isLoadingStats,
    isUpdatingProfile,
    error,
    updateProfileError,
    bootstrap,
    loadStats,
    selectCompany,
    updateProfile,
    reset,
  }
})
