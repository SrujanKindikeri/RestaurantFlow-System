// =============================================================================
// RestaurantFlow — Global TypeScript Types
// Phase 1 Foundation + Phase 2 Organizations + Phase 3 Users/Roles/Permissions
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
// Phase 3 — Auth / Users
// -----------------------------------------------------------------------------

export interface UserProfile {
  display_name: string
  employee_code: string
  profile_photo: string | null
  is_active: boolean
}

/** Scope summary returned by /api/auth/me/ and /api/users/<id>/ */
export interface UserScope {
  is_superuser: boolean
  is_staff: boolean
  permissions: string[]
  roles: UserScopeRole[]
}

export interface UserScopeRole {
  assignment_id: string
  role_code: string
  role_name: string
  scope: 'organization' | 'restaurant' | 'branch'
  organization: { id: string; name: string } | null
  restaurant: { id: string; name: string } | null
  branch: { id: string; name: string } | null
}

export interface User {
  id: number
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  is_active: boolean
  date_joined: string
  updated_at: string
  profile: UserProfile | null
  scope: UserScope
}

export interface UserDetail extends User {
  is_staff: boolean
  last_login: string | null
  role_assignments: UserRoleAssignment[]
  permissions: string[]
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
  phone?: string
  password: string
  password_confirm: string
}

export interface UserCreatePayload {
  email: string
  first_name: string
  last_name: string
  phone?: string
  password: string
}

export interface UserUpdatePayload {
  first_name?: string
  last_name?: string
  phone?: string
  profile?: Partial<UserProfile>
}

// -----------------------------------------------------------------------------
// Phase 3 — Roles & Permissions
// -----------------------------------------------------------------------------

export interface Permission {
  id: string
  code: string
  name: string
  description: string
  module: string
  action: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RoleMinimal {
  id: string
  name: string
  code: string
  scope: 'organization' | 'restaurant' | 'branch'
}

export interface Role {
  id: string
  name: string
  code: string
  description: string
  scope: 'organization' | 'restaurant' | 'branch'
  is_system_role: boolean
  is_active: boolean
  permissions: Permission[]
  permission_codes: string[]
  created_at: string
  updated_at: string
}

// -----------------------------------------------------------------------------
// Phase 3 — User Role Assignments
// -----------------------------------------------------------------------------

export interface UserRoleAssignment {
  id: string
  user: number
  role: string
  role_detail: RoleMinimal
  organization: string | null
  organization_name: string | null
  restaurant: string | null
  restaurant_name: string | null
  branch: string | null
  branch_name: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface UserRoleAssignmentCreatePayload {
  role: string
  organization?: string | null
  restaurant?: string | null
  branch?: string | null
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
