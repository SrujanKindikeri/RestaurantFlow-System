// =============================================================================
// RestaurantFlow — Marketing API Service
// Phase 18
// =============================================================================

import api from './api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CampaignStatus =
  | 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'SCHEDULED'
  | 'RUNNING' | 'PAUSED' | 'COMPLETED' | 'CANCELLED' | 'FAILED'

export type CampaignType =
  | 'PROMOTION' | 'LOYALTY' | 'REACTIVATION' | 'NEW_CUSTOMER'
  | 'REPEAT_CUSTOMER' | 'BIRTHDAY' | 'SEASONAL' | 'EVENT'
  | 'FEEDBACK' | 'ANNOUNCEMENT' | 'OTHER'

export type PromotionType =
  | 'PERCENTAGE_DISCOUNT' | 'FIXED_DISCOUNT' | 'FREE_ITEM'
  | 'BUY_X_GET_Y' | 'LOYALTY_BONUS' | 'OTHER'

export type DiscountType = 'PERCENTAGE' | 'FIXED_AMOUNT'

export interface Campaign {
  id: string
  name: string
  code: string
  description: string
  campaign_type: CampaignType
  status: CampaignStatus
  start_at: string | null
  end_at: string | null
  audience_type: string
  restaurant: string | null
  restaurant_name: string
  branch: string | null
  branch_name: string
  company: string
  company_name: string
  created_by_email: string
  approved_by_email: string
  approved_at: string | null
  cancelled_by_email: string
  cancelled_at: string | null
  cancellation_reason: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface CampaignListItem
  extends Pick<Campaign, 'id' | 'name' | 'code' | 'campaign_type' | 'status'
    | 'start_at' | 'end_at' | 'audience_type' | 'restaurant' | 'restaurant_name'
    | 'branch' | 'branch_name' | 'created_by_email' | 'created_at' | 'updated_at'> {}

export interface CampaignApproval {
  id: string
  campaign: string
  campaign_code: string
  requested_by_email: string
  reviewed_by_email: string
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED'
  review_note: string
  requested_at: string
  reviewed_at: string | null
  created_at: string
}

export interface CampaignAudience {
  id: string
  campaign: string
  audience_type: string
  criteria: Record<string, unknown>
  estimated_count: number
  created_at: string
  updated_at: string
}

export interface CampaignAudienceMember {
  id: string
  campaign: string
  customer: string
  customer_number: string
  customer_name: string
  status: 'ELIGIBLE' | 'EXCLUDED' | 'CONTACTED' | 'CONVERTED' | 'UNSUBSCRIBED'
  added_at: string
  removed_at: string | null
  metadata: Record<string, unknown>
}

export interface Promotion {
  id: string
  name: string
  code: string
  description: string
  promotion_type: PromotionType
  discount_type: DiscountType | null
  discount_value: string | null
  max_discount_amount: string | null
  minimum_order_amount: string | null
  minimum_quantity: number | null
  free_item: string | null
  free_item_name: string
  buy_quantity: number | null
  get_quantity: number | null
  loyalty_bonus_multiplier: string | null
  start_at: string | null
  end_at: string | null
  usage_limit: number | null
  usage_limit_per_customer: number | null
  current_usage_count: number
  is_active: boolean
  company: string
  restaurant: string | null
  restaurant_name: string
  branch: string | null
  branch_name: string
  created_by_email: string
  created_at: string
  updated_at: string
  rules: PromotionRule[]
}

export interface PromotionListItem
  extends Pick<Promotion, 'id' | 'name' | 'code' | 'promotion_type' | 'discount_type'
    | 'discount_value' | 'start_at' | 'end_at' | 'usage_limit' | 'usage_limit_per_customer'
    | 'current_usage_count' | 'is_active' | 'restaurant' | 'restaurant_name'
    | 'created_by_email' | 'created_at'> {}

export interface PromotionRule {
  id: string
  promotion: string
  rule_type: string
  configuration: Record<string, unknown>
  priority: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PromotionUsage {
  id: string
  promotion: string
  promotion_name: string
  customer: string | null
  customer_number: string
  order: string | null
  bill: string | null
  discount_amount: string
  used_at: string | null
  status: 'RESERVED' | 'APPLIED' | 'REVERSED' | 'CANCELLED'
  created_at: string
}

export interface PromotionValidateRequest {
  promotion_code?: string
  promotion_id?: string
  customer_id?: string
  order_id?: string
  branch_id?: string
  order_subtotal?: string
}

export interface PromotionValidateResponse {
  eligible: boolean
  promotion_id: string | null
  promotion_name: string
  promotion_type: string
  estimated_discount: string
  discount_type: string | null
  discount_value: string | null
  reason: string
}

export interface CampaignDelivery {
  id: string
  campaign: string
  campaign_code: string
  customer: string
  customer_number: string
  channel: string
  notification_id: string | null
  status: string
  sent_at: string | null
  delivered_at: string | null
  failed_at: string | null
  failure_reason: string
  created_at: string
}

export interface CampaignConversion {
  id: string
  campaign: string
  campaign_code: string
  customer: string
  customer_number: string
  order: string | null
  promotion: string | null
  conversion_type: string
  conversion_value: string
  converted_at: string
}

export interface CampaignAnalytics {
  campaign_id: string
  campaign_code: string
  audience_total: number
  eligible: number
  contacted: number
  converted: number
  deliveries_sent: number
  deliveries_failed: number
  delivery_rate_pct: number
  conversion_rate_pct: number
  conversion_value: string
  discount_given: string
}

export interface MarketingDashboardStats {
  active_campaigns: number
  scheduled_campaigns: number
  draft_campaigns: number
  pending_approvals: number
  completed_campaigns: number
  total_conversions: number
  total_revenue_attributed: string
  total_discount_given: string
  total_promotion_uses: number
}

export interface MarketingSettings {
  id: string
  restaurant: string
  default_currency: string
  max_discount_without_approval: string | null
  default_campaign_timezone: string
  frequency_limit_enabled: boolean
  default_daily_contact_limit: number
  default_weekly_contact_limit: number
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

// ---------------------------------------------------------------------------
// API methods
// ---------------------------------------------------------------------------

const marketingApi = {
  // Dashboard
  getDashboard: (restaurantId?: string) =>
    api.get<MarketingDashboardStats>('/marketing/dashboard/', {
      params: restaurantId ? { restaurant: restaurantId } : {},
    }),

  // Campaigns
  getCampaigns: (params?: Record<string, string>) =>
    api.get<PaginatedResponse<CampaignListItem>>('/marketing/campaigns/', { params }),

  getCampaign: (id: string) =>
    api.get<Campaign>(`/marketing/campaigns/${id}/`),

  createCampaign: (data: Partial<Campaign>) =>
    api.post<Campaign>('/marketing/campaigns/', data),

  updateCampaign: (id: string, data: Partial<Campaign>) =>
    api.patch<Campaign>(`/marketing/campaigns/${id}/`, data),

  submitCampaign: (id: string) =>
    api.post<CampaignApproval>(`/marketing/campaigns/${id}/submit/`),

  approveCampaign: (id: string, note?: string) =>
    api.post<CampaignApproval>(`/marketing/campaigns/${id}/approve/`, { note }),

  rejectCampaign: (id: string, note: string) =>
    api.post<CampaignApproval>(`/marketing/campaigns/${id}/reject/`, { note }),

  scheduleCampaign: (id: string) =>
    api.post<Campaign>(`/marketing/campaigns/${id}/schedule/`),

  pauseCampaign: (id: string) =>
    api.post<Campaign>(`/marketing/campaigns/${id}/pause/`),

  resumeCampaign: (id: string) =>
    api.post<Campaign>(`/marketing/campaigns/${id}/resume/`),

  cancelCampaign: (id: string, reason: string) =>
    api.post<Campaign>(`/marketing/campaigns/${id}/cancel/`, { reason }),

  // Audience
  getCampaignAudience: (campaignId: string) =>
    api.get<CampaignAudience[]>(`/marketing/campaigns/${campaignId}/audience/`),

  createAudience: (campaignId: string, data: { audience_type: string; criteria: Record<string, unknown> }) =>
    api.post<CampaignAudience>(`/marketing/campaigns/${campaignId}/audience/`, data),

  generateAudience: (campaignId: string) =>
    api.post(`/marketing/campaigns/${campaignId}/audience/generate/`),

  getAudienceMembers: (campaignId: string, params?: Record<string, string>) =>
    api.get<PaginatedResponse<CampaignAudienceMember>>(
      `/marketing/campaigns/${campaignId}/audience/members/`, { params }
    ),

  // Analytics
  getCampaignAnalytics: (campaignId: string) =>
    api.get<CampaignAnalytics>(`/marketing/campaigns/${campaignId}/analytics/`),

  getConversions: (params?: Record<string, string>) =>
    api.get<PaginatedResponse<CampaignConversion>>('/marketing/conversions/', { params }),

  // Promotions
  getPromotions: (params?: Record<string, string>) =>
    api.get<PaginatedResponse<PromotionListItem>>('/marketing/promotions/', { params }),

  getPromotion: (id: string) =>
    api.get<Promotion>(`/marketing/promotions/${id}/`),

  createPromotion: (data: Partial<Promotion>) =>
    api.post<Promotion>('/marketing/promotions/', data),

  updatePromotion: (id: string, data: Partial<Promotion>) =>
    api.patch<Promotion>(`/marketing/promotions/${id}/`, data),

  activatePromotion: (id: string) =>
    api.post<Promotion>(`/marketing/promotions/${id}/activate/`),

  deactivatePromotion: (id: string) =>
    api.post<Promotion>(`/marketing/promotions/${id}/deactivate/`),

  getPromotionUsage: (id: string, params?: Record<string, string>) =>
    api.get<PaginatedResponse<PromotionUsage>>(`/marketing/promotions/${id}/usage/`, { params }),

  validatePromotion: (data: PromotionValidateRequest) =>
    api.post<PromotionValidateResponse>('/marketing/promotions/validate/', data),

  // Settings
  getSettings: (restaurantId: string) =>
    api.get<MarketingSettings>('/marketing/settings/', { params: { restaurant: restaurantId } }),

  updateSettings: (restaurantId: string, data: Partial<MarketingSettings>) =>
    api.patch<MarketingSettings>('/marketing/settings/', { ...data, restaurant: restaurantId }),
}

export default marketingApi
