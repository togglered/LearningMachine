import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

api.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.access) {
    config.headers.Authorization = `Bearer ${auth.access}`
  }
  return config
})

let refreshing: Promise<string | null> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const auth = useAuthStore()
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined

    if (
      error.response?.status !== 401 ||
      !original ||
      original._retry ||
      original.url?.includes('/auth/token')
    ) {
      return Promise.reject(error)
    }
    original._retry = true

    if (!refreshing) {
      refreshing = auth.refreshAccess().finally(() => {
        refreshing = null
      })
    }
    const newAccess = await refreshing

    if (!newAccess) {
      auth.logout()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
      return Promise.reject(error)
    }

    original.headers.Authorization = `Bearer ${newAccess}`
    return api(original)
  },
)
