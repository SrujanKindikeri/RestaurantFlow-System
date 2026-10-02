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

// -----------------------------------------------------------------------------
// Phase 4 — Counters
// -----------------------------------------------------------------------------

export type CounterType = 'MAIN_BILLING' | 'TAKEAWAY' | 'SNACKS' | 'DRIVE_THROUGH' | 'OTHER'
export type CounterStatus = 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE'
export type SessionStatus = 'OPEN' | 'CLOSED' | 'FORCE_CLOSED'

export interface Counter {
  id: string
  branch: string
  branch_name: string
  restaurant_id: string
  restaurant_name: string
  organization_id: string
  name: string
  code: string
  description: string
  counter_type: CounterType
  location: string
  status: CounterStatus
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CurrentSessionSummary {
  id: string
  opened_by_email: string
  opened_by_name: string
  opened_at: string
  opening_cash: string
  expected_cash: string
  status: SessionStatus
}

export interface ActiveAssignmentSummary {
  id: string
  user_id: number
  user_email: string
  user_name: string
  assigned_at: string
  expires_at: string | null
}

export interface CounterDetail extends Counter {
  current_session: CurrentSessionSummary | null
  active_assignments: ActiveAssignmentSummary[]
}

export interface CounterCreatePayload {
  branch: string
  name: string
  code: string
  description?: string
  counter_type?: CounterType
  location?: string
}

export type CounterUpdatePayload = Partial<CounterCreatePayload> & {
  status?: CounterStatus
}

// -----------------------------------------------------------------------------
// Phase 4 — Counter Assignments
// -----------------------------------------------------------------------------

export interface CounterAssignment {
  id: string
  counter: string
  counter_code: string
  counter_name: string
  branch_id: string
  branch_name: string
  user: number
  user_email: string
  user_name: string
  assigned_by: number | null
  assigned_by_email: string | null
  assigned_at: string
  expires_at: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CounterAssignmentCreatePayload {
  counter: string
  user: number
  expires_at?: string | null
}

// -----------------------------------------------------------------------------
// Phase 4 — Counter Sessions
// -----------------------------------------------------------------------------

export interface CounterSession {
  id: string
  counter: string
  counter_code: string
  counter_name: string
  branch_id: string
  branch_name: string
  restaurant_name: string
  shift: string | null
  shift_name: string | null
  opened_by: number
  opened_by_email: string
  opened_by_name: string
  closed_by: number | null
  closed_by_email: string | null
  opened_at: string
  closed_at: string | null
  opening_cash: string
  expected_cash: string
  actual_cash: string | null
  cash_difference: string | null
  status: SessionStatus
  closing_note: string
  created_at: string
  updated_at: string
}

export interface OpenSessionPayload {
  opening_cash: string
  shift?: string | null
}

export interface CloseSessionPayload {
  actual_cash: string
  closing_note?: string
}

export interface ForceCloseSessionPayload {
  reason: string
  actual_cash?: string | null
}

// -----------------------------------------------------------------------------
// Phase 4 — Shifts
// -----------------------------------------------------------------------------

export interface Shift {
  id: string
  branch: string
  branch_name: string
  name: string
  start_time: string
  end_time: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ShiftCreatePayload {
  branch: string
  name: string
  start_time: string
  end_time: string
}

// -----------------------------------------------------------------------------
// Phase 4 — Counter Dashboard
// -----------------------------------------------------------------------------

export interface CounterDashboardItem {
  id: string
  code: string
  name: string
  counter_type: CounterType
  status: CounterStatus
  branch_id: string
  branch_name: string
  restaurant_name: string
  current_session: {
    id: string
    opened_by_email: string
    opened_by_name: string
    opened_at: string
    opening_cash: string
    status: SessionStatus
  } | null
  assigned_cashier: {
    user_id: number
    user_name: string
    user_email: string
  } | null
}

export interface CounterDashboardResponse {
  branch_id: string | null
  counters: CounterDashboardItem[]
  summary: {
    total: number
    active: number
    sessions_open: number
    inactive: number
    maintenance: number
  }
}
