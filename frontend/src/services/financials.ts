// =============================================================================
// RestaurantFlow — Financials API Service
// Phase 12
// =============================================================================

import { get, post, patch, del } from '@/services/api'
import type {
  ExpenseCategory,
  Expense,
  ExpenseDetail,
  ExpenseCorrectionRequest,
  ExpenseAttachment,
  RecurringExpense,
  SupplierInvoice,
  SupplierInvoiceDetail,
  Payable,
  FinancialDashboard,
  PayableDashboard,
  PaginatedResponse,
  CreateExpenseCategoryPayload,
  CreateExpensePayload,
  UpdateExpensePayload,
  CreateRecurringExpensePayload,
  CreateSupplierInvoicePayload,
  CreateCorrectionRequestPayload,
} from '@/types'

// ---------------------------------------------------------------------------
// Expense Categories
// ---------------------------------------------------------------------------

export const listExpenseCategories = (params?: Record<string, string>) =>
  get<ExpenseCategory[]>('/financials/expense-categories/', { params })

export const createExpenseCategory = (data: CreateExpenseCategoryPayload) =>
  post<ExpenseCategory>('/financials/expense-categories/', data)

export const getExpenseCategory = (id: string) =>
  get<ExpenseCategory>(`/financials/expense-categories/${id}/`)

export const updateExpenseCategory = (id: string, data: Partial<CreateExpenseCategoryPayload>) =>
  patch<ExpenseCategory>(`/financials/expense-categories/${id}/`, data)

// ---------------------------------------------------------------------------
// Expenses
// ---------------------------------------------------------------------------

export const listExpenses = (params?: Record<string, string>) =>
  get<PaginatedResponse<Expense>>('/financials/expenses/', { params })

export const createExpense = (data: CreateExpensePayload) =>
  post<ExpenseDetail>('/financials/expenses/', data)

export const getExpense = (id: string) =>
  get<ExpenseDetail>(`/financials/expenses/${id}/`)

export const updateExpense = (id: string, data: UpdateExpensePayload) =>
  patch<ExpenseDetail>(`/financials/expenses/${id}/`, data)

export const submitExpense = (id: string) =>
  post<ExpenseDetail>(`/financials/expenses/${id}/submit/`, {})

export const approveExpense = (id: string, note?: string) =>
  post<ExpenseDetail>(`/financials/expenses/${id}/approve/`, { approval_note: note ?? '' })

export const rejectExpense = (id: string, reason: string) =>
  post<ExpenseDetail>(`/financials/expenses/${id}/reject/`, { rejection_reason: reason })

export const cancelExpense = (id: string) =>
  post<ExpenseDetail>(`/financials/expenses/${id}/cancel/`, {})

// ---------------------------------------------------------------------------
// Expense Attachments
// ---------------------------------------------------------------------------

export const listAttachments = (expenseId: string) =>
  get<ExpenseAttachment[]>(`/financials/expenses/${expenseId}/attachments/`)

export const uploadAttachment = (expenseId: string, file: File) => {
  const form = new FormData()
  form.append('file', file)
  return post<ExpenseAttachment>(`/financials/expenses/${expenseId}/attachments/`, form)
}

export const deleteAttachment = (expenseId: string, attId: string) =>
  del(`/financials/expenses/${expenseId}/attachments/${attId}/`)

// ---------------------------------------------------------------------------
// Expense Corrections
// ---------------------------------------------------------------------------

export const listCorrections = (params?: Record<string, string>) =>
  get<PaginatedResponse<ExpenseCorrectionRequest>>('/financials/expense-corrections/', { params })

export const requestCorrection = (expenseId: string, data: CreateCorrectionRequestPayload) =>
  post<ExpenseCorrectionRequest>(`/financials/expenses/${expenseId}/corrections/`, data)

export const approveCorrection = (id: string, note?: string) =>
  post<ExpenseCorrectionRequest>(`/financials/expense-corrections/${id}/approve/`, { review_note: note ?? '' })

export const rejectCorrection = (id: string, note: string) =>
  post<ExpenseCorrectionRequest>(`/financials/expense-corrections/${id}/reject/`, { review_note: note })

export const cancelCorrection = (id: string) =>
  post<ExpenseCorrectionRequest>(`/financials/expense-corrections/${id}/cancel/`, {})

// ---------------------------------------------------------------------------
// Recurring Expenses
// ---------------------------------------------------------------------------

export const listRecurringExpenses = (params?: Record<string, string>) =>
  get<PaginatedResponse<RecurringExpense>>('/financials/recurring-expenses/', { params })

export const createRecurringExpense = (data: CreateRecurringExpensePayload) =>
  post<RecurringExpense>('/financials/recurring-expenses/', data)

export const getRecurringExpense = (id: string) =>
  get<RecurringExpense>(`/financials/recurring-expenses/${id}/`)

export const updateRecurringExpense = (id: string, data: Partial<CreateRecurringExpensePayload>) =>
  patch<RecurringExpense>(`/financials/recurring-expenses/${id}/`, data)

export const disableRecurringExpense = (id: string) =>
  post<RecurringExpense>(`/financials/recurring-expenses/${id}/disable/`, {})

// ---------------------------------------------------------------------------
// Supplier Invoices
// ---------------------------------------------------------------------------

export const listSupplierInvoices = (params?: Record<string, string>) =>
  get<PaginatedResponse<SupplierInvoice>>('/financials/supplier-invoices/', { params })

export const createSupplierInvoice = (data: CreateSupplierInvoicePayload) =>
  post<SupplierInvoiceDetail>('/financials/supplier-invoices/', data)

export const getSupplierInvoice = (id: string) =>
  get<SupplierInvoiceDetail>(`/financials/supplier-invoices/${id}/`)

export const submitSupplierInvoice = (id: string) =>
  post<SupplierInvoiceDetail>(`/financials/supplier-invoices/${id}/submit/`, {})

export const approveSupplierInvoice = (id: string, note?: string) =>
  post<SupplierInvoiceDetail>(`/financials/supplier-invoices/${id}/approve/`, { note: note ?? '' })

export const cancelSupplierInvoice = (id: string, reason?: string) =>
  post<SupplierInvoiceDetail>(`/financials/supplier-invoices/${id}/cancel/`, { reason: reason ?? '' })

// ---------------------------------------------------------------------------
// Payables
// ---------------------------------------------------------------------------

export const listPayables = (params?: Record<string, string>) =>
  get<PaginatedResponse<Payable>>('/financials/payables/', { params })

export const getPayable = (id: string) =>
  get<Payable>(`/financials/payables/${id}/`)

export const recordPayment = (id: string, amount: string) =>
  post<Payable>(`/financials/payables/${id}/record-payment/`, { payment_amount: amount })

export const getPayableDashboard = (params?: Record<string, string>) =>
  get<PayableDashboard>('/financials/payables/dashboard/', { params })

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export const getFinancialDashboard = (params?: Record<string, string>) =>
  get<FinancialDashboard>('/financials/dashboard/', { params })
