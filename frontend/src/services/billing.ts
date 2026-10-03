// =============================================================================
// RestaurantFlow — Billing API Service
// Phase 8
// =============================================================================

import { get, post, del } from '@/services/api'
import type {
  Bill,
  BillSummary,
  BillCalculation,
  BillReceiptData,
  BillCorrectionRequest,
  ApplyDiscountPayload,
  FinalizeBillPayload,
  CancelBillPayload,
  VoidBillPayload,
  CreateCorrectionPayload,
  ReviewCorrectionPayload,
  BillListParams,
  PaginatedResponse,
} from '@/types'

// ---------------------------------------------------------------------------
// Bills
// ---------------------------------------------------------------------------

/** GET /api/billing/bills/ */
export const listBills = (params?: BillListParams) =>
  get<PaginatedResponse<BillSummary>>('/billing/bills/', { params })

/** POST /api/billing/bills/from-order/{order_id}/ */
export const createBillFromOrder = (orderId: string) =>
  post<Bill>(`/billing/bills/from-order/${orderId}/`)

/** GET /api/billing/bills/{id}/ */
export const getBill = (id: string) =>
  get<Bill>(`/billing/bills/${id}/`)

/** GET /api/billing/bills/{id}/calculate/ */
export const calculateBill = (id: string) =>
  get<BillCalculation>(`/billing/bills/${id}/calculate/`)

/** POST /api/billing/bills/{id}/discount/ */
export const applyDiscount = (id: string, data: ApplyDiscountPayload) =>
  post<Bill>(`/billing/bills/${id}/discount/`, data)

/** DELETE /api/billing/bills/{id}/discount/ */
export const removeDiscount = (id: string) =>
  del<Bill>(`/billing/bills/${id}/discount/`)

/** POST /api/billing/bills/{id}/finalize/ */
export const finalizeBill = (id: string, data?: FinalizeBillPayload) =>
  post<Bill>(`/billing/bills/${id}/finalize/`, data ?? {})

/** POST /api/billing/bills/{id}/cancel/ */
export const cancelBill = (id: string, data: CancelBillPayload) =>
  post<Bill>(`/billing/bills/${id}/cancel/`, data)

/** POST /api/billing/bills/{id}/void/ */
export const voidBill = (id: string, data: VoidBillPayload) =>
  post<Bill>(`/billing/bills/${id}/void/`, data)

/** GET /api/billing/bills/{id}/receipt/ */
export const getBillReceipt = (id: string) =>
  get<BillReceiptData>(`/billing/bills/${id}/receipt/`)

// ---------------------------------------------------------------------------
// Corrections
// ---------------------------------------------------------------------------

/** GET /api/billing/bill-corrections/ */
export const listCorrections = (params?: Record<string, string>) =>
  get<PaginatedResponse<BillCorrectionRequest>>('/billing/bill-corrections/', { params })

/** POST /api/billing/bills/{id}/corrections/ */
export const requestCorrection = (billId: string, data: CreateCorrectionPayload) =>
  post<BillCorrectionRequest>(`/billing/bills/${billId}/corrections/`, data)

/** GET /api/billing/bill-corrections/{id}/ */
export const getCorrection = (id: string) =>
  get<BillCorrectionRequest>(`/billing/bill-corrections/${id}/`)

/** POST /api/billing/bill-corrections/{id}/approve/ */
export const approveCorrection = (id: string, data?: ReviewCorrectionPayload) =>
  post<BillCorrectionRequest>(`/billing/bill-corrections/${id}/approve/`, data ?? {})

/** POST /api/billing/bill-corrections/{id}/reject/ */
export const rejectCorrection = (id: string, data: ReviewCorrectionPayload) =>
  post<BillCorrectionRequest>(`/billing/bill-corrections/${id}/reject/`, data)

/** POST /api/billing/bill-corrections/{id}/cancel/ */
export const cancelCorrection = (id: string) =>
  post<BillCorrectionRequest>(`/billing/bill-corrections/${id}/cancel/`)
