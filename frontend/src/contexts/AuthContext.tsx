// =============================================================================
// RestaurantFlow — Auth Context
// Phase 1: Skeleton only — full implementation in Phase 3.
// =============================================================================

import { createContext, useContext, useState, type ReactNode } from 'react'
import type { User } from '@/types'

interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  accessToken: string | null
  /** Called after a successful login to store tokens. */
  setTokens: (access: string, refresh: string) => void
  /** Clear session data on logout. */
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(
    () => localStorage.getItem('access_token'),
  )

  const setTokens = (access: string, refresh: string) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    setAccessToken(access)
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setAccessToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!accessToken,
        accessToken,
        setTokens,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
