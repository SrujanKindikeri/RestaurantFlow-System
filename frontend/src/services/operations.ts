// =============================================================================
// RestaurantFlow — Operations API Service
// Phase 19: Advanced POS & Restaurant Operations
// =============================================================================

import { get, post, patch, del } from '@/services/api'

// ---------------------------------------------------------------------------
// POS Session
// ---------------------------------------------------------------------------

export const getPOSSessions = () =>
  get<any>('/operations/pos/session/')

export const startPOSSession = (data: { counter_id: string; device_identifier?: string }) =>
  post<any>('/operations/pos/session/start/', data)

export const pausePOSSession = (sessionId: string) =>
  post<any>(`/operations/pos/session/${sessionId}/pause/`)

export const resumePOSSession = (sessionId: string) =>
  post<any>(`/operations/pos/session/${sessionId}/resume/`)

export const endPOSSession = (sessionId: string) =>
  post<any>(`/operations/pos/session/${sessionId}/end/`)

export const getPOSRecovery = (counterId: string) =>
  get<any>('/operations/pos/recovery/', { params: { counter_id: counterId } })

// ---------------------------------------------------------------------------
// Barcode / SKU Scan
// ---------------------------------------------------------------------------

export const scanBarcode = (barcodeOrSku: string) =>
  post<any>('/operations/pos/scan/', { barcode_or_sku: barcodeOrSku })

// ---------------------------------------------------------------------------
// Order Operations
// ---------------------------------------------------------------------------

export const holdOrder = (orderId: string) =>
  post<any>(`/operations/orders/${orderId}/hold/`)

export const resumeOrder = (orderId: string) =>
  post<any>(`/operations/orders/${orderId}/resume/`)

export const setOrderPriority = (orderId: string, priority: 'NORMAL' | 'HIGH' | 'URGENT') =>
  post<any>(`/operations/orders/${orderId}/priority/`, { priority })

export const assignWaiter = (orderId: string, waiterId: number) =>
  post<any>(`/operations/orders/${orderId}/waiter/`, { waiter_id: waiterId })

export const getOrderChangeRequests = (orderId: string) =>
  get<any>(`/operations/orders/${orderId}/change-request/`)

export const createOrderChangeRequest = (orderId: string, data: {
  change_type: string; reason: string; requested_data?: Record<string, any>
}) => post<any>(`/operations/orders/${orderId}/change-request/`, data)

export const approveChangeRequest = (changeRequestId: string, reviewNote?: string) =>
  post<any>(`/operations/change-requests/${changeRequestId}/approve/`, { review_note: reviewNote })

export const rejectChangeRequest = (changeRequestId: string, reviewNote?: string) =>
  post<any>(`/operations/change-requests/${changeRequestId}/reject/`, { review_note: reviewNote })

export const mergeOrders = (data: {
  source_order_ids: string[]; destination_order_id: string; reason?: string
}) => post<any>('/operations/orders/merge/', data)

// ---------------------------------------------------------------------------
// Modifiers
// ---------------------------------------------------------------------------

export const getMenuItemModifiers = (menuItemId: string) =>
  get<any>(`/operations/menu-items/${menuItemId}/modifiers/`)

export const addOrderItemModifier = (orderItemId: string, data: {
  modifier_option_id?: string; name: string; value: string
}) => post<any>(`/operations/order-items/${orderItemId}/modifiers/`, data)

export const removeOrderItemModifier = (modifierId: string) =>
  del<any>(`/operations/order-item-modifiers/${modifierId}/`)

// ---------------------------------------------------------------------------
// Tables
// ---------------------------------------------------------------------------

export const getOperationalTables = (branchId?: string) =>
  get<any[]>('/operations/tables/', { params: branchId ? { branch_id: branchId } : undefined })

export const setTableStatus = (tableId: string, status: string, notes?: string) =>
  patch<any>(`/operations/tables/${tableId}/status/`, { status, notes })

export const requestTableTransfer = (tableId: string, destinationTableId: string, reason?: string) =>
  post<any>(`/operations/tables/${tableId}/transfer/`, { destination_table_id: destinationTableId, reason })

export const mergeTable = (data: {
  source_table_ids: string[]; destination_table_id: string; reason?: string
}) => post<any>('/operations/tables/merge/', data)

export const closeTable = (tableId: string) =>
  post<any>(`/operations/tables/${tableId}/close/`)

// ---------------------------------------------------------------------------
// Bill Splits
// ---------------------------------------------------------------------------

export const getBillSplits = (billId: string) =>
  get<any[]>(`/operations/bills/${billId}/splits/`)

export const createBillSplit = (billId: string, data: {
  split_type: string; num_splits?: number; item_allocations?: any[]
}) => post<any>(`/operations/bills/${billId}/split/`, data)

export const finalizeBillSplit = (billId: string, splitId: string) =>
  post<any>(`/operations/bills/${billId}/splits/${splitId}/finalize/`)

// ---------------------------------------------------------------------------
// Receipts
// ---------------------------------------------------------------------------

export const printReceipt = (billId: string, data: {
  payment_id?: string; print_type?: string; reason?: string
}) => post<any>(`/operations/bills/${billId}/receipt/print/`, data)

export const reprintReceipt = (billId: string, reason: string) =>
  post<any>(`/operations/bills/${billId}/receipt/reprint/`, { reason })

// ---------------------------------------------------------------------------
// Shifts
// ---------------------------------------------------------------------------

export const listShifts = () =>
  get<any[]>('/operations/shifts/')

export const createShift = (data: { branch_id: string; shift_type: string; notes?: string }) =>
  post<any>('/operations/shifts/', data)

export const closeShift = (shiftId: string, notes?: string) =>
  post<any>(`/operations/shifts/${shiftId}/close/`, { notes })

export const getShiftHandover = (shiftId: string) =>
  get<any>(`/operations/shifts/${shiftId}/handover/`)

export const addHandoverNote = (shiftId: string, data: {
  note_type: string; content: string; priority?: string
}) => post<any>(`/operations/shifts/${shiftId}/handover/`, data)

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export const getOperationsDashboard = (branchId?: string) =>
  get<any>('/operations/dashboard/', { params: branchId ? { branch_id: branchId } : undefined })
