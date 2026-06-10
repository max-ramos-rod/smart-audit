import { ref } from 'vue'
import { defineStore } from 'pinia'

import { extractProblemMessage } from '@/services/api/problem'
import {
  createAssetType,
  deactivateAssetType,
  fetchAssetTypes,
  updateAssetType,
} from '@/services/asset-types.service'
import type { PaginationMeta } from '@/types/api'
import type { AssetType, AssetTypeCreatePayload, AssetTypeUpdatePayload } from '@/types/asset-types'

export const useAssetTypesStore = defineStore('asset-types', () => {
  const items = ref<AssetType[]>([])
  const meta = ref<PaginationMeta | null>(null)
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)

  async function load(page = 1, pageSize = 20, isActive?: boolean) {
    isLoading.value = true
    error.value = null
    try {
      const response = await fetchAssetTypes(page, pageSize, isActive)
      items.value = response.data
      meta.value = response.meta
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar os tipos de ativo.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function create(payload: AssetTypeCreatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const created = await createAssetType(payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      return created
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel criar o tipo de ativo.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function update(assetTypeId: string, payload: AssetTypeUpdatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await updateAssetType(assetTypeId, payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      return updated
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel atualizar o tipo de ativo.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deactivate(assetTypeId: string) {
    isSaving.value = true
    error.value = null
    try {
      await deactivateAssetType(assetTypeId)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel desativar o tipo de ativo.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  return { items, meta, isLoading, isSaving, error, load, create, update, deactivate }
})
