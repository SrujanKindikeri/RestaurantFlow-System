// =============================================================================
// RestaurantFlow — Global TypeScript Types
// Phase 1 Foundation
// =============================================================================

// -----------------------------------------------------------------------------
// API
// -----------------------------------------------------------------------------

/** Standard API error envelope returned by the backend. */
export interface ApiError {
  error: true
  message: string
  details: Record<string, unknown> | null
}

/** Paginated list response from DRF. */
export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// -----------------------------------------------------------------------------
// Health
// -----------------------------------------------------------------------------

export interface HealthCheckResponse {
  status: 'ok' | 'error'
  service: string
}

// -----------------------------------------------------------------------------
// Auth
// -----------------------------------------------------------------------------

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  is_active: boolean
  date_joined: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access: string
  refresh: string
}

export interface RegisterRequest {
  email: string
  first_name: string
  last_name: string
  password: string
  password_confirm: string
}
