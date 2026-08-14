import { create } from 'zustand'

import type { User } from '../lib/types'

const TOKEN_KEY = 'lingua_access_token'

interface AuthState {
  accessToken: string | null
  user: User | null
  setAuth: (token: string, user: User) => void
  setAccessToken: (token: string) => void
  setUser: (user: User) => void
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: localStorage.getItem(TOKEN_KEY),
  user: null,

  setAuth: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token)
    set({ accessToken: token, user })
  },
  setAccessToken: (token) => {
    localStorage.setItem(TOKEN_KEY, token)
    set({ accessToken: token })
  },
  setUser: (user) => set({ user }),
  clear: () => {
    localStorage.removeItem(TOKEN_KEY)
    set({ accessToken: null, user: null })
  },
}))
