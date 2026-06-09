import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/context.service', () => ({
  fetchMyCompanies: vi.fn(),
  fetchMyContext: vi.fn(),
  fetchMyStats: vi.fn(),
}))

import { fetchMyCompanies, fetchMyContext, fetchMyStats } from '@/services/context.service'
import { useContextStore } from '@/stores/context/context.store'
import type { UserCompany, UserContext } from '@/types/context'

const mockCompany: UserCompany = {
  id: 'c1',
  name: 'Acme',
  slug: 'acme',
  plan: 'free',
  role: 'OWNER',
  is_active: true,
}

const mockContext: UserContext = {
  user: { id: 'u1', name: 'Alice', email: 'alice@test.com' },
  active_company: mockCompany,
  membership: { role: 'OWNER' },
  available_companies: [mockCompany],
  requires_company_selection: false,
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
})

describe('context.store', () => {
  it('starts with empty state', () => {
    const store = useContextStore()
    expect(store.companies).toEqual([])
    expect(store.context).toBeNull()
    expect(store.activeCompany).toBeNull()
    expect(store.isLoading).toBe(false)
  })

  it('bootstrap loads companies and context', async () => {
    vi.mocked(fetchMyCompanies).mockResolvedValue([mockCompany])
    vi.mocked(fetchMyContext).mockResolvedValue(mockContext)

    const store = useContextStore()
    await store.bootstrap()

    expect(store.companies).toHaveLength(1)
    expect(store.context).toEqual(mockContext)
    expect(store.activeCompany?.id).toBe('c1')
    expect(store.isLoading).toBe(false)
  })

  it('bootstrap persists active company id to localStorage', async () => {
    vi.mocked(fetchMyCompanies).mockResolvedValue([mockCompany])
    vi.mocked(fetchMyContext).mockResolvedValue(mockContext)

    const store = useContextStore()
    await store.bootstrap()

    expect(localStorage.getItem('smart-audit.company-id')).toBe('c1')
  })

  it('bootstrap sets error and rethrows on failure', async () => {
    const err = new Error('network error')
    vi.mocked(fetchMyCompanies).mockRejectedValue(err)

    const store = useContextStore()
    await expect(store.bootstrap()).rejects.toBe(err)

    expect(store.error).toBeTruthy()
    expect(store.isLoading).toBe(false)
  })

  it('selectCompany updates context and persists company id', async () => {
    const newContext = { ...mockContext, active_company: { ...mockCompany, id: 'c2' } }
    vi.mocked(fetchMyContext).mockResolvedValue(newContext)
    vi.mocked(fetchMyStats).mockResolvedValue({
      total_submissions: 0,
      completed: 0,
      in_progress: 0,
      avg_score: null,
      recent: [],
      score_by_form: [],
      score_trend: [],
    })

    const store = useContextStore()
    await store.selectCompany('c2')

    expect(store.selectedCompanyId).toBe('c2')
    expect(localStorage.getItem('smart-audit.company-id')).toBe('c2')
    expect(store.context?.active_company?.id).toBe('c2')
  })

  it('reset clears all state and removes company id from localStorage', async () => {
    vi.mocked(fetchMyCompanies).mockResolvedValue([mockCompany])
    vi.mocked(fetchMyContext).mockResolvedValue(mockContext)

    const store = useContextStore()
    await store.bootstrap()
    expect(store.companies).toHaveLength(1)

    store.reset()

    expect(store.companies).toEqual([])
    expect(store.context).toBeNull()
    expect(store.stats).toBeNull()
    expect(store.selectedCompanyId).toBeNull()
    expect(localStorage.getItem('smart-audit.company-id')).toBeNull()
  })
})
