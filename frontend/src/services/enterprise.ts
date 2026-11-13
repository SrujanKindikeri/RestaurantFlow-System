// =============================================================================
// RestaurantFlow — Enterprise API Service
// Phase 20: Multi-Branch Enterprise Operations & Configuration
// =============================================================================

import { get, post, patch } from '@/services/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface EnterpriseDashboard {
  total_restaurants: number
  total_branches: number
  active_branches: number
  temporarily_closed: number
  scheduled_closures: number
  pending_transfers: number
  pending_rollouts: number
  pending_closures: number
  failed_rollouts_24h: number
}

export interface BranchStatus {
  id: string
  branch: { id: string; name: string; code: string }
  status: string
  status_changed_at: string | null
  status_changed_by: { id: number; email: string; full_name: string } | null
  status_reason: string
  created_at: string
  updated_at: string
}

export interface BranchDetail {
  branch_id: string
  branch_name: string
  branch_code: string
  operational_status: string
  status_changed_at: string | null
  status_reason: string
  active_staff_count: number
  active_counter_count: number | null
  operating_hours: OperatingHour[]
  active_closures: BranchClosure[]
}

export interface ChecklistItem {
  type: string
  label: string
  status: 'READY' | 'WARNING' | 'BLOCKED'
  detail: string
}

export interface OperatingHour {
  id?: string
  branch?: { id: string; name: string; code: string }
  day_of_week: string
  opening_time: string | null
  closing_time: string | null
  is_closed: boolean
  is_overnight?: boolean
}

export interface BranchClosure {
  id: string
  branch?: { id: string; name: string; code: string }
  closure_type: string
  start_datetime: string
  end_datetime: string
  reason: string
  status: string
  created_by?: { id: number; email: string; full_name: string }
  approved_by?: { id: number; email: string; full_name: string } | null
  approved_at: string | null
  rejected_at: string | null
  rejection_reason: string
}

export interface EnterpriseConfig {
  id: string
  company: string
  restaurant: string | null
  branch: string | null
  configuration_key: string
  configuration_value: string
  value_type: string
  scope: string
  is_active: boolean
  version: number
  created_by: { id: number; email: string; full_name: string } | null
  updated_by: { id: number; email: string; full_name: string } | null
  created_at: string
  updated_at: string
}

export interface EffectiveConfig {
  key: string
  value: unknown
  raw_value: string
  source: string
  is_overridden: boolean
  description: string
  value_type: string
}

export interface ConfigChange {
  id: string
  configuration_key: string
  old_value: string
  new_value: string
  version: number
  changed_by: { id: number; email: string; full_name: string } | null
  change_reason: string
  scope: string
  created_at: string
}

export interface MenuRollout {
  id: string
  restaurant: { id: string; name: string; code: string }
  menu_item: { id: string; name: string; sku: string }
  rollout_type: string
  new_price: string | null
  is_available: boolean | null
  force_override: boolean
  source_branch: { id: string; name: string; code: string } | null
  target_scope: string
  effective_from: string | null
  status: string
  created_by: { id: number; email: string; full_name: string }
  approved_by: { id: number; email: string; full_name: string } | null
  approved_at: string | null
  completed_at: string | null
  notes: string
  branch_results: MenuRolloutBranchResult[]
  created_at: string
  updated_at: string
}

export interface MenuRolloutBranchResult {
  id: string
  branch: { id: string; name: string; code: string }
  result: string
  old_value: string
  new_value: string
  failure_reason: string
}

export interface RolloutPreview {
  rollout_id: string
  rollout_type: string
  menu_item: { id: string; name: string; sku: string }
  target_scope: string
  force_override: boolean
  total_branches: number
  will_change_count: number
  will_skip_count: number
  branches: RolloutPreviewBranch[]
}

export interface RolloutPreviewBranch {
  branch_id: string
  branch_name: string
  branch_code: string
  current_value: string | null
  new_value: string | null
  will_change: boolean
  skip_reason: string | null
}

export interface StaffAssignment {
  id: string
  user: { id: number; email: string; full_name: string }
  restaurant: { id: string; name: string; code: string }
  branch: { id: string; name: string; code: string }
  role_code: string
  role_name: string
  assigned_by: { id: number; email: string; full_name: string }
  assigned_at: string
  start_date: string | null
  end_date: string | null
  is_primary: boolean
  is_active: boolean
}

export interface StaffTransfer {
  id: string
  user: { id: number; email: string; full_name: string }
  restaurant: { id: string; name: string; code: string }
  source_branch: { id: string; name: string; code: string }
  destination_branch: { id: string; name: string; code: string }
  requested_by: { id: number; email: string; full_name: string }
  approved_by: { id: number; email: string; full_name: string } | null
  reason: string
  status: string
  requested_at: string
  approved_at: string | null
  completed_at: string | null
  rejected_at: string | null
  rejection_reason: string
}

export interface ApprovalPolicy {
  id: string
  company: string
  restaurant: { id: string; name: string; code: string } | null
  branch: { id: string; name: string; code: string } | null
  policy_type: string
  threshold_amount: string | null
  threshold_percentage: string | null
  required_permission: string
  required_role_code: string | null
  is_active: boolean
  created_by: { id: number; email: string; full_name: string } | null
  updated_at: string
}

export interface EnterpriseAuditLog {
  id: string
  performed_by: { id: number; email: string; full_name: string } | null
  company: string
  restaurant: { id: string; name: string; code: string } | null
  branch: { id: string; name: string; code: string } | null
  action: string
  description: string
  source_type: string
  source_id: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface BulkOperationResult {
  successful: { key: string; config_id?: string; branch_id?: string; branch_name?: string }[]
  failed: { key?: string; branch_id?: string; branch_name?: string; error: string }[]
  skipped: { branch_id?: string; branch_name?: string; reason?: string }[]
  warnings: string[]
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

// Dashboard
export const enterpriseApi = {
  getDashboard: (): Promise<EnterpriseDashboard> =>
    get('/enterprise/dashboard/'),

  // Branch lifecycle
  getBranches: (params?: { status?: string; restaurant_id?: string }) =>
    get('/enterprise/branches/', { params }),

  getBranchDetail: (branchId: string): Promise<BranchDetail> =>
    get(`/enterprise/branches/${branchId}/`),

  setBranchStatus: (branchId: string, payload: { new_status: string; reason?: string }) =>
    patch(`/enterprise/branches/${branchId}/status/`, payload),

  openBranch: (branchId: string, reason?: string) =>
    post(`/enterprise/branches/${branchId}/open/`, { reason }),

  closeBranch: (branchId: string, reason: string, force?: boolean) =>
    post(`/enterprise/branches/${branchId}/close/`, { reason, force }),

  reopenBranch: (branchId: string, reason?: string) =>
    post(`/enterprise/branches/${branchId}/reopen/`, { reason }),

  getOpeningChecklist: (branchId: string): Promise<{ branch_id: string; checklist: ChecklistItem[] }> =>
    get(`/enterprise/branches/${branchId}/opening-checklist/`),

  // Operating hours
  getSchedules: (branchId: string): Promise<OperatingHour[]> =>
    get('/enterprise/schedules/', { params: { branch_id: branchId } }),

  upsertSchedule: (branchId: string, payload: Omit<OperatingHour, 'id' | 'branch' | 'is_overnight'>) =>
    post('/enterprise/schedules/', { ...payload, branch_id: branchId }),

  bulkUpsertSchedules: (branchId: string, hours: Omit<OperatingHour, 'id' | 'branch' | 'is_overnight'>[]) =>
    put('/enterprise/schedules/bulk/', { hours, branch_id: branchId }),

  // Closures
  getClosures: (branchId: string): Promise<BranchClosure[]> =>
    get('/enterprise/closures/', { params: { branch_id: branchId } }),

  createClosure: (payload: {
    branch_id: string
    closure_type: string
    start_datetime: string
    end_datetime: string
    reason: string
    auto_approve?: boolean
  }): Promise<BranchClosure> =>
    post('/enterprise/closures/', payload),

  approveClosure: (closureId: string) =>
    post(`/enterprise/closures/${closureId}/approve/`, {}),

  rejectClosure: (closureId: string, rejection_reason?: string) =>
    post(`/enterprise/closures/${closureId}/reject/`, { rejection_reason }),

  cancelClosure: (closureId: string) =>
    post(`/enterprise/closures/${closureId}/cancel/`, {}),

  // Configuration
  getConfigurations: (params: {
    company_id?: string
    restaurant_id?: string
    branch_id?: string
  }): Promise<EnterpriseConfig[]> =>
    get('/enterprise/configuration/', { params }),

  getEffectiveConfiguration: (params: {
    branch_id?: string
    restaurant_id?: string
    company_id?: string
  }): Promise<EffectiveConfig[]> =>
    get('/enterprise/configuration/effective/', { params }),

  setConfiguration: (payload: {
    configuration_key: string
    configuration_value: string
    reason?: string
    branch_id?: string
    restaurant_id?: string
    company_id?: string
  }): Promise<EnterpriseConfig> =>
    post('/enterprise/configuration/', payload),

  updateConfiguration: (configId: string, payload: {
    configuration_value: string
    reason?: string
  }): Promise<EnterpriseConfig> =>
    patch(`/enterprise/configuration/${configId}/`, payload),

  bulkSetConfiguration: (payload: {
    configs: { key: string; value: string }[]
    reason?: string
    branch_id?: string
    restaurant_id?: string
    company_id?: string
  }): Promise<BulkOperationResult> =>
    post('/enterprise/configuration/bulk/', payload),

  rollbackConfiguration: (configId: string, reason?: string) =>
    post(`/enterprise/configuration/${configId}/rollback/`, { reason }),

  getConfigurationHistory: (params?: {
    key?: string
    company_id?: string
  }): Promise<ConfigChange[]> =>
    get('/enterprise/configuration/history/', { params }),

  // Rollouts
  getRollouts: (restaurantId: string, params?: { status?: string; rollout_type?: string }): Promise<MenuRollout[]> =>
    get('/enterprise/rollouts/', { params: { restaurant_id: restaurantId, ...params } }),

  getRollout: (rolloutId: string): Promise<MenuRollout> =>
    get(`/enterprise/rollouts/${rolloutId}/`),

  createRollout: (payload: {
    restaurant_id: string
    menu_item_id: string
    rollout_type: string
    target_scope: string
    target_branch_ids?: string[]
    is_available?: boolean
    new_price?: string
    force_override?: boolean
    effective_from?: string
    notes?: string
  }): Promise<MenuRollout> =>
    post('/enterprise/rollouts/', payload),

  previewRollout: (rolloutId: string): Promise<RolloutPreview> =>
    post(`/enterprise/rollouts/${rolloutId}/preview/`, {}),

  approveRollout: (rolloutId: string) =>
    post(`/enterprise/rollouts/${rolloutId}/approve/`, {}),

  executeRollout: (rolloutId: string): Promise<BulkOperationResult> =>
    post(`/enterprise/rollouts/${rolloutId}/execute/`, {}),

  cancelRollout: (rolloutId: string, reason?: string) =>
    post(`/enterprise/rollouts/${rolloutId}/cancel/`, { reason }),

  // Staff
  getStaff: (restaurantId: string): Promise<StaffAssignment[]> =>
    get('/enterprise/staff/', { params: { restaurant_id: restaurantId } }),

  getAssignments: (branchId: string): Promise<StaffAssignment[]> =>
    get('/enterprise/staff/assignments/', { params: { branch_id: branchId } }),

  assignStaff: (payload: {
    branch_id: string
    user_id: number
    role_id: string
    is_primary?: boolean
    start_date?: string
    end_date?: string
  }): Promise<StaffAssignment> =>
    post('/enterprise/staff/assign/', payload),

  getTransfers: (restaurantId: string, params?: { status?: string }): Promise<StaffTransfer[]> =>
    get('/enterprise/staff/transfers/', { params: { restaurant_id: restaurantId, ...params } }),

  getTransfer: (transferId: string): Promise<StaffTransfer> =>
    get(`/enterprise/staff/transfers/${transferId}/`),

  requestTransfer: (payload: {
    user_id: number
    source_branch_id: string
    destination_branch_id: string
    reason: string
  }): Promise<StaffTransfer> =>
    post('/enterprise/staff/transfers/', payload),

  approveTransfer: (transferId: string) =>
    post(`/enterprise/staff/transfers/${transferId}/approve/`, {}),

  rejectTransfer: (transferId: string, rejection_reason?: string) =>
    post(`/enterprise/staff/transfers/${transferId}/reject/`, { rejection_reason }),

  completeTransfer: (transferId: string) =>
    post(`/enterprise/staff/transfers/${transferId}/complete/`, {}),

  cancelTransfer: (transferId: string) =>
    post(`/enterprise/staff/transfers/${transferId}/cancel/`, {}),

  // Approval Policies
  getApprovalPolicies: (params?: { policy_type?: string; company_id?: string }): Promise<ApprovalPolicy[]> =>
    get('/enterprise/approval-policies/', { params }),

  createApprovalPolicy: (payload: {
    policy_type: string
    required_permission: string
    threshold_amount?: string
    threshold_percentage?: string
    required_role_id?: string
    branch_id?: string
    restaurant_id?: string
    company_id?: string
  }): Promise<ApprovalPolicy> =>
    post('/enterprise/approval-policies/', payload),

  updateApprovalPolicy: (policyId: string, payload: Partial<{
    threshold_amount: string
    threshold_percentage: string
    required_permission: string
    is_active: boolean
  }>) =>
    patch(`/enterprise/approval-policies/${policyId}/`, payload),

  // Audit
  getAuditLogs: (params?: {
    branch_id?: string
    restaurant_id?: string
    action?: string
  }): Promise<EnterpriseAuditLog[]> =>
    get('/enterprise/audit/', { params }),
}

// PUT helper (reuse api pattern)
function put(url: string, data?: unknown) {
  return post(url, data)
}
