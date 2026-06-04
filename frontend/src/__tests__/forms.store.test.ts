import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/forms.service', () => ({
  fetchForms: vi.fn(),
  createForm: vi.fn(),
  publishNewVersion: vi.fn(),
}))

import { createForm, fetchForms, publishNewVersion } from '@/services/forms.service'
import { useFormsStore } from '@/stores/forms/forms.store'
import type { FormDetail, FormListItem } from '@/types/forms'

const mockListItem: FormListItem = {
  id: 'f1',
  company_id: 'c1',
  name: 'Checklist Segurança',
  description: null,
  is_active: true,
  current_version_number: 1,
  current_version_status: 'published',
  published_at: '2026-01-01T00:00:00Z',
}

const mockFormDetail: FormDetail = {
  id: 'f1',
  company_id: 'c1',
  name: 'Checklist Segurança',
  description: null,
  is_active: true,
  current_version: {
    id: 'v1',
    version: 1,
    status: 'published',
    published_at: '2026-01-01T00:00:00Z',
    fields: [
      {
        id: 'ff1',
        key: 'extintor_ok',
        label: 'Extintor OK?',
        field_type: 'boolean',
        required: true,
        position: 1,
        config_json: {},
        instruction: null,
      },
    ],
  },
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

describe('forms.store', () => {
  it('starts with empty state', () => {
    const store = useFormsStore()
    expect(store.items).toEqual([])
    expect(store.meta).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.isSaving).toBe(false)
    expect(store.error).toBeNull()
  })

  describe('load', () => {
    it('populates items and meta on success', async () => {
      vi.mocked(fetchForms).mockResolvedValue(mockPaginatedResponse)
      const store = useFormsStore()

      await store.load()

      expect(store.items).toHaveLength(1)
      expect(store.items[0].name).toBe('Checklist Segurança')
      expect(store.meta?.total).toBe(1)
      expect(store.isLoading).toBe(false)
    })

    it('passes page and pageSize to service', async () => {
      vi.mocked(fetchForms).mockResolvedValue(mockPaginatedResponse)
      const store = useFormsStore()

      await store.load(2, 10)

      expect(fetchForms).toHaveBeenCalledWith(2, 10)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Erro de rede.' } } }
      vi.mocked(fetchForms).mockRejectedValue(err)
      const store = useFormsStore()

      await expect(store.load()).rejects.toBe(err)
      expect(store.error).toBe('Erro de rede.')
      expect(store.isLoading).toBe(false)
    })
  })

  describe('create', () => {
    it('calls createForm, reloads list, and returns created form', async () => {
      vi.mocked(createForm).mockResolvedValue(mockFormDetail)
      vi.mocked(fetchForms).mockResolvedValue(mockPaginatedResponse)
      const store = useFormsStore()

      const payload = {
        name: 'Checklist Segurança',
        fields: [
          { key: 'extintor_ok', label: 'Extintor OK?', field_type: 'boolean' as const, required: true, position: 1, config_json: {} },
        ],
      }
      const result = await store.create(payload)

      expect(createForm).toHaveBeenCalledWith(payload)
      expect(fetchForms).toHaveBeenCalled()
      expect(result).toEqual(mockFormDetail)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Nome já existe.' } } }
      vi.mocked(createForm).mockRejectedValue(err)
      vi.mocked(fetchForms).mockResolvedValue(mockPaginatedResponse)
      const store = useFormsStore()

      await expect(store.create({ name: 'X', fields: [] })).rejects.toBe(err)
      expect(store.error).toBe('Nome já existe.')
      expect(store.isSaving).toBe(false)
    })
  })

  describe('publishVersion', () => {
    it('calls publishNewVersion, reloads list, and returns updated form', async () => {
      const updatedForm: FormDetail = {
        ...mockFormDetail,
        current_version: { ...mockFormDetail.current_version, version: 2 },
      }
      vi.mocked(publishNewVersion).mockResolvedValue(updatedForm)
      vi.mocked(fetchForms).mockResolvedValue(mockPaginatedResponse)
      const store = useFormsStore()

      const payload = { fields: [{ key: 'item_novo', label: 'Item novo', field_type: 'text' as const, required: false, position: 1, config_json: {} }] }
      const result = await store.publishVersion('f1', payload)

      expect(publishNewVersion).toHaveBeenCalledWith('f1', payload)
      expect(fetchForms).toHaveBeenCalled()
      expect(result?.current_version.version).toBe(2)
      expect(store.isSaving).toBe(false)
    })

    it('sets error and rethrows on failure', async () => {
      const err = { response: { data: { detail: 'Formulario nao encontrado.' } } }
      vi.mocked(publishNewVersion).mockRejectedValue(err)
      vi.mocked(fetchForms).mockResolvedValue(mockPaginatedResponse)
      const store = useFormsStore()

      await expect(store.publishVersion('f1', { fields: [] })).rejects.toBe(err)
      expect(store.error).toBe('Formulario nao encontrado.')
    })
  })
})
