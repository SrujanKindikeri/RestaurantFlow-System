// =============================================================================
// RestaurantFlow — Central Control Center API Service
// Phase 15
// =============================================================================

import { get, post, patch } from '@/services/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CentralDashboard {
  organization_id: string
  organization_name: string
  restaurants: { total: number; active: number; inactive: number }
  branches: { total: number; active: number }
  operations: {
    orders_today: number
    sales_today: string
    open_tables: number
    open_counters: number
  }
  kitchen: { pending_orders: number; delayed_orders: number }
  inventory: { low_stock_items: number; out_of_stock_items: number }
  financial: { pending_expenses: number; overdue_payables: number }
  alerts: { CRITICAL: number; HIGH: number; MEDIUM: number; LOW: number; info: number }
  issues: { open: number; critical: number }
  generated_at: string
}

export interface RestaurantHealth {
  restaurant_id: string
  restaurant_name: string
  is_active: boolean
  branch_count: number
  active_branch_count: number
  orders_today: number
  sales_today: string
  pending_kitchen_orders: number
  delayed_kitchen_orders: number
  low_stock_items: number
  out_of_stock_items: number
  pending_expenses: number
  overdue_payables: number
  unresolved_alerts: number
  unresolved_critical_alerts: number
  open_issues: number
  critical_issues: number
  health_status: 'HEALTHY' | 'WARNING' | 'CRITICAL' | 'OFFLINE' | 'UNKNOWN'
}

export interface SystemHealth {
  overall: string
  api: string
  database: string
  redis: string
  workers: string
  websocket: string
  checked_at: string
}

export interface CentralAlert {
  id: string
  organization: { id: string; name: string }
  restaurant: { id: string; name: string; is_active: boolean } | null
  branch: { id: string; name: string; is_active: boolean } | null
  alert_type: string
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  title: string
  message: string
  source_type: string
  source_id: string
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'DISMISSED' | 'EXPIRED'
  detected_at: string
  expires_at: string | null
  acknowledged_at: string | null
  acknowledged_by: { id: number; email: string; first_name: string; last_name: string } | null
  resolved_at: string | null
  resolved_by: { id: number; email: string; first_name: string; last_name: string } | null
  resolution_note: string
  detection_count: number
  last_detected_at: string | null
  created_at: string
  updated_at: string
}

export interface CentralIssue {
  id: string
  organization: { id: string; name: string }
  restaurant: { id: string; name: string; is_active: boolean } | null
  branch: { id: string; name: string; is_active: boolean } | null
  category: string
  title: string
  description: string
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  status: 'OPEN' | 'ASSIGNED' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED' | 'CANCELLED'
  detected_from_alert_id: string | null
  created_by: { id: number; email: string; first_name: string; last_name: string }
  assigned_to: { id: number; email: string; first_name: string; last_name: string } | null
  resolved_by: { id: number; email: string; first_name: string; last_name: string } | null
  due_at: string | null
  resolved_at: string | null
  closed_at: string | null
  resolution_note: string
  created_at: string
  updated_at: string
}

export interface CentralSystemEvent {
  id: string
  organization: { id: string; name: string }
  restaurant: { id: string; name: string; is_active: boolean } | null
  branch: { id: string; name: string; is_active: boolean } | null
  event_type: string
  severity: string
  title: string
  description: string
  alert_id: string | null
  issue_id: string | null
  metadata: Record<string, unknown>
  occurred_at: string
  created_at: string
}

export interface PaginatedResponse<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface AlertFilters {
  organization_id?: string
  restaurant_id?: string
  branch_id?: string
  severity?: string
  status?: string
  alert_type?: string
  search?: string
  ordering?: string
  page?: number
  page_size?: number
}

export interface IssueFilters {
  organization_id?: string
  restaurant_id?: string
  branch_id?: string
  severity?: string
  status?: string
  category?: string
  assigned_to?: string
  search?: string
  ordering?: string
  page?: number
  page_size?: number
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

export const centralControlApi = {
  // Dashboard
  getDashboard: (organizationId?: string) =>
    get<CentralDashboard>('/central-control/dashboard/', organizationId ? { organization_id: organizationId } : {}),

  // Restaurant health
  getRestaurantHealth: (organizationId?: string) =>
    get<{ results: RestaurantHealth[]; count: number }>('/central-control/restaurants/health/', organizationId ? { organization_id: organizationId } : {}),

  // Restaurants list
  getRestaurants: (params?: Record<string, unknown>) =>
    get<PaginatedResponse<Record<string, unknown>>>('/central-control/restaurants/', params || {}),

  // Branches list
  getBranches: (params?: Record<string, unknown>) =>
    get<PaginatedResponse<Record<string, unknown>>>('/central-control/branches/', params || {}),

  // Alerts
  getAlerts: (filters: AlertFilters = {}) =>
    get<PaginatedResponse<CentralAlert>>('/central-control/alerts/', filters as Record<string, unknown>),

  getAlert: (id: string) =>
    get<CentralAlert>(`/central-control/alerts/${id}/`, {}),

  acknowledgeAlert: (id: string) =>
    post<CentralAlert>(`/central-control/alerts/${id}/acknowledge/`, {}),

  resolveAlert: (id: string, resolutionNote?: string) =>
    post<CentralAlert>(`/central-control/alerts/${id}/resolve/`, { resolution_note: resolutionNote || '' }),

  dismissAlert: (id: string, resolutionNote?: string) =>
    post<CentralAlert>(`/central-control/alerts/${id}/dismiss/`, { resolution_note: resolutionNote || '' }),

  // Issues
  getIssues: (filters: IssueFilters = {}) =>
    get<PaginatedResponse<CentralIssue>>('/central-control/issues/', filters as Record<string, unknown>),

  getIssue: (id: string) =>
    get<CentralIssue>(`/central-control/issues/${id}/`, {}),

  createIssue: (data: Record<string, unknown>) =>
    post<CentralIssue>('/central-control/issues/', data),

  updateIssue: (id: string, data: Record<string, unknown>) =>
    patch<CentralIssue>(`/central-control/issues/${id}/`, data),

  assignIssue: (id: string, assigneeId: number) =>
    post<CentralIssue>(`/central-control/issues/${id}/assign/`, { assignee_id: assigneeId }),

  startIssue: (id: string) =>
    post<CentralIssue>(`/central-control/issues/${id}/start/`, {}),

  resolveIssue: (id: string, resolutionNote: string) =>
    post<CentralIssue>(`/central-control/issues/${id}/resolve/`, { resolution_note: resolutionNote }),

  closeIssue: (id: string) =>
    post<CentralIssue>(`/central-control/issues/${id}/close/`, {}),

  cancelIssue: (id: string, reason?: string) =>
    post<CentralIssue>(`/central-control/issues/${id}/cancel/`, { reason: reason || '' }),

  // Events timeline
  getEvents: (params?: Record<string, unknown>) =>
    get<PaginatedResponse<CentralSystemEvent>>('/central-control/events/', params || {}),

  // System health
  getSystemHealth: () =>
    get<SystemHealth>('/central-control/system-health/', {}),

  // Settings
  getSettings: () =>
    get<Record<string, unknown>>('/central-control/settings/', {}),

  updateSettings: (data: Record<string, unknown>) =>
    patch<Record<string, unknown>>('/central-control/settings/', data),

  // Audit
  getAuditLog: (params?: Record<string, unknown>) =>
    get<PaginatedResponse<Record<string, unknown>>>('/central-control/audit/', params || {}),

  // Users
  getUsers: (params?: Record<string, unknown>) =>
    get<PaginatedResponse<Record<string, unknown>>>('/central-control/users/', params || {}),
}
