// =============================================================================
// RestaurantFlow — Notifications API Service
// Phase 16
// =============================================================================

import api from './api'
import type {
  NotificationRecipient,
  UnreadCountResponse,
  NotificationPreference,
  NotificationPreferenceBulkPayload,
  NotificationDelivery,
  NotificationTemplate,
  NotificationProviderConfig,
  ProviderStatus,
  NotificationListParams,
  NotificationListResponse,
  DeliveryListResponse,
} from '@/types'

const BASE = '/notifications'

// ---------------------------------------------------------------------------
// User-facing
// ---------------------------------------------------------------------------

export async function listNotifications(
  params?: NotificationListParams,
): Promise<NotificationListResponse> {
  const resp = await api.get<NotificationListResponse>(BASE + '/', { params })
  return resp.data
}

export async function getUnreadCount(): Promise<UnreadCountResponse> {
  const resp = await api.get<UnreadCountResponse>(`${BASE}/unread-count/`)
  return resp.data
}

export async function getNotification(id: string): Promise<NotificationRecipient> {
  const resp = await api.get<NotificationRecipient>(`${BASE}/${id}/`)
  return resp.data
}

export async function markNotificationRead(id: string): Promise<NotificationRecipient> {
  const resp = await api.post<NotificationRecipient>(`${BASE}/${id}/read/`)
  return resp.data
}

export async function acknowledgeNotification(id: string): Promise<NotificationRecipient> {
  const resp = await api.post<NotificationRecipient>(`${BASE}/${id}/acknowledge/`)
  return resp.data
}

export async function markAllRead(): Promise<{ updated: number }> {
  const resp = await api.post<{ updated: number }>(`${BASE}/read-all/`)
  return resp.data
}

// ---------------------------------------------------------------------------
// Preferences
// ---------------------------------------------------------------------------

export async function listPreferences(): Promise<NotificationPreference[]> {
  const resp = await api.get<NotificationPreference[]>(`${BASE}/preferences/`)
  return resp.data
}

export async function upsertPreference(
  payload: NotificationPreferenceBulkPayload,
): Promise<NotificationPreference> {
  const resp = await api.post<NotificationPreference>(`${BASE}/preferences/`, payload)
  return resp.data
}

export async function updatePreference(
  id: string,
  enabled: boolean,
): Promise<NotificationPreference> {
  const resp = await api.patch<NotificationPreference>(`${BASE}/preferences/${id}/`, { enabled })
  return resp.data
}

// ---------------------------------------------------------------------------
// Delivery history (user's own)
// ---------------------------------------------------------------------------

export async function listMyDeliveries(): Promise<NotificationDelivery[]> {
  const resp = await api.get<NotificationDelivery[]>(`${BASE}/deliveries/`)
  return resp.data
}

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------

export async function listAdminDeliveries(
  params?: Record<string, string>,
): Promise<DeliveryListResponse> {
  const resp = await api.get<DeliveryListResponse>(`${BASE}/admin/deliveries/`, { params })
  return resp.data
}

export async function listTemplates(): Promise<NotificationTemplate[]> {
  const resp = await api.get<NotificationTemplate[]>(`${BASE}/admin/templates/`)
  return resp.data
}

export async function createTemplate(
  data: Partial<NotificationTemplate>,
): Promise<NotificationTemplate> {
  const resp = await api.post<NotificationTemplate>(`${BASE}/admin/templates/`, data)
  return resp.data
}

export async function updateTemplate(
  id: string,
  data: Partial<NotificationTemplate>,
): Promise<NotificationTemplate> {
  const resp = await api.patch<NotificationTemplate>(`${BASE}/admin/templates/${id}/`, data)
  return resp.data
}

export async function listProviderConfigs(): Promise<NotificationProviderConfig[]> {
  const resp = await api.get<NotificationProviderConfig[]>(`${BASE}/admin/providers/`)
  return resp.data
}

export async function updateProviderConfig(
  id: string,
  data: Partial<NotificationProviderConfig>,
): Promise<NotificationProviderConfig> {
  const resp = await api.patch<NotificationProviderConfig>(
    `${BASE}/admin/providers/${id}/`,
    data,
  )
  return resp.data
}

export async function getProviderStatus(): Promise<ProviderStatus[]> {
  const resp = await api.get<ProviderStatus[]>(`${BASE}/admin/providers/status/`)
  return resp.data
}
