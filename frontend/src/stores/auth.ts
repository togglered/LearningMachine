import axios from 'axios'
import { defineStore } from 'pinia'

interface TokenResponse {
  access: string
  refresh: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    access: localStorage.getItem('access'),
    refresh: localStorage.getItem('refresh'),
  }),
  getters: {
    isAuthenticated: (state) => !!state.access,
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await axios.post<TokenResponse>(
        `${import.meta.env.VITE_API_URL}/auth/token/`,
        { username, password },
      )
      this.access = data.access
      this.refresh = data.refresh
      localStorage.setItem('access', data.access)
      localStorage.setItem('refresh', data.refresh)
    },
    logout() {
      this.access = null
      this.refresh = null
      localStorage.removeItem('access')
      localStorage.removeItem('refresh')
    },
  },
})
