import axios from 'axios'

import { useAuthStore } from '../stores/auth'

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
