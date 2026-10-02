// =============================================================================
// RestaurantFlow — Auth Context
// Phase 3: Full implementation with user population, roles, permissions
// =============================================================================

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from 'react'
import type { UserDetail } from '@/types'
import { fetchCurrentUser, logout as apiLogout } from '@/services/auth'

interface AuthContextValue {
  user: UserDetail | null
  isAuthenticated: boolean
  isLoading: boolean
  accessToken: string | null
  /** Call after a successful login to store tokens and fetch user. */
  setTokens: (access: string, refresh: string) => Promise<void>
  /** Clear session on logout. */
  logout: () => void
  /** Reload the current user from the API (after profile changes, etc.). */
  refreshUser: () => Promise<void>
  /** Check if the current user holds a permission code. */
  hasPermission: (code: string) => boolean
  /** Check if the current user holds a specific role code. */
  hasRole: (code: string) => boolean
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserDetail | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(
    () => localStorage.getItem('access_token'),
  )
  const [isLoading, setIsLoading] = useState<boolean>(true)

  // ------------------------------------------------------------------
  // Bootstrap: if a token exists on mount, fetch the current user
  // ------------------------------------------------------------------
  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (!token) {
      setIsLoading(false)
      return
    }

    fetchCurrentUser()
      .then((u) => {
        setUser(u)
        setAccessToken(token)
      })
      .catch(() => {
        // Token invalid / expired and refresh failed — clear everything
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setAccessToken(null)
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  // ------------------------------------------------------------------
  // setTokens — called immediately after a successful login
  // ------------------------------------------------------------------
  const setTokens = useCallback(async (access: string, refresh: string) => {
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    setAccessToken(access)

    try {
      const u = await fetchCurrentUser()
      setUser(u)
    } catch {
      // If /api/auth/me/ fails immediately after login, clear tokens
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setAccessToken(null)
      setUser(null)
    }
  }, [])

  // ------------------------------------------------------------------
  // logout
  // ------------------------------------------------------------------
  const logout = useCallback(() => {
    const refreshToken = localStorage.getItem('refresh_token')
    if (refreshToken) {
      // Fire-and-forget blacklist call — don't block UI on it
      apiLogout(refreshToken).catch(() => {
        /* ignore network errors on logout */
      })
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setAccessToken(null)
    setUser(null)
  }, [])

  // ------------------------------------------------------------------
  // refreshUser — reload from API
  // ------------------------------------------------------------------
  const refreshUser = useCallback(async () => {
    try {
      const u = await fetchCurrentUser()
      setUser(u)
    } catch {
      logout()
    }
  }, [logout])

  // ------------------------------------------------------------------
  // Permission helpers — frontend hints only; backend is authoritative
  // ------------------------------------------------------------------
  const hasPermission = useCallback(
    (code: string): boolean => {
      if (!user) return false
      if (user.is_staff || user.scope?.is_superuser) return true
      return user.scope?.permissions?.includes(code) ?? false
    },
    [user],
  )

  const hasRole = useCallback(
    (code: string): boolean => {
      if (!user) return false
      return (
        user.scope?.roles?.some((r) => r.role_code === code) ?? false
      )
    },
    [user],
  )

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!accessToken && !!user,
        isLoading,
        accessToken,
        setTokens,
        logout,
        refreshUser,
        hasPermission,
        hasRole,
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
