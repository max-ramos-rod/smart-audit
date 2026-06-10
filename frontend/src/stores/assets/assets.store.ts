import { ref } from 'vue'
import { defineStore } from 'pinia'

import { extractProblemMessage } from '@/services/api/problem'
import {
  createAsset,
  deactivateAsset,
  fetchAsset,
  fetchAssets,
  updateAsset,
} from '@/services/assets.service'
import type { PaginationMeta } from '@/types/api'
import type {
  Asset,
  AssetCreatePayload,
  AssetDetail,
  AssetListFilters,
  AssetUpdatePayload,
} from '@/types/assets'

export const useAssetsStore = defineStore('assets', () => {
  const items = ref<Asset[]>([])
  const meta = ref<PaginationMeta | null>(null)
  const detail = ref<AssetDetail | null>(null)
  const filters = ref<AssetListFilters>({ status: 'active' })
  const isLoading = ref(false)
  const isSaving = ref(false)
  const error = ref<string | null>(null)

  async function load(page = 1, pageSize = 20, override?: AssetListFilters) {
    if (override) filters.value = override
    isLoading.value = true
    error.value = null
    try {
      const response = await fetchAssets(page, pageSize, filters.value)
      items.value = response.data
      meta.value = response.meta
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar os ativos.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  async function loadDetail(assetId: string) {
    error.value = null
    try {
      detail.value = await fetchAsset(assetId)
      return detail.value
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel carregar o ativo.')
      throw err
    }
  }

  function clearDetail() {
    detail.value = null
  }

  async function create(payload: AssetCreatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const created = await createAsset(payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      return created
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel criar o ativo.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function update(assetId: string, payload: AssetUpdatePayload) {
    isSaving.value = true
    error.value = null
    try {
      const updated = await updateAsset(assetId, payload)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
      return updated
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel atualizar o ativo.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  async function deactivate(assetId: string) {
    isSaving.value = true
    error.value = null
    try {
      await deactivateAsset(assetId)
      await load(meta.value?.page ?? 1, meta.value?.page_size ?? 20)
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel desativar o ativo.')
      throw err
    } finally {
      isSaving.value = false
    }
  }

  return {
    items,
    meta,
    detail,
    filters,
    isLoading,
    isSaving,
    error,
    load,
    loadDetail,
    clearDetail,
    create,
    update,
    deactivate,
  }
})
