// =============================================================================
// RestaurantFlow — Global TypeScript Types
// Phase 1 Foundation + Phase 2 Organizations
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

// -----------------------------------------------------------------------------
// Phase 2 — Organizations
// -----------------------------------------------------------------------------

export interface Organization {
  id: string
  name: string
  legal_name: string
  slug: string
  email: string
  phone: string
  address: string
  city: string
  state: string
  country: string
  postal_code: string
  tax_id: string
  currency: string
  timezone: string
  is_active: boolean
  restaurant_count: number
  active_restaurant_count: number
  created_at: string
  updated_at: string
}

export interface OrganizationDetail extends Organization {
  restaurants: Restaurant[]
}

export interface OrganizationCreatePayload {
  name: string
  legal_name?: string
  email?: string
  phone?: string
  address?: string
  city?: string
  state?: string
  country?: string
  postal_code?: string
  tax_id?: string
  currency?: string
  timezone?: string
}

export type OrganizationUpdatePayload = Partial<OrganizationCreatePayload> & {
  is_active?: boolean
}

// -----------------------------------------------------------------------------
// Phase 2 — Restaurants
// -----------------------------------------------------------------------------

export interface RestaurantSettings {
  id: string
  currency: string
  timezone: string
  tax_enabled: boolean
  default_tax_rate: string
  receipt_header: string
  receipt_footer: string
  allow_negative_stock: boolean
  order_prefix: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Restaurant {
  id: string
  organization: string
  organization_name: string
  name: string
  slug: string
  code: string
  description: string
  email: string
  phone: string
  address: string
  city: string
  state: string
  country: string
  postal_code: string
  is_active: boolean
  branch_count: number
  active_branch_count: number
  created_at: string
  updated_at: string
}

export interface RestaurantDetail extends Restaurant {
  settings: RestaurantSettings | null
  branches: Branch[]
}

export interface RestaurantCreatePayload {
  name: string
  code: string
  description?: string
  email?: string
  phone?: string
  address?: string
  city?: string
  state?: string
  country?: string
  postal_code?: string
}

export type RestaurantUpdatePayload = Partial<RestaurantCreatePayload> & {
  is_active?: boolean
}

// -----------------------------------------------------------------------------
// Phase 2 — Branches
// -----------------------------------------------------------------------------

export interface BranchSettings {
  id: string
  opening_time: string | null
  closing_time: string | null
  default_order_type: 'dine_in' | 'takeaway' | 'delivery'
  receipt_footer: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Branch {
  id: string
  restaurant: string
  restaurant_name: string
  organization_id: string
  name: string
  code: string
  address: string
  city: string
  state: string
  country: string
  postal_code: string
  phone: string
  email: string
  latitude: string | null
  longitude: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface BranchDetail extends Branch {
  settings: BranchSettings | null
}

export interface BranchCreatePayload {
  name: string
  code: string
  address?: string
  city?: string
  state?: string
  country?: string
  postal_code?: string
  phone?: string
  email?: string
  latitude?: string
  longitude?: string
}

export type BranchUpdatePayload = Partial<BranchCreatePayload> & {
  is_active?: boolean
}

// -----------------------------------------------------------------------------
// Phase 2 — Dashboard stats
// -----------------------------------------------------------------------------

export interface OrganizationStats {
  total_organizations: number
  active_organizations: number
  total_restaurants: number
  active_restaurants: number
  total_branches: number
  active_branches: number
}
