import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi, UserInfo } from '@/api/auth'

interface AuthState {
  accessToken: string | null
  refreshToken: string | null
  user: UserInfo | null
  setTokens: (access: string, refresh: string) => void
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,

      setTokens: (access, refresh) =>
        set({ accessToken: access, refreshToken: refresh }),

      login: async (username, password) => {
        const res = await authApi.login({ username, password })
        set({
          accessToken: res.data.access_token,
          refreshToken: res.data.refresh_token,
        })
        const userRes = await authApi.getMe()
        set({ user: userRes.data })
      },

      logout: () => set({ accessToken: null, refreshToken: null, user: null }),

      fetchUser: async () => {
        const res = await authApi.getMe()
        set({ user: res.data })
      },
    }),
    { name: 'meks-auth' }
  )
)
