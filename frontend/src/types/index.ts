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
 
// -----------------------------------------------------------------------------
// Phase 5 — Menu
// -----------------------------------------------------------------------------

export type FoodType = 'VEG' | 'NON_VEG' | 'EGG' | 'VEGAN' | 'OTHER'

export interface TaxRate {
  id: string
  restaurant: string
  restaurant_name: string
  name: string
  code: string
  rate: string
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TaxRateMinimal {
  id: string
  name: string
  code: string
  rate: string
  is_active: boolean
}

export interface TaxRateCreatePayload {
  restaurant: string
  name: string
  code: string
  rate: string
  description?: string
}

export type TaxRateUpdatePayload = Partial<TaxRateCreatePayload> & {
  is_active?: boolean
}

export interface Category {
  id: string
  restaurant: string
  restaurant_name: string
  name: string
  slug: string
  description: string
  image: string | null
  display_order: number
  is_active: boolean
  item_count: number
  created_at: string
  updated_at: string
}

export interface CategoryCreatePayload {
  restaurant: string
  name: string
  description?: string
  display_order?: number
}

export type CategoryUpdatePayload = Partial<CategoryCreatePayload> & {
  is_active?: boolean
}

export interface MenuItem {
  id: string
  restaurant: string
  restaurant_name: string
  category: string
  category_name: string
  tax_rate: string | null
  tax_rate_detail: TaxRateMinimal | null
  name: string
  slug: string
  sku: string
  description: string
  short_description: string
  image: string | null
  food_type: FoodType
  display_order: number
  is_active: boolean
  is_available: boolean
  preparation_time_minutes: number
  created_at: string
  updated_at: string
}

export interface MenuItemDetail extends MenuItem {
  active_prices: {
    id: string
    branch: string
    branch_name: string
    price: string
    effective_from: string | null
    effective_to: string | null
  }[]
  branch_availability: {
    id: string
    branch: string
    branch_name: string
    is_available: boolean
    available_from: string | null
    available_to: string | null
  }[]
}

export interface MenuItemCreatePayload {
  restaurant: string
  category: string
  name: string
  sku?: string
  description?: string
  short_description?: string
  food_type?: FoodType
  tax_rate?: string | null
  display_order?: number
  preparation_time_minutes?: number
}

export type MenuItemUpdatePayload = Partial<MenuItemCreatePayload> & {
  is_active?: boolean
  is_available?: boolean
}

export interface MenuItemPrice {
  id: string
  menu_item: string
  menu_item_name: string
  menu_item_sku: string
  branch: string
  branch_name: string
  restaurant_id: string
  price: string
  effective_from: string | null
  effective_to: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface MenuItemPriceCreatePayload {
  menu_item: string
  branch: string
  price: string
  effective_from?: string | null
  effective_to?: string | null
  is_active?: boolean
}

export type MenuItemPriceUpdatePayload = Partial<MenuItemPriceCreatePayload>

export interface MenuItemBranch {
  id: string
  menu_item: string
  menu_item_name: string
  menu_item_sku: string
  branch: string
  branch_name: string
  restaurant_id: string
  is_available: boolean
  available_from: string | null
  available_to: string | null
  created_at: string
  updated_at: string
}

export interface MenuItemBranchCreatePayload {
  menu_item: string
  branch: string
  is_available?: boolean
  available_from?: string | null
  available_to?: string | null
}

export type MenuItemBranchUpdatePayload = Partial<MenuItemBranchCreatePayload>

// Catalog (POS read-optimized)
export interface CatalogItem {
  id: string
  name: string
  slug: string
  sku: string
  short_description: string
  food_type: FoodType
  image: string | null
  display_order: number
  preparation_time_minutes: number
  price: string | null
  tax_rate_code: string | null
  tax_rate_name: string | null
  tax_rate: string | null
}

export interface CatalogCategory {
  id: string
  name: string
  slug: string
  display_order: number
  items: CatalogItem[]
}

export interface BranchCatalog {
  branch: {
    id: string
    name: string
    restaurant_id: string
    restaurant_name: string
  }
  categories: CatalogCategory[]
}

// Dashboard
export interface MenuDashboardStats {
  categories: {
    total: number
    active: number
    inactive: number
  }
  items: {
    total: number
    active: number
    inactive: number
    available: number
    unavailable: number
  }
  branches: {
    id: string
    name: string
    restaurant_name: string
    available_items: number
  }[]
}

// -----------------------------------------------------------------------------
// Phase 6 — Dining Tables
// -----------------------------------------------------------------------------

export type TableStatus = 'ACTIVE' | 'INACTIVE'
export type TableSessionStatus = 'OPEN' | 'CLOSED'
export type OrderType = 'DINE_IN' | 'TAKEAWAY' | 'COUNTER'
export type OrderStatus = 'DRAFT' | 'CONFIRMED' | 'CANCELLED'

export interface ActiveOrderSummary {
  id: string
  order_number: string
  status: OrderStatus
  assigned_waiter: string | null
}

export interface DiningTable {
  id: string
  branch: string
  branch_name: string
  restaurant_id: string
  restaurant_name: string
  organization_id: string
  table_number: string
  name: string
  capacity: number
  section: string
  status: TableStatus
  display_order: number
  is_occupied: boolean
  active_session_id: string | null
  active_order: ActiveOrderSummary | null
  created_at: string
  updated_at: string
}

export interface DiningTableCreatePayload {
  branch: string
  table_number: string
  name?: string
  capacity: number
  section?: string
  display_order?: number
}

export type DiningTableUpdatePayload = Partial<DiningTableCreatePayload> & {
  status?: TableStatus
}

// -----------------------------------------------------------------------------
// Phase 6 — Table Sessions
// -----------------------------------------------------------------------------

export interface TableSession {
  id: string
  table: string
  table_number: string
  table_name: string
  branch_id: string
  branch_name: string
  restaurant_name: string
  opened_by: number
  opened_by_email: string
  opened_by_name: string
  closed_by: number | null
  closed_by_email: string | null
  opened_at: string
  closed_at: string | null
  status: TableSessionStatus
  guest_count: number
  notes: string
  created_at: string
  updated_at: string
}

export interface OpenTableSessionPayload {
  guest_count: number
  notes?: string
}

// -----------------------------------------------------------------------------
// Phase 6 — Orders
// -----------------------------------------------------------------------------

export interface OrderItem {
  id: string
  order: string
  menu_item: string
  item_name_snapshot: string
  sku_snapshot: string
  unit_price_snapshot: string
  tax_rate_snapshot: string
  tax_code_snapshot: string
  quantity: string
  notes: string
  line_total: string
  created_at: string
  updated_at: string
}

export interface Order {
  id: string
  branch: string
  branch_name: string
  restaurant_id: string
  restaurant_name: string
  organization_id: string
  order_number: string
  order_type: OrderType
  table: string | null
  table_number: string | null
  table_section: string | null
  table_session: string | null
  counter: string | null
  counter_code: string | null
  counter_name: string | null
  counter_session: string | null
  created_by: number
  created_by_email: string
  created_by_name: string
  assigned_waiter: number | null
  assigned_waiter_email: string | null
  assigned_waiter_name: string | null
  guest_count: number | null
  status: OrderStatus
  notes: string
  item_count: number
  preview_total: string
  confirmed_at: string | null
  cancelled_at: string | null
  cancellation_reason: string
  created_at: string
  updated_at: string
}

export interface OrderDetail extends Order {
  items: OrderItem[]
}

export interface CreateOrderPayload {
  branch: string
  order_type: OrderType
  table?: string | null
  table_session?: string | null
  counter?: string | null
  counter_session?: string | null
  guest_count?: number | null
  assigned_waiter?: number | null
  notes?: string
}

export interface AddOrderItemPayload {
  menu_item: string
  quantity: string
  notes?: string
}

export interface UpdateOrderItemPayload {
  quantity?: string
  notes?: string
}

export interface CancelOrderPayload {
  reason?: string
}

export interface AssignWaiterPayload {
  waiter: number
}

// POS draft order state (local, not server)
export interface DraftOrderItem {
  menu_item_id: string
  name: string
  sku: string
  price: string
  tax_rate: string | null
  tax_code: string | null
  quantity: number
  notes: string
}

// Combined for the POS screen
export interface POSCart {
  order_id: string | null         // null = not yet created on backend
  order_number: string | null
  items: DraftOrderItem[]
}

// =============================================================================
// Phase 7 — Kitchen / KDS
// =============================================================================

export type KitchenOrderStatus = 'NEW' | 'ACCEPTED' | 'PREPARING' | 'READY' | 'CANCELLED'
export type KitchenItemStatus  = 'NEW' | 'PREPARING' | 'READY' | 'CANCELLED'
export type KitchenPriority    = 'NORMAL' | 'HIGH' | 'URGENT'

export interface KitchenOrderItem {
  id: string
  order_item: string
  menu_item: string
  item_name_snapshot: string
  quantity: string
  notes: string
  food_type: string
  preparation_time_minutes: number
  status: KitchenItemStatus
  station: string
  started_at: string | null
  ready_at: string | null
  cancelled_at: string | null
  created_at: string
  updated_at: string
}

export interface KitchenOrder {
  id: string
  order: string
  order_number: string
  order_type: 'DINE_IN' | 'TAKEAWAY' | 'COUNTER'
  order_notes: string
  branch: string
  branch_name: string
  restaurant_id: string
  restaurant_name: string
  table_number: string | null
  table_section: string | null
  counter_code: string | null
  counter_name: string | null
  assigned_waiter_name: string | null
  status: KitchenOrderStatus
  priority: KitchenPriority
  kitchen_note: string
  received_at: string
  accepted_at: string | null
  started_at: string | null
  ready_at: string | null
  cancelled_at: string | null
  age_seconds: number
  item_count: number
  items: KitchenOrderItem[]
  accepted_by_name: string | null
  started_by_name: string | null
  completed_by_name: string | null
  cancelled_by_name: string | null
  cancelled_by: number | null
  cancellation_reason: string
  created_at: string
  updated_at: string
}

export interface KitchenOrdersParams {
  branch?: string
  status?: KitchenOrderStatus
  order_type?: string
  priority?: KitchenPriority
  table?: string
  counter?: string
  date?: string
  include_ready?: boolean
  include_cancelled?: boolean
  ordering?: string
}

export interface KitchenHistoryParams {
  branch?: string
  date?: string
  date_from?: string
  date_to?: string
  status?: KitchenOrderStatus
  order_type?: string
  ordering?: string
}

// WebSocket event types
export type KitchenEventType =
  | 'kitchen.order.created'
  | 'kitchen.order.accepted'
  | 'kitchen.order.preparing'
  | 'kitchen.order.ready'
  | 'kitchen.order.cancelled'
  | 'kitchen.item.preparing'
  | 'kitchen.item.ready'
  | 'kitchen.priority.changed'

export interface KitchenEvent {
  event_id: string
  event: KitchenEventType
  kitchen_order_id: string
  order_id: string
  order_number: string
  order_type: string
  status: KitchenOrderStatus
  priority: KitchenPriority
  branch_id: string
  received_at: string
  timestamp: string
  table: string | null
  counter: string | null
  item_id?: string
  item_name?: string
  old_priority?: KitchenPriority
  new_priority?: KitchenPriority
}

export interface KitchenSyncMessage {
  type: 'kitchen.sync'
  branch_id: string
  orders: KitchenOrder[]
}

export interface KitchenEventMessage {
  type: 'kitchen.event'
  payload: KitchenEvent
}

// =============================================================================
// Phase 8 — Billing
// =============================================================================

export type BillStatus = 'DRAFT' | 'FINALIZED' | 'CANCELLED' | 'VOID'
export type DiscountType = 'PERCENTAGE' | 'FIXED_AMOUNT'
export type CorrectionType = 'ITEM_CORRECTION' | 'DISCOUNT_CORRECTION' | 'TAX_CORRECTION' | 'CANCELLATION'
export type CorrectionStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED'

export interface BillItem {
  id: string
  order_item: string
  menu_item: string
  item_name_snapshot: string
  sku_snapshot: string
  quantity: string
  unit_price: string
  gross_amount: string
  discount_amount: string
  taxable_amount: string
  tax_rate: string
  tax_code: string
  tax_amount: string
  total_amount: string
  created_at: string
}

export interface Bill {
  id: string
  bill_number: string
  order: string
  order_number: string | null
  order_type: OrderType | null
  branch: string
  branch_name: string
  restaurant_id: string
  restaurant_name: string
  organization_id: string
  table_number: string | null
  counter_code: string | null
  counter_session: string | null
  status: BillStatus
  discount_type: DiscountType | null
  discount_value: string
  subtotal: string
  discount_amount: string
  taxable_amount: string
  tax_amount: string
  tax_breakdown: Record<string, string>
  rounding_amount: string
  grand_total: string
  notes: string
  created_by: number
  created_by_email: string | null
  created_by_name: string | null
  finalized_by: number | null
  finalized_by_email: string | null
  finalized_by_name: string | null
  finalized_at: string | null
  cancelled_by: number | null
  cancelled_by_email: string | null
  cancelled_at: string | null
  cancellation_reason: string
  correction_count: number
  has_pending_correction: boolean
  items: BillItem[]
  created_at: string
  updated_at: string
}

export type BillSummary = Omit<Bill, 'items' | 'tax_breakdown' | 'organization_id' | 'table_number' | 'counter_code' | 'counter_session'>

export interface BillCalculation {
  subtotal: string
  discount_amount: string
  taxable_amount: string
  tax_amount: string
  tax_breakdown: Record<string, string>
  rounding_amount: string
  grand_total: string
}

export interface ApplyDiscountPayload {
  discount_type: DiscountType
  discount_value: string
}

export interface FinalizeBillPayload {
  notes?: string
}

export interface CancelBillPayload {
  reason: string
}

export interface VoidBillPayload {
  reason: string
}

export interface BillCorrectionRequest {
  id: string
  bill: string
  bill_number: string
  correction_type: CorrectionType
  reason: string
  requested_data: Record<string, unknown>
  status: CorrectionStatus
  requested_by: number
  requested_by_email: string | null
  requested_by_name: string | null
  reviewed_by: number | null
  reviewed_by_email: string | null
  reviewed_by_name: string | null
  reviewed_at: string | null
  review_note: string
  created_at: string
  updated_at: string
}

export interface CreateCorrectionPayload {
  correction_type: CorrectionType
  reason: string
}

export interface ReviewCorrectionPayload {
  review_note?: string
}

export interface BillReceiptData {
  bill_number: string
  order_number: string
  order_type: string
  date: string
  finalized_at: string | null
  currency: string
  restaurant: {
    name: string
    address: string
    city: string
    state: string
    postal_code: string
    phone: string
    email: string
    tax_id: string
  }
  branch: {
    name: string
    address: string
    city: string
    state: string
    postal_code: string
    phone: string
  }
  cashier: string | null
  table_number: string | null
  counter_code: string | null
  receipt_header: string
  receipt_footer: string
  items: {
    name: string
    sku: string
    quantity: string
    unit_price: string
    gross_amount: string
    discount_amount: string
    taxable_amount: string
    tax_rate: string
    tax_code: string
    tax_amount: string
    total_amount: string
  }[]
  subtotal: string
  discount_amount: string
  discount_type: DiscountType | null
  discount_value: string
  taxable_amount: string
  tax_breakdown: Record<string, string>
  tax_amount: string
  rounding_amount: string
  grand_total: string
  status: BillStatus
  correction_count: number
}

export interface BillListParams {
  status?: BillStatus
  order_type?: OrderType
  branch?: string
  bill_number?: string
  order_number?: string
  cashier?: string
  date_from?: string
  date_to?: string
  page?: number
}

// =============================================================================
// Phase 9 — Payments
// =============================================================================

export type PaymentStatus =
  | 'PENDING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'REFUNDED'
  | 'PARTIALLY_REFUNDED'

export type PaymentMethod =
  | 'CASH'
  | 'UPI'
  | 'CARD'
  | 'WALLET'
  | 'NET_BANKING'
  | 'BANK_TRANSFER'
  | 'CHEQUE'
  | 'CREDIT'
  | 'OTHER'

export type BillPaymentStatus = 'UNPAID' | 'PARTIALLY_PAID' | 'PAID' | 'OVERPAID'

export type RefundStatus =
  | 'REQUESTED'
  | 'APPROVED'
  | 'REJECTED'
  | 'PROCESSED'
  | 'CANCELLED'

// ---------------------------------------------------------------------------
// Payment
// ---------------------------------------------------------------------------

export interface PaymentRefundItem {
  id: string
  refund_number: string
  payment: string
  amount: string
  status: RefundStatus
  reason: string
  rejection_reason: string
  notes: string
  transaction_reference: string
  requested_by: number | null
  requested_by_email: string | null
  requested_by_name: string | null
  approved_by: number | null
  approved_by_email: string | null
  approved_by_name: string | null
  processed_by: number | null
  processed_by_name: string | null
  requested_at: string
  approved_at: string | null
  processed_at: string | null
  rejected_at: string | null
  created_at: string
  updated_at: string
}

export interface Payment {
  id: string
  payment_number: string
  bill: string
  bill_number: string | null
  branch: string
  branch_name: string | null
  counter: string | null
  counter_code: string | null
  counter_session: string | null
  counter_session_id: string | null
  amount: string
  payment_method: PaymentMethod
  status: PaymentStatus
  transaction_reference: string
  provider_reference: string
  cash_received: string | null
  change_amount: string | null
  notes: string
  idempotency_key: string
  initiated_by: number | null
  initiated_by_email: string | null
  initiated_by_name: string | null
  completed_by: number | null
  completed_by_name: string | null
  completed_at: string | null
  failed_at: string | null
  cancelled_at: string | null
  cancellation_reason: string
  refunds: PaymentRefundItem[]
  created_at: string
  updated_at: string
}

export type PaymentSummary = Omit<Payment, 'refunds' | 'provider_reference' | 'counter_session_id' | 'notes'>

// ---------------------------------------------------------------------------
// Bill Payment Summary
// ---------------------------------------------------------------------------

export interface BillPaymentSummary {
  bill_id: string
  bill_number: string
  bill_total: string
  total_paid: string
  total_refunded: string
  remaining: string
  payment_status: BillPaymentStatus
  payments: Payment[]
}

// ---------------------------------------------------------------------------
// Create/Action payloads
// ---------------------------------------------------------------------------

export interface CreatePaymentPayload {
  bill_id: string
  amount: string
  payment_method: PaymentMethod
  cash_received?: string | null
  transaction_reference?: string
  provider_reference?: string
  notes?: string
  idempotency_key?: string
  counter_session?: string | null
}

export interface CancelPaymentPayload {
  reason: string
}

export interface CreateRefundPayload {
  amount: string
  reason: string
  notes?: string
}

export interface RejectRefundPayload {
  reason: string
}

export interface ProcessRefundPayload {
  transaction_reference?: string
  notes?: string
}

// ---------------------------------------------------------------------------
// Payment list filters
// ---------------------------------------------------------------------------

export interface PaymentListParams {
  bill?: string
  branch?: string
  status?: PaymentStatus
  payment_method?: PaymentMethod
  date_from?: string
  date_to?: string
  counter?: string
  counter_session?: string
  page?: number
}

// ---------------------------------------------------------------------------
// Receipt — Phase 9 additions to BillReceiptData
// ---------------------------------------------------------------------------

export interface ReceiptPaymentLine {
  payment_number: string
  payment_method: PaymentMethod
  amount: string
  cash_received: string | null
  change_amount: string | null
  transaction_reference: string
  completed_at: string | null
}

// Extends the existing BillReceiptData with payment fields
export interface BillReceiptDataV9 extends BillReceiptData {
  payment_status: BillPaymentStatus
  total_paid: string
  total_refunded: string
  remaining: string
  payments: ReceiptPaymentLine[]
}

// ---------------------------------------------------------------------------
// Audit log
// ---------------------------------------------------------------------------

export interface PaymentAuditLog {
  id: string
  payment: string
  refund: string | null
  actor: number | null
  actor_email: string | null
  actor_name: string | null
  action: string
  old_status: string
  new_status: string
  amount: string | null
  reason: string
  metadata: Record<string, unknown>
  created_at: string
}

// =============================================================================
// Phase 10 — Inventory & Stock Management Types
// =============================================================================

// ---------------------------------------------------------------------------
// Enums / constants
// ---------------------------------------------------------------------------

export type UnitOfMeasurement =
  | 'KG' | 'GRAM' | 'LITRE' | 'MILLILITRE'
  | 'PIECE' | 'PACK' | 'BOX' | 'BOTTLE' | 'DOZEN'

export type LocationType =
  | 'MAIN_STORE' | 'KITCHEN' | 'COLD_STORAGE'
  | 'FREEZER' | 'BAR' | 'DRY_STORE' | 'OTHER'

export type MovementType =
  | 'PURCHASE' | 'PURCHASE_RETURN' | 'TRANSFER_IN' | 'TRANSFER_OUT'
  | 'WASTAGE' | 'ADJUSTMENT_IN' | 'ADJUSTMENT_OUT'
  | 'CONSUMPTION' | 'OPENING_STOCK' | 'CORRECTION'

export type PurchaseOrderStatus =
  | 'DRAFT' | 'SUBMITTED' | 'APPROVED'
  | 'PARTIALLY_RECEIVED' | 'RECEIVED' | 'CANCELLED'

export type TransferStatus =
  | 'DRAFT' | 'REQUESTED' | 'APPROVED' | 'COMPLETED' | 'CANCELLED'

export type WastageType =
  | 'SPOILED' | 'DAMAGED' | 'EXPIRED' | 'PREPARATION_LOSS' | 'OTHER'

export type WastageStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'RECORDED'

export type StockStatus = 'IN_STOCK' | 'LOW_STOCK' | 'OUT_OF_STOCK'

// ---------------------------------------------------------------------------
// Inventory Category
// ---------------------------------------------------------------------------

export interface InventoryCategory {
  id: string
  restaurant: string
  restaurant_name: string
  name: string
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Inventory Item
// ---------------------------------------------------------------------------

export interface InventoryItem {
  id: string
  restaurant: string
  restaurant_name: string
  category: string | null
  category_name: string | null
  name: string
  sku: string
  description: string
  default_unit: UnitOfMeasurement
  minimum_stock: string
  reorder_level: string
  maximum_stock: string
  average_cost: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Storage Location
// ---------------------------------------------------------------------------

export interface StorageLocation {
  id: string
  branch: string
  branch_name: string
  restaurant_name: string
  name: string
  code: string
  location_type: LocationType
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Stock Balance
// ---------------------------------------------------------------------------

export interface StockBalance {
  id: string
  inventory_item: string
  item_name: string
  item_sku: string
  item_unit: UnitOfMeasurement
  category_name: string | null
  storage_location: string
  location_name: string
  location_code: string
  branch_name: string
  quantity: string
  reserved_quantity: string
  available_quantity: string
  average_cost: string
  reorder_level: string
  stock_status: StockStatus
  last_movement_at: string | null
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Stock Movement
// ---------------------------------------------------------------------------

export interface StockMovement {
  id: string
  inventory_item: string
  item_name: string
  item_sku: string
  item_unit: UnitOfMeasurement
  storage_location: string
  location_name: string
  branch_name: string
  movement_type: MovementType
  quantity: string
  unit_cost: string
  total_cost: string
  reference_type: string
  reference_id: string | null
  reason: string
  performed_by: number
  performed_by_email: string
  performed_by_name: string
  created_at: string
}

// ---------------------------------------------------------------------------
// Supplier
// ---------------------------------------------------------------------------

export interface Supplier {
  id: string
  restaurant: string
  restaurant_name: string
  name: string
  code: string
  contact_person: string
  phone: string
  email: string
  address: string
  tax_identifier: string
  notes: string
  is_active: boolean
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Purchase Order
// ---------------------------------------------------------------------------

export interface PurchaseOrderItem {
  id: string
  inventory_item: string
  item_name: string
  item_sku: string
  quantity: string
  unit: UnitOfMeasurement
  unit_cost: string
  tax_rate: string
  discount_amount: string
  total_amount: string
  received_quantity: string
  remaining_quantity: string
  notes: string
  created_at: string
}

export interface PurchaseOrder {
  id: string
  purchase_number: string
  restaurant: string
  restaurant_name: string
  branch: string
  branch_name: string
  supplier: string
  supplier_name: string
  status: PurchaseOrderStatus
  order_date: string | null
  expected_date: string | null
  subtotal: string
  tax_amount: string
  discount_amount: string
  total_amount: string
  notes: string
  created_by: number
  created_by_email: string
  approved_by: number | null
  approved_by_email: string | null
  received_by: number | null
  received_by_email: string | null
  approved_at: string | null
  received_at: string | null
  items: PurchaseOrderItem[]
  created_at: string
  updated_at: string
}

export interface PurchaseOrderSummary extends Omit<PurchaseOrder, 'items'> {}

// ---------------------------------------------------------------------------
// Purchase Receipt
// ---------------------------------------------------------------------------

export interface PurchaseReceiptItem {
  id: string
  purchase_order_item: string
  item_name: string
  quantity_received: string
  unit_cost: string
}

export interface PurchaseReceipt {
  id: string
  purchase_order: string
  purchase_number: string
  received_by: number
  received_by_email: string
  storage_location: string
  location_name: string
  received_at: string
  notes: string
  items: PurchaseReceiptItem[]
}

// ---------------------------------------------------------------------------
// Stock Transfer
// ---------------------------------------------------------------------------

export interface StockTransferItem {
  id: string
  inventory_item: string
  item_name: string
  item_sku: string
  quantity: string
  unit: UnitOfMeasurement
}

export interface StockTransfer {
  id: string
  transfer_number: string
  restaurant: string
  restaurant_name: string
  source_location: string
  source_location_name: string
  destination_location: string
  destination_location_name: string
  status: TransferStatus
  notes: string
  requested_by: number
  requested_by_email: string
  approved_by: number | null
  approved_by_email: string | null
  completed_by: number | null
  completed_by_email: string | null
  requested_at: string | null
  approved_at: string | null
  completed_at: string | null
  items: StockTransferItem[]
  created_at: string
  updated_at: string
}

export interface StockTransferSummary extends Omit<StockTransfer, 'items'> {}

// ---------------------------------------------------------------------------
// Stock Wastage
// ---------------------------------------------------------------------------

export interface StockWastage {
  id: string
  inventory_item: string
  item_name: string
  item_sku: string
  storage_location: string
  location_name: string
  branch_name: string
  quantity: string
  unit: UnitOfMeasurement
  wastage_type: WastageType
  reason: string
  estimated_cost: string
  status: WastageStatus
  recorded_by: number
  recorded_by_email: string
  approved_by: number | null
  approved_by_email: string | null
  approved_at: string | null
  rejection_reason: string
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Stock Adjustment
// ---------------------------------------------------------------------------

export interface StockAdjustment {
  id: string
  inventory_item: string
  item_name: string
  item_sku: string
  storage_location: string
  location_name: string
  quantity_before: string
  quantity_physical: string
  quantity_difference: string
  unit: UnitOfMeasurement
  reason: string
  adjusted_by: number
  adjusted_by_email: string
  stock_movement: string | null
  created_at: string
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface InventoryDashboard {
  total_items: number
  low_stock: number
  out_of_stock: number
  pending_purchases: number
  pending_transfers: number
  pending_wastage: number
}

// ---------------------------------------------------------------------------
// API payload types
// ---------------------------------------------------------------------------

export interface CreateInventoryCategoryPayload {
  restaurant_id: string
  name: string
  description?: string
}

export interface CreateInventoryItemPayload {
  restaurant_id: string
  category_id?: string | null
  name: string
  sku: string
  description?: string
  default_unit: UnitOfMeasurement
  minimum_stock?: string
  reorder_level?: string
  maximum_stock?: string
}

export interface CreateStorageLocationPayload {
  branch_id: string
  name: string
  code: string
  location_type: LocationType
  description?: string
}

export interface CreateSupplierPayload {
  restaurant_id: string
  name: string
  code: string
  contact_person?: string
  phone?: string
  email?: string
  address?: string
  tax_identifier?: string
  notes?: string
}

export interface CreatePurchaseOrderItemPayload {
  inventory_item_id: string
  quantity: string
  unit: UnitOfMeasurement
  unit_cost: string
  tax_rate?: string
  discount_amount?: string
  notes?: string
}

export interface CreatePurchaseOrderPayload {
  restaurant_id: string
  branch_id: string
  supplier_id: string
  order_date?: string | null
  expected_date?: string | null
  discount_amount?: string
  notes?: string
  items: CreatePurchaseOrderItemPayload[]
}

export interface ReceiveItemPayload {
  purchase_order_item_id: string
  quantity_received: string
}

export interface ReceivePurchaseOrderPayload {
  storage_location_id: string
  notes?: string
  items: ReceiveItemPayload[]
}

export interface CreateTransferItemPayload {
  inventory_item_id: string
  quantity: string
  unit: UnitOfMeasurement
}

export interface CreateStockTransferPayload {
  restaurant_id: string
  source_location_id: string
  destination_location_id: string
  notes?: string
  items: CreateTransferItemPayload[]
}

export interface CreateStockWastagePayload {
  inventory_item_id: string
  storage_location_id: string
  quantity: string
  unit: UnitOfMeasurement
  wastage_type: WastageType
  reason: string
}

export interface CreateStockAdjustmentPayload {
  inventory_item_id: string
  storage_location_id: string
  quantity_physical: string
  unit: UnitOfMeasurement
  reason: string
}

// =============================================================================
// Phase 11 — Recipes & Inventory Consumption Types
// =============================================================================

// ---------------------------------------------------------------------------
// Enums
// ---------------------------------------------------------------------------

export type RecipeStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE' | 'ARCHIVED'
export type ConsumptionTrigger = 'KITCHEN_STARTED' | 'KITCHEN_COMPLETED'
export type BatchStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED' | 'REVERSED'
export type ConsumptionStatus = 'PENDING' | 'CONSUMED' | 'FAILED' | 'REVERSED'

// ---------------------------------------------------------------------------
// RecipeItem (ingredient line)
// ---------------------------------------------------------------------------

export interface RecipeItem {
  id: string
  recipe: string
  inventory_item: string
  inventory_item_name: string
  inventory_item_sku: string
  inventory_item_unit: UnitOfMeasurement
  quantity: string
  unit: UnitOfMeasurement
  preparation_loss_percentage: string
  effective_quantity: string
  notes: string
  display_order: number
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Recipe (list)
// ---------------------------------------------------------------------------

export interface Recipe {
  id: string
  restaurant: string
  restaurant_name: string
  menu_item: string
  menu_item_name: string
  name: string
  version: number
  status: RecipeStatus
  yield_quantity: string
  yield_unit: UnitOfMeasurement
  effective_from: string | null
  effective_to: string | null
  created_by: number | null
  created_by_email: string | null
  approved_by: number | null
  approved_by_email: string | null
  approved_at: string | null
  ingredient_count: number
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// Recipe (detail — includes ingredients)
// ---------------------------------------------------------------------------

export interface RecipeDetail extends Recipe {
  preparation_notes: string
  ingredients: RecipeItem[]
}

// ---------------------------------------------------------------------------
// Recipe cost
// ---------------------------------------------------------------------------

export interface RecipeCostIngredient {
  inventory_item_id: string
  inventory_item_name: string
  recipe_quantity: string
  recipe_unit: UnitOfMeasurement
  preparation_loss_percentage: string
  effective_quantity: string
  converted_quantity: string
  item_unit: UnitOfMeasurement
  unit_cost: string
  line_cost: string
}

export interface RecipeCost {
  recipe_id: string
  recipe_name: string
  version: number
  status: RecipeStatus
  yield_quantity: string
  yield_unit: UnitOfMeasurement
  total_cost: string
  ingredients: RecipeCostIngredient[]
}

// ---------------------------------------------------------------------------
// StockConsumption
// ---------------------------------------------------------------------------

export interface StockConsumption {
  id: string
  batch: string
  order: string | null
  order_number: string | null
  order_item: string | null
  restaurant: string
  branch: string
  branch_name: string
  recipe: string | null
  recipe_version: number | null
  menu_item_name: string | null
  inventory_item: string
  inventory_item_name: string
  inventory_item_sku: string
  storage_location: string
  location_name: string
  quantity: string
  unit: UnitOfMeasurement
  unit_cost: string
  total_cost: string
  status: ConsumptionStatus
  consumed_at: string | null
  consumed_by: number | null
  consumed_by_email: string | null
  reference_type: string
  reference_id: string | null
  created_at: string
}

// ---------------------------------------------------------------------------
// ConsumptionBatch (list)
// ---------------------------------------------------------------------------

export interface ConsumptionBatch {
  id: string
  order: string | null
  order_number: string | null
  branch: string
  branch_name: string
  status: BatchStatus
  trigger: string
  triggered_by: number | null
  triggered_by_email: string | null
  triggered_at: string
  completed_at: string | null
  failure_reason: string
  consumption_count: number
  total_cost: string
  created_at: string
}

// ---------------------------------------------------------------------------
// ConsumptionBatch (detail — includes consumption items)
// ---------------------------------------------------------------------------

export interface ConsumptionBatchDetail extends ConsumptionBatch {
  items: StockConsumption[]
}

// ---------------------------------------------------------------------------
// BranchConsumptionConfig
// ---------------------------------------------------------------------------

export interface BranchConsumptionConfig {
  id: string
  branch: string
  branch_name: string
  consumption_trigger: ConsumptionTrigger
  default_consumption_location: string | null
  location_name: string | null
  created_at: string
  updated_at: string
}

// ---------------------------------------------------------------------------
// API Payload types — Recipes
// ---------------------------------------------------------------------------

export interface CreateRecipePayload {
  restaurant_id: string
  menu_item_id: string
  name: string
  yield_quantity?: string
  yield_unit?: UnitOfMeasurement
  preparation_notes?: string
  effective_from?: string | null
  effective_to?: string | null
}

export interface UpdateRecipePayload {
  name?: string
  yield_quantity?: string
  yield_unit?: UnitOfMeasurement
  preparation_notes?: string
  effective_from?: string | null
  effective_to?: string | null
}

export interface AddRecipeItemPayload {
  inventory_item_id: string
  quantity: string
  unit: UnitOfMeasurement
  preparation_loss_percentage?: string
  notes?: string
  display_order?: number
}

export interface UpdateRecipeItemPayload {
  quantity?: string
  unit?: UnitOfMeasurement
  preparation_loss_percentage?: string
  notes?: string
  display_order?: number
}

// ---------------------------------------------------------------------------
// API Payload types — Consumption
// ---------------------------------------------------------------------------

export interface ManualConsumptionPayload {
  branch_id: string
  inventory_item_id: string
  storage_location_id: string
  quantity: string
  unit: UnitOfMeasurement
  reason: string
}

export interface ReversalPayload {
  reason?: string
}

export interface UpdateBranchConsumptionConfigPayload {
  branch_id: string
  consumption_trigger?: ConsumptionTrigger
  default_consumption_location_id?: string | null
}

// ---------------------------------------------------------------------------
// List filter params
// ---------------------------------------------------------------------------

export interface RecipeListParams {
  restaurant?: string
  menu_item?: string
  status?: RecipeStatus
  search?: string
}

export interface ConsumptionListParams {
  branch?: string
  status?: BatchStatus
  date?: string
  order?: string
}
