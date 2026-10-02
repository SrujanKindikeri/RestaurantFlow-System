// =============================================================================
// RestaurantFlow — Auth Service
// Phase 3
// =============================================================================

import api, { post } from './api'
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  User,
  UserDetail,
} from '@/types'

// ---------------------------------------------------------------------------
// Login / logout
// ---------------------------------------------------------------------------

export async function login(data: LoginRequest): Promise<LoginResponse> {
  return post<LoginResponse>('/auth/login/', data)
}

export async function logout(refreshToken: string): Promise<void> {
  await post('/auth/logout/', { refresh: refreshToken })
}

export async function refreshAccessToken(refreshToken: string): Promise<string> {
  const data = await post<{ access: string }>('/auth/token/refresh/', {
    refresh: refreshToken,
  })
  return data.access
}

// ---------------------------------------------------------------------------
// Current user
// ---------------------------------------------------------------------------

export async function fetchCurrentUser(): Promise<UserDetail> {
  return api.get<UserDetail>('/auth/me/').then((r) => r.data)
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

export async function register(data: RegisterRequest): Promise<User> {
  return post<User>('/auth/register/', data)
}
