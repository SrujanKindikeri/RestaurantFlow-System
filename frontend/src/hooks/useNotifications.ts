// =============================================================================
// RestaurantFlow — Notifications Hooks
// Phase 16
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  NotificationRecipient,
  UnreadCountResponse,
  NotificationPreference,
  NotificationPreferenceBulkPayload,
  NotificationListParams,
  NotificationListResponse,
} from '@/types'
import {
  listNotifications,
  getUnreadCount,
  getNotification,
  markNotificationRead,
  acknowledgeNotification,
  markAllRead,
  listPreferences,
  upsertPreference,
  updatePreference,
} from '@/services/notifications'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const notificationKeys = {
  all:          ['notifications'] as const,
  lists:        (params?: NotificationListParams) => ['notifications', 'list', params] as const,
  detail:       (id: string) => ['notifications', 'detail', id] as const,
  unreadCount:  () => ['notifications', 'unread-count'] as const,
  preferences:  () => ['notifications', 'preferences'] as const,
}

// ---------------------------------------------------------------------------
// Hooks — listing + unread count
// ---------------------------------------------------------------------------

export function useNotifications(params?: NotificationListParams) {
  return useQuery<NotificationListResponse, Error>({
    queryKey: notificationKeys.lists(params),
    queryFn:  () => listNotifications(params),
    staleTime: 15_000,
    refetchInterval: 30_000,  // Poll every 30s as WS fallback
  })
}

export function useUnreadCount() {
  return useQuery<UnreadCountResponse, Error>({
    queryKey:        notificationKeys.unreadCount(),
    queryFn:         getUnreadCount,
    staleTime:       10_000,
    refetchInterval: 20_000,
  })
}

export function useNotificationDetail(id: string) {
  return useQuery<NotificationRecipient, Error>({
    queryKey: notificationKeys.detail(id),
    queryFn:  () => getNotification(id),
    enabled:  !!id,
  })
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useMarkRead() {
  const qc = useQueryClient()
  return useMutation<NotificationRecipient, Error, string>({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount() })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
    },
  })
}

export function useAcknowledge() {
  const qc = useQueryClient()
  return useMutation<NotificationRecipient, Error, string>({
    mutationFn: acknowledgeNotification,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount() })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
    },
  })
}

export function useMarkAllRead() {
  const qc = useQueryClient()
  return useMutation<{ updated: number }, Error, void>({
    mutationFn: markAllRead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount() })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
    },
  })
}

// ---------------------------------------------------------------------------
// Preferences
// ---------------------------------------------------------------------------

export function useNotificationPreferences() {
  return useQuery<NotificationPreference[], Error>({
    queryKey: notificationKeys.preferences(),
    queryFn:  listPreferences,
    staleTime: 60_000,
  })
}

export function useUpsertPreference() {
  const qc = useQueryClient()
  return useMutation<NotificationPreference, Error, NotificationPreferenceBulkPayload>({
    mutationFn: upsertPreference,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.preferences() })
    },
  })
}

export function useUpdatePreference() {
  const qc = useQueryClient()
  return useMutation<NotificationPreference, Error, { id: string; enabled: boolean }>({
    mutationFn: ({ id, enabled }) => updatePreference(id, enabled),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.preferences() })
    },
  })
}
