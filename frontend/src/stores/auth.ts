import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../lib/api'

interface User {
  id: string
  username: string
  email: string
  display_name: string | null
  avatar_url: string | null
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string, displayName?: string) => Promise<void>
  logout: () => void
  refreshAuth: () => Promise<void>
  clearError: () => void
  fetchUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (username: string, password: string) => {
        set({ isLoading: true, error: null })
        try {
          const response = await api.post('/api/v1/auth/login', {
            username,
            password,
          })
          
          const { access_token, refresh_token } = response.data
          
          // Set tokens first
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
          })
          
          // Fetch user info
          const userResponse = await api.get('/api/v1/auth/me', {
            headers: { Authorization: `Bearer ${access_token}` }
          })
          
          set({
            user: userResponse.data,
            isLoading: false,
          })
        } catch (error: unknown) {
          let message = 'Login failed'
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { data?: { detail?: string } } }
            message = axiosError.response?.data?.detail || message
          }
          set({ error: message, isLoading: false })
          throw error
        }
      },

      register: async (username: string, email: string, password: string, displayName?: string) => {
        set({ isLoading: true, error: null })
        try {
          const payload: Record<string, string> = {
            username,
            email,
            password,
          }
          if (displayName) {
            payload.display_name = displayName
          }
          
          await api.post('/api/v1/auth/register', payload)
          
          // Auto-login after registration
          await get().login(username, password)
        } catch (error: unknown) {
          let message = 'Registration failed'
          if (error && typeof error === 'object' && 'response' in error) {
            const axiosError = error as { response?: { data?: { detail?: string } } }
            message = axiosError.response?.data?.detail || message
          }
          set({ error: message, isLoading: false })
          throw error
        }
      },

      logout: () => {
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
          error: null,
        })
      },

      refreshAuth: async () => {
        const { refreshToken } = get()
        if (!refreshToken) {
          get().logout()
          return
        }

        try {
          const response = await api.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken,
          })
          
          const { access_token, refresh_token } = response.data
          
          set({
            accessToken: access_token,
            refreshToken: refresh_token,
          })
        } catch {
          get().logout()
        }
      },
      
      fetchUser: async () => {
        const { accessToken } = get()
        if (!accessToken) return
        
        try {
          const response = await api.get('/api/v1/auth/me', {
            headers: { Authorization: `Bearer ${accessToken}` }
          })
          set({ user: response.data })
        } catch {
          // Token might be expired, try refreshing
          await get().refreshAuth()
        }
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
