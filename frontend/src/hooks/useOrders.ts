// =============================================================================
// RestaurantFlow — Orders + Tables Hooks
// Phase 6
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
import {
  listTables,
  getTable,
  createTable,
  updateTable,
  disableTable,
  enableTable,
  listTableSessions,
  getTableSession,
  openTableSession,
  closeTableSession,
  listOrders,
  getOrder,
  createOrder,
  updateOrder,
  confirmOrder,
  cancelOrder,
  assignWaiter,
  addOrderItem,
  updateOrderItem,
  removeOrderItem,
} from '@/services/orders'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const tableKeys = {
  all: ['dining-tables'] as const,
  lists: () => [...tableKeys.all, 'list'] as const,
  list: (params?: Record<string, unknown>) =>
    [...tableKeys.lists(), params] as const,
  details: () => [...tableKeys.all, 'detail'] as const,
  detail: (id: string) => [...tableKeys.details(), id] as const,
}

export const tableSessionKeys = {
  all: ['table-sessions'] as const,
  lists: () => [...tableSessionKeys.all, 'list'] as const,
  list: (params?: Record<string, unknown>) =>
    [...tableSessionKeys.lists(), params] as const,
  detail: (id: string) => [...tableSessionKeys.all, 'detail', id] as const,
}

export const orderKeys = {
  all: ['orders'] as const,
  lists: () => [...orderKeys.all, 'list'] as const,
  list: (params?: Record<string, unknown>) =>
    [...orderKeys.lists(), params] as const,
  details: () => [...orderKeys.all, 'detail'] as const,
  detail: (id: string) => [...orderKeys.details(), id] as const,
}

// ---------------------------------------------------------------------------
// Table hooks
// ---------------------------------------------------------------------------

export function useTables(params?: Record<string, string | number | boolean>) {
  return useQuery<PaginatedResponse<DiningTable>, Error>({
    queryKey: tableKeys.list(params),
    queryFn: () => listTables(params),
  })
}

export function useTable(id: string) {
  return useQuery<DiningTable, Error>({
    queryKey: tableKeys.detail(id),
    queryFn: () => getTable(id),
    enabled: !!id,
  })
}

export function useCreateTable() {
  const qc = useQueryClient()
  return useMutation<DiningTable, Error, DiningTableCreatePayload>({
    mutationFn: createTable,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tableKeys.lists() })
    },
  })
}

export function useUpdateTable(id: string) {
  const qc = useQueryClient()
  return useMutation<DiningTable, Error, DiningTableUpdatePayload>({
    mutationFn: (data) => updateTable(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tableKeys.detail(id) })
      qc.invalidateQueries({ queryKey: tableKeys.lists() })
    },
  })
}

export function useDisableTable() {
  const qc = useQueryClient()
  return useMutation<DiningTable, Error, string>({
    mutationFn: disableTable,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tableKeys.lists() })
      qc.invalidateQueries({ queryKey: tableKeys.all })
    },
  })
}

export function useEnableTable() {
  const qc = useQueryClient()
  return useMutation<DiningTable, Error, string>({
    mutationFn: enableTable,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tableKeys.lists() })
      qc.invalidateQueries({ queryKey: tableKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// Table session hooks
// ---------------------------------------------------------------------------

export function useTableSessions(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<TableSession>, Error>({
    queryKey: tableSessionKeys.list(params),
    queryFn: () => listTableSessions(params),
  })
}

export function useTableSession(id: string) {
  return useQuery<TableSession, Error>({
    queryKey: tableSessionKeys.detail(id),
    queryFn: () => getTableSession(id),
    enabled: !!id,
  })
}

export function useOpenTableSession(tableId: string) {
  const qc = useQueryClient()
  return useMutation<TableSession, Error, OpenTableSessionPayload>({
    mutationFn: (data) => openTableSession(tableId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: tableKeys.detail(tableId) })
      qc.invalidateQueries({ queryKey: tableKeys.lists() })
      qc.invalidateQueries({ queryKey: tableSessionKeys.lists() })
    },
  })
}

export function useCloseTableSession(sessionId: string) {
  const qc = useQueryClient()
  return useMutation<TableSession, Error, void>({
    mutationFn: () => closeTableSession(sessionId),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: tableSessionKeys.detail(sessionId) })
      qc.invalidateQueries({ queryKey: tableSessionKeys.lists() })
      qc.invalidateQueries({ queryKey: tableKeys.detail(data.table) })
      qc.invalidateQueries({ queryKey: tableKeys.lists() })
    },
  })
}

// ---------------------------------------------------------------------------
// Order hooks
// ---------------------------------------------------------------------------

export function useOrders(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<Order>, Error>({
    queryKey: orderKeys.list(params),
    queryFn: () => listOrders(params),
  })
}

export function useOrder(id: string) {
  return useQuery<OrderDetail, Error>({
    queryKey: orderKeys.detail(id),
    queryFn: () => getOrder(id),
    enabled: !!id,
  })
}

export function useCreateOrder() {
  const qc = useQueryClient()
  return useMutation<Order, Error, CreateOrderPayload>({
    mutationFn: createOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orderKeys.lists() })
      qc.invalidateQueries({ queryKey: tableKeys.lists() })
    },
  })
}

export function useUpdateOrder(id: string) {
  const qc = useQueryClient()
  return useMutation<Order, Error, { notes?: string }>({
    mutationFn: (data) => updateOrder(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orderKeys.detail(id) })
    },
  })
}

export function useConfirmOrder() {
  const qc = useQueryClient()
  return useMutation<OrderDetail, Error, string>({
    mutationFn: (id) => confirmOrder(id),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: orderKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: orderKeys.lists() })
    },
  })
}

export function useCancelOrder() {
  const qc = useQueryClient()
  return useMutation<OrderDetail, Error, { id: string; data: CancelOrderPayload }>({
    mutationFn: ({ id, data }) => cancelOrder(id, data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: orderKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: orderKeys.lists() })
      qc.invalidateQueries({ queryKey: tableKeys.lists() })
    },
  })
}

export function useAssignWaiter(orderId: string) {
  const qc = useQueryClient()
  return useMutation<Order, Error, AssignWaiterPayload>({
    mutationFn: (data) => assignWaiter(orderId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orderKeys.detail(orderId) })
      qc.invalidateQueries({ queryKey: orderKeys.lists() })
    },
  })
}

// ---------------------------------------------------------------------------
// Order item hooks
// ---------------------------------------------------------------------------

export function useAddOrderItem(orderId: string) {
  const qc = useQueryClient()
  return useMutation<OrderItem, Error, AddOrderItemPayload>({
    mutationFn: (data) => addOrderItem(orderId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orderKeys.detail(orderId) })
    },
  })
}

export function useUpdateOrderItem(itemId: string, orderId: string) {
  const qc = useQueryClient()
  return useMutation<OrderItem, Error, UpdateOrderItemPayload>({
    mutationFn: (data) => updateOrderItem(itemId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orderKeys.detail(orderId) })
    },
  })
}

export function useRemoveOrderItem(itemId: string, orderId: string) {
  const qc = useQueryClient()
  return useMutation<void, Error, void>({
    mutationFn: () => removeOrderItem(itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: orderKeys.detail(orderId) })
    },
  })
}
