// =============================================================================
// RestaurantFlow — CRM API Service
// Phase 17
// =============================================================================

import api from './api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Customer {
  id: string
  customer_number: string
  first_name: string
  last_name: string
  display_name: string
  masked_phone: string
  masked_email: string
  phone?: string
  email?: string
  date_of_birth?: string | null
  gender?: string
  address?: string
  city?: string
  state?: string
  postal_code?: string
  country?: string
  notes?: string
  preferred_language?: string
  is_active: boolean
  is_blocked: boolean
  blocked_reason?: string
  total_orders: number
  total_visits: number
  lifetime_spend: string
  first_order_at?: string | null
  last_order_at?: string | null
  last_visit_at?: string | null
  created_at: string
  updated_at: string
}

export interface CustomerSearchResult {
  id: string
  customer_number: string
  display_name: string
  masked_phone: string
  masked_email: string
  loyalty_points: number
  last_visit_at?: string | null
}

export interface LoyaltyAccount {
  id: string
  program_name: string
  points_balance: number
  lifetime_points_earned: number
  lifetime_points_redeemed: number
  created_at: string
  updated_at: string
}

export interface LoyaltyTransaction {
  id: string
  transaction_type: string
  points: number
  balance_before: number
  balance_after: number
  reference_type: string
  reference_id: string
  reason: string
  created_at: string
}

export interface LoyaltyReward {
  id: string
  name: string
  description: string
  reward_type: string
  points_required: number
  reward_value?: string | null
  discount_type?: string
  discount_value?: string | null
  max_discount_amount?: string | null
  is_active: boolean
  valid_from?: string | null
  valid_until?: string | null
  created_at: string
  updated_at: string
}

export interface RewardRedemption {
  id: string
  reward_name: string
  points_used: number
  status: string
  reference_code: string
  redeemed_at?: string | null
  expires_at?: string | null
  created_at: string
}

export interface CustomerFeedback {
  id: string
  branch_name: string
  rating: number
  service_rating?: number | null
  food_rating?: number | null
  ambience_rating?: number | null
  comment: string
  status: string
  created_at: string
  updated_at: string
}

export interface CustomerSegment {
  id: string
  name: string
  code: string
  description: string
  criteria: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CustomerTag {
  id: string
  name: string
  code: string
  description: string
  is_active: boolean
  created_at: string
}

export interface CustomerConsent {
  id: string
  consent_type: string
  status: string
  source: string
  granted_at?: string | null
  revoked_at?: string | null
  updated_at: string
}

export interface CustomerVisit {
  id: string
  visit_number: number
  branch_name: string
  visit_type: string
  status: string
  visit_started_at: string
  visit_completed_at?: string | null
  guest_count: number
  created_at: string
}

export interface CRMDashboardKPIs {
  total_customers: number
  new_customers: number
  returning_customers: number
  inactive_customers: number
  avg_lifetime_spend: string | null
  avg_visits: number | null
  avg_orders: number | null
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ---------------------------------------------------------------------------
// Customer endpoints
// ---------------------------------------------------------------------------

export const crmApi = {
  // List / search
  listCustomers: (params?: Record<string, string>) =>
    api.get<PaginatedResponse<Customer>>('/crm/customers/', { params }),

  searchCustomers: (q: string, restaurantId?: string) =>
    api.get<{ results: CustomerSearchResult[] }>('/crm/customers/search/', {
      params: { q, ...(restaurantId ? { restaurant_id: restaurantId } : {}) },
    }),

  getCustomer: (id: string) =>
    api.get<Customer>(`/crm/customers/${id}/`),

  createCustomer: (data: Record<string, unknown>) =>
    api.post<Customer>('/crm/customers/', data),

  updateCustomer: (id: string, data: Record<string, unknown>) =>
    api.patch<Customer>(`/crm/customers/${id}/`, data),

  // Sub-resources
  getCustomerOrders: (id: string, params?: Record<string, string>) =>
    api.get<PaginatedResponse<unknown>>(`/crm/customers/${id}/orders/`, { params }),

  getCustomerVisits: (id: string, params?: Record<string, string>) =>
    api.get<PaginatedResponse<CustomerVisit>>(`/crm/customers/${id}/visits/`, { params }),

  getCustomerSpending: (id: string, params?: Record<string, string>) =>
    api.get<PaginatedResponse<unknown>>(`/crm/customers/${id}/spending/`, { params }),

  getCustomerLoyalty: (id: string) =>
    api.get<LoyaltyAccount[]>(`/crm/customers/${id}/loyalty/`),

  getCustomerRewards: (id: string) =>
    api.get<RewardRedemption[]>(`/crm/customers/${id}/rewards/`),

  getCustomerTags: (id: string) =>
    api.get<{ tag: CustomerTag; is_active: boolean }[]>(`/crm/customers/${id}/tags/`),

  assignTag: (customerId: string, tagId: string) =>
    api.post(`/crm/customers/${customerId}/tags/`, { tag_id: tagId }),

  removeTag: (customerId: string, tagId: string) =>
    api.delete(`/crm/customers/${customerId}/tags/${tagId}/`),

  getCustomerFeedback: (id: string) =>
    api.get<PaginatedResponse<CustomerFeedback>>(`/crm/customers/${id}/feedback/`),

  getCustomerPreferences: (id: string) =>
    api.get(`/crm/customers/${id}/preferences/`),

  updateCustomerPreferences: (id: string, data: Record<string, unknown>) =>
    api.patch(`/crm/customers/${id}/preferences/`, data),

  redeemReward: (customerId: string, rewardId: string) =>
    api.post<RewardRedemption>(`/crm/customers/${customerId}/rewards/${rewardId}/redeem/`),

  // Consents
  getConsents: (customerId: string) =>
    api.get<CustomerConsent[]>(`/crm/consents/?customer_id=${customerId}`),

  updateConsent: (customerId: string, data: Record<string, unknown>) =>
    api.post<CustomerConsent>('/crm/consents/', { customer_id: customerId, ...data }),

  // Merge requests
  requestMerge: (data: { source_customer_id: string; target_customer_id: string; reason: string }) =>
    api.post('/crm/customer-merge-requests/', data),

  approveMerge: (id: string) =>
    api.post(`/crm/customer-merge-requests/${id}/approve/`),

  rejectMerge: (id: string) =>
    api.post(`/crm/customer-merge-requests/${id}/reject/`),

  // Segments
  listSegments: (params?: Record<string, string>) =>
    api.get<CustomerSegment[]>('/crm/segments/', { params }),

  createSegment: (data: Record<string, unknown>) =>
    api.post<CustomerSegment>('/crm/segments/', data),

  updateSegment: (id: string, data: Record<string, unknown>) =>
    api.patch<CustomerSegment>(`/crm/segments/${id}/`, data),

  // Loyalty programs
  getLoyaltyPrograms: () =>
    api.get<LoyaltyAccount[]>('/crm/loyalty/program/'),

  createLoyaltyProgram: (data: Record<string, unknown>) =>
    api.post('/crm/loyalty/program/', data),

  // Rewards (management)
  listRewards: (params?: Record<string, string>) =>
    api.get<PaginatedResponse<LoyaltyReward>>('/crm/rewards/', { params }),

  createReward: (data: Record<string, unknown>) =>
    api.post<LoyaltyReward>('/crm/rewards/', data),

  updateReward: (id: string, data: Record<string, unknown>) =>
    api.patch<LoyaltyReward>(`/crm/rewards/${id}/`, data),

  // Feedback
  listFeedback: (params?: Record<string, string>) =>
    api.get<PaginatedResponse<CustomerFeedback>>('/crm/feedback/', { params }),

  createFeedback: (data: Record<string, unknown>) =>
    api.post<CustomerFeedback>('/crm/feedback/', data),

  getFeedback: (id: string) =>
    api.get<CustomerFeedback>(`/crm/feedback/${id}/`),

  moderateFeedback: (id: string, data: Record<string, unknown>) =>
    api.post(`/crm/feedback/${id}/moderate/`, data),

  // Dashboard
  getDashboard: (restaurantId?: string) =>
    api.get<{ kpis: CRMDashboardKPIs; top_customers: Customer[]; feedback_summary: unknown }>(
      '/crm/dashboard/',
      { params: restaurantId ? { restaurant_id: restaurantId } : {} },
    ),
}

export default crmApi
