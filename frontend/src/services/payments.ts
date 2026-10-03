// =============================================================================
// RestaurantFlow — Payments API Service
// Phase 9
// =============================================================================

import { get, post } from '@/services/api'
import type {
  Payment,
  PaymentSummary,
  BillPaymentSummary,
  BillReceiptDataV9,
  PaymentRefundItem,
  PaymentAuditLog,
  CreatePaymentPayload,
  CancelPaymentPayload,
  CreateRefundPayload,
  RejectRefundPayload,
  ProcessRefundPayload,
  PaymentListParams,
  PaginatedResponse,
} from '@/types'

// ---------------------------------------------------------------------------
// Payments
// ---------------------------------------------------------------------------

/** POST /api/payments/ — create a payment against a finalized bill */
export const createPayment = (data: CreatePaymentPayload) =>
  post<Payment>('/payments/', data)

/** GET /api/payments/list/ — list payments (filterable) */
export const listPayments = (params?: PaymentListParams) =>
  get<PaginatedResponse<PaymentSummary>>('/payments/list/', { params })

/** GET /api/payments/{id}/ — full payment detail with nested refunds */
export const getPayment = (id: string) =>
  get<Payment>(`/payments/${id}/`)

/** POST /api/payments/{id}/cancel/ — cancel a PENDING payment */
export const cancelPayment = (id: string, data: CancelPaymentPayload) =>
  post<Payment>(`/payments/${id}/cancel/`, data)

// ---------------------------------------------------------------------------
// Bill-scoped payment endpoints
// ---------------------------------------------------------------------------

/** GET /api/payments/bill/{billId}/ — all payments for a bill */
export const getBillPayments = (billId: string) =>
  get<Payment[]>(`/payments/bill/${billId}/`)

/** GET /api/payments/bill/{billId}/summary/ — totals, remaining, status */
export const getBillPaymentSummary = (billId: string) =>
  get<BillPaymentSummary>(`/payments/bill/${billId}/summary/`)

/** GET /api/payments/bill/{billId}/receipt/ — full receipt with payment data */
export const getBillReceiptWithPayments = (billId: string) =>
  get<BillReceiptDataV9>(`/payments/bill/${billId}/receipt/`)

// ---------------------------------------------------------------------------
// Refunds
// ---------------------------------------------------------------------------

/** GET  /api/payments/{id}/refunds/ — list refunds for a payment */
export const listRefunds = (paymentId: string) =>
  get<PaymentRefundItem[]>(`/payments/${paymentId}/refunds/`)

/** POST /api/payments/{id}/refunds/ — request a refund */
export const requestRefund = (paymentId: string, data: CreateRefundPayload) =>
  post<PaymentRefundItem>(`/payments/${paymentId}/refunds/`, data)

/** GET  /api/payments/refunds/{refundId}/ — refund detail */
export const getRefund = (refundId: string) =>
  get<PaymentRefundItem>(`/payments/refunds/${refundId}/`)

/** POST /api/payments/refunds/{refundId}/approve/ */
export const approveRefund = (refundId: string) =>
  post<PaymentRefundItem>(`/payments/refunds/${refundId}/approve/`, {})

/** POST /api/payments/refunds/{refundId}/reject/ */
export const rejectRefund = (refundId: string, data: RejectRefundPayload) =>
  post<PaymentRefundItem>(`/payments/refunds/${refundId}/reject/`, data)

/** POST /api/payments/refunds/{refundId}/process/ */
export const processRefund = (refundId: string, data?: ProcessRefundPayload) =>
  post<PaymentRefundItem>(`/payments/refunds/${refundId}/process/`, data ?? {})

/** POST /api/payments/refunds/{refundId}/cancel/ */
export const cancelRefund = (refundId: string) =>
  post<PaymentRefundItem>(`/payments/refunds/${refundId}/cancel/`, {})

// ---------------------------------------------------------------------------
// Audit log
// ---------------------------------------------------------------------------

/** GET /api/payments/{id}/audit/ — immutable audit trail */
export const getPaymentAuditLog = (paymentId: string) =>
  get<PaymentAuditLog[]>(`/payments/${paymentId}/audit/`)
