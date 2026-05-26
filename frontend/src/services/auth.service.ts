import type { ApiEnvelope } from '@/types/api'
import type { LoginPayload, TokenResponse } from '@/types/auth'

import { http } from './api/http'

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const response = await http.post<ApiEnvelope<TokenResponse>>('/auth/login', payload)
  return response.data.data
}

export async function fetchMe() {
  const response = await http.get<ApiEnvelope<TokenResponse['user']>>('/auth/me')
  return response.data.data
}
