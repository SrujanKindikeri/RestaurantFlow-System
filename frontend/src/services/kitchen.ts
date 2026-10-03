// =============================================================================
// RestaurantFlow — Kitchen API Service
// Phase 7
// =============================================================================

import { get, post } from '@/services/api'
import type {
  KitchenOrder,
  KitchenOrderItem,
  KitchenOrdersParams,
  KitchenHistoryParams,
  PaginatedResponse,
} from '@/types'

// ---------------------------------------------------------------------------
// Kitchen Orders — live KDS
// ---------------------------------------------------------------------------

/** GET /api/kitchen/orders/ */
export const listKitchenOrders = (params?: KitchenOrdersParams) =>
  get<PaginatedResponse<KitchenOrder>>('/kitchen/orders/', { params })

/** GET /api/kitchen/orders/:id/ */
export const getKitchenOrder = (id: string) =>
  get<KitchenOrder>(`/kitchen/orders/${id}/`)

/** POST /api/kitchen/orders/:id/accept/ */
export const acceptKitchenOrder = (id: string) =>
  post<KitchenOrder>(`/kitchen/orders/${id}/accept/`)

/** POST /api/kitchen/orders/:id/start/ */
export const startKitchenOrder = (id: string) =>
  post<KitchenOrder>(`/kitchen/orders/${id}/start/`)

/** POST /api/kitchen/orders/:id/ready/ */
export const readyKitchenOrder = (id: string) =>
  post<KitchenOrder>(`/kitchen/orders/${id}/ready/`)

/** POST /api/kitchen/orders/:id/cancel/ */
export const cancelKitchenOrder = (id: string, reason?: string) =>
  post<KitchenOrder>(`/kitchen/orders/${id}/cancel/`, { reason: reason ?? '' })

/** POST /api/kitchen/orders/:id/priority/ */
export const updateKitchenPriority = (id: string, priority: string) =>
  post<KitchenOrder>(`/kitchen/orders/${id}/priority/`, { priority })

// ---------------------------------------------------------------------------
// Kitchen History
// ---------------------------------------------------------------------------

/** GET /api/kitchen/history/ */
export const listKitchenHistory = (params?: KitchenHistoryParams) =>
  get<PaginatedResponse<KitchenOrder>>('/kitchen/history/', { params })

// ---------------------------------------------------------------------------
// Kitchen Items
// ---------------------------------------------------------------------------

/** GET /api/kitchen/items/:id/ */
export const getKitchenItem = (id: string) =>
  get<KitchenOrderItem>(`/kitchen/items/${id}/`)

/** POST /api/kitchen/items/:id/start/ */
export const startKitchenItem = (id: string) =>
  post<KitchenOrderItem>(`/kitchen/items/${id}/start/`)

/** POST /api/kitchen/items/:id/ready/ */
export const readyKitchenItem = (id: string) =>
  post<KitchenOrderItem>(`/kitchen/items/${id}/ready/`)
