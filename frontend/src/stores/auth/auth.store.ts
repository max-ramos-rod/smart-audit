import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { login as loginRequest } from '@/services/auth.service'
import { extractProblemMessage } from '@/services/api/problem'
import {
  clearAccessToken,
  readAccessToken,
  writeAccessToken,
  clearCompanyId,
} from '@/services/api/storage'
import type { AuthenticatedUser, LoginPayload } from '@/types/auth'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(readAccessToken())
  const user = ref<AuthenticatedUser | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => Boolean(accessToken.value))

  async function login(payload: LoginPayload) {
    isLoading.value = true
    error.value = null
    try {
      const response = await loginRequest(payload)
      accessToken.value = response.access_token
      user.value = response.user
      writeAccessToken(response.access_token)
      return response
    } catch (err) {
      error.value = extractProblemMessage(err, 'Nao foi possivel autenticar.')
      throw err
    } finally {
      isLoading.value = false
    }
  }

  function setUser(nextUser: AuthenticatedUser | null) {
    user.value = nextUser
  }

  function logout() {
    accessToken.value = null
    user.value = null
    error.value = null
    clearAccessToken()
    clearCompanyId()
  }

  return {
    accessToken,
    user,
    isLoading,
    error,
    isAuthenticated,
    login,
    logout,
    setUser,
  }
})
