// =============================================================================
// RestaurantFlow — Orders API Service
// Phase 6
// =============================================================================

import { get, post, patch, del } from '@/services/api'
import type {
  DiningTable,
  DiningTableCreatePayload,
  DiningTableUpdatePayload,
  TableSession,
  OpenTableSessionPayload,
  Order,
  OrderDetail,
  CreateOrderPayload,
  OrderItem,
  AddOrderItemPayload,
  UpdateOrderItemPayload,
  CancelOrderPayload,
  AssignWaiterPayload,
  PaginatedResponse,
} from '@/types'

// ---------------------------------------------------------------------------
// Dining Tables
// ---------------------------------------------------------------------------

/** GET /api/tables/ */
export const listTables = (params?: Record<string, string | number | boolean>) =>
  get<PaginatedResponse<DiningTable>>('/tables/', { params })

/** GET /api/tables/:id/ */
export const getTable = (id: string) =>
  get<DiningTable>(`/tables/${id}/`)

/** POST /api/tables/ */
export const createTable = (data: DiningTableCreatePayload) =>
  post<DiningTable>('/tables/', data)

/** PATCH /api/tables/:id/ */
export const updateTable = (id: string, data: DiningTableUpdatePayload) =>
  patch<DiningTable>(`/tables/${id}/`, data)

/** POST /api/tables/:id/disable/ */
export const disableTable = (id: string) =>
  post<DiningTable>(`/tables/${id}/disable/`)

/** POST /api/tables/:id/enable/ */
export const enableTable = (id: string) =>
  post<DiningTable>(`/tables/${id}/enable/`)

// ---------------------------------------------------------------------------
// Table Sessions
// ---------------------------------------------------------------------------

/** GET /api/table-sessions/ */
export const listTableSessions = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<TableSession>>('/table-sessions/', { params })

/** GET /api/table-sessions/:id/ */
export const getTableSession = (id: string) =>
  get<TableSession>(`/table-sessions/${id}/`)

/** POST /api/tables/:id/sessions/open/ */
export const openTableSession = (tableId: string, data: OpenTableSessionPayload) =>
  post<TableSession>(`/tables/${tableId}/sessions/open/`, data)

/** POST /api/table-sessions/:id/close/ */
export const closeTableSession = (sessionId: string) =>
  post<TableSession>(`/table-sessions/${sessionId}/close/`)

// ---------------------------------------------------------------------------
// Orders
// ---------------------------------------------------------------------------

/** GET /api/orders/ */
export const listOrders = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<Order>>('/orders/', { params })

/** GET /api/orders/:id/ */
export const getOrder = (id: string) =>
  get<OrderDetail>(`/orders/${id}/`)

/** POST /api/orders/ */
export const createOrder = (data: CreateOrderPayload) =>
  post<Order>('/orders/', data)

/** PATCH /api/orders/:id/ — update notes on draft */
export const updateOrder = (id: string, data: { notes?: string }) =>
  patch<Order>(`/orders/${id}/`, data)

/** POST /api/orders/:id/confirm/ */
export const confirmOrder = (id: string) =>
  post<OrderDetail>(`/orders/${id}/confirm/`)

/** POST /api/orders/:id/cancel/ */
export const cancelOrder = (id: string, data: CancelOrderPayload) =>
  post<OrderDetail>(`/orders/${id}/cancel/`, data)

/** POST /api/orders/:id/assign-waiter/ */
export const assignWaiter = (id: string, data: AssignWaiterPayload) =>
  post<Order>(`/orders/${id}/assign-waiter/`, data)

// ---------------------------------------------------------------------------
// Order Items
// ---------------------------------------------------------------------------

/** POST /api/orders/:id/items/ */
export const addOrderItem = (orderId: string, data: AddOrderItemPayload) =>
  post<OrderItem>(`/orders/${orderId}/items/`, data)

/** PATCH /api/order-items/:id/ */
export const updateOrderItem = (itemId: string, data: UpdateOrderItemPayload) =>
  patch<OrderItem>(`/order-items/${itemId}/`, data)

/** DELETE /api/order-items/:id/ */
export const removeOrderItem = (itemId: string) =>
  del<void>(`/order-items/${itemId}/`)
