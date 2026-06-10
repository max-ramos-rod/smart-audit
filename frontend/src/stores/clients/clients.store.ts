import { ref } from 'vue'
import { defineStore } from 'pinia'

import { extractProblemMessage } from '@/services/api/problem'
import {
  createClient,
  deactivateClient,
  fetchClients,
  updateClient,
} from '@/services/clients.service'
import type { PaginationMeta } from '@/types/api'
import type { Client, ClientCreatePayload, ClientUpdatePayload } from '@/types/clients'

export const useClientsStore = defineStore('clients', () => {
  const items = ref<Client[]>([])
  const meta = ref<PaginationMeta | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)

  async function load(page = 1, pageSize = 20, isActive?: boolean) {
    isLoading.value = true
    error.value = null
    try {
      const response = await fetchClients(page, pageSize, isActive)
      items.value = response.data
      meta.value = response.meta
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar clientes.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function create(payload: ClientCreatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const created = await createClient(payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      return created
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel criar o cliente.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function update(clientId: string, payload: ClientUpdatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await updateClient(clientId, payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      return updated
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel atualizar o cliente.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deactivate(clientId: string) {
    isSaving.value = true
    error.value = null
    try {
      await deactivateClient(clientId)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel desativar o cliente.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  return { items, meta, isLoading, isSaving, error, load, create, update, deactivate }
})
