import axios from 'axios'

import { clearAccessToken, readAccessToken, readCompanyId } from './storage'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

export const http = axios.create({
  baseURL: apiBaseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
})

http.interceptors.request.use((config) => {
  const token = readAccessToken()
  const companyId = readCompanyId()

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  if (companyId) {
    config.headers['X-Company-Id'] = companyId
  }

  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }

  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAccessToken()
    }
    return Promise.reject(error)
  },
)
