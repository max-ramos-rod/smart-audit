import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/services/auth.service', () => ({
  login: vi.fn(),
}))

import { login as loginRequest } from '@/services/auth.service'
import { useAuthStore } from '@/stores/auth/auth.store'

const mockUser = { id: 'u1', name: 'Alice', email: 'alice@test.com' }
const mockTokenResponse = {
  access_token: 'jwt_token',
  token_type: 'bearer',
  expires_in: 3600,
  user: mockUser,
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
})

describe('auth.store', () => {
  it('isAuthenticated is false when no token in localStorage', () => {
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(false)
    expect(store.user).toBeNull()
  })

  it('isAuthenticated is true when token exists in localStorage', () => {
    localStorage.setItem('smart-audit.token', 'existing_token')
    const store = useAuthStore()
    expect(store.isAuthenticated).toBe(true)
  })

  it('login sets token and user, persists token', async () => {
    vi.mocked(loginRequest).mockResolvedValue(mockTokenResponse)
    const store = useAuthStore()

    await store.login({ email: 'alice@test.com', password: 'secret123' })

    expect(store.accessToken).toBe('jwt_token')
    expect(store.user).toEqual(mockUser)
    expect(store.isAuthenticated).toBe(true)
    expect(localStorage.getItem('smart-audit.token')).toBe('jwt_token')
  })

  it('login sets error and rethrows on failure', async () => {
    const apiError = { response: { data: { detail: 'Credenciais inválidas.' } } }
    vi.mocked(loginRequest).mockRejectedValue(apiError)
    const store = useAuthStore()

    await expect(store.login({ email: 'x@y.com', password: 'wrong' })).rejects.toBe(apiError)
    expect(store.error).toBe('Credenciais inválidas.')
    expect(store.isAuthenticated).toBe(false)
  })

  it('logout clears user, token and company id', async () => {
    vi.mocked(loginRequest).mockResolvedValue(mockTokenResponse)
    const store = useAuthStore()
    await store.login({ email: 'alice@test.com', password: 'secret123' })
    localStorage.setItem('smart-audit.company-id', 'c1')

    store.logout()

    expect(store.accessToken).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('smart-audit.token')).toBeNull()
    expect(localStorage.getItem('smart-audit.company-id')).toBeNull()
  })

  it('setUser updates the user ref', () => {
    const store = useAuthStore()
    expect(store.user).toBeNull()

    store.setUser(mockUser)
    expect(store.user).toEqual(mockUser)

    store.setUser(null)
    expect(store.user).toBeNull()
  })
})
