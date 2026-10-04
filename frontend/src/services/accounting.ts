// =============================================================================
// RestaurantFlow — Accounting API Service
// Phase 13
// =============================================================================

import { get, post, patch } from '@/services/api'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FiscalYear {
  id: string
  restaurant: string
  restaurant_name: string
  name: string
  start_date: string
  end_date: string
  status: 'OPEN' | 'CLOSED'
  closed_at: string | null
  closed_by: string | null
  closed_by_email: string | null
  created_at: string
  updated_at: string
}

export interface AccountingPeriod {
  id: string
  restaurant: string
  restaurant_name: string
  fiscal_year: string | null
  fiscal_year_name: string | null
  name: string
  start_date: string
  end_date: string
  status: 'OPEN' | 'CLOSE_REQUESTED' | 'CLOSED'
  closed_at: string | null
  closed_by: string | null
  closed_by_email: string | null
  closing_note: string
  created_at: string
  updated_at: string
}

export interface Account {
  id: string
  restaurant: string
  restaurant_name: string
  code: string
  name: string
  description: string
  account_type: 'ASSET' | 'LIABILITY' | 'EQUITY' | 'REVENUE' | 'EXPENSE'
  account_subtype: string
  parent_account: string | null
  parent_code: string | null
  parent_name: string | null
  is_group: boolean
  is_postable: boolean
  is_active: boolean
  is_system_account: boolean
  normal_balance: 'DEBIT' | 'CREDIT'
  children_count: number
  created_at: string
  updated_at: string
}

export interface AccountTree extends Omit<Account, 'children_count'> {
  children: AccountTree[]
}

export interface AccountingSettings {
  id: string
  restaurant: string
  restaurant_name: string
  default_sales_account: string | null
  default_sales_account_code: string | null
  default_discount_account: string | null
  default_cash_account: string | null
  default_cash_account_code: string | null
  default_bank_account: string | null
  default_bank_account_code: string | null
  default_accounts_receivable: string | null
  default_accounts_receivable_code: string | null
  default_inventory_account: string | null
  default_inventory_account_code: string | null
  default_card_clearing_account: string | null
  default_upi_clearing_account: string | null
  default_accounts_payable: string | null
  default_accounts_payable_code: string | null
  default_tax_payable: string | null
  default_tax_payable_code: string | null
  default_cogs_account: string | null
  default_cogs_account_code: string | null
  default_rounding_account: string | null
  retained_earnings_account: string | null
  created_at: string
  updated_at: string
}

export interface JournalEntryLine {
  id: string
  journal_entry: string
  account: string
  account_code: string
  account_name: string
  account_type: string
  normal_balance: string
  description: string
  debit_amount: string
  credit_amount: string
  reference_type: string
  reference_id: string | null
  created_at: string
}

export interface JournalEntry {
  id: string
  restaurant: string
  restaurant_name: string
  branch: string | null
  branch_name: string | null
  entry_number: string
  accounting_period: string
  period_name: string
  entry_date: string
  description: string
  source_type: string
  source_id: string | null
  reference_type: string
  reference_id: string | null
  status: 'DRAFT' | 'POSTED' | 'REVERSED' | 'VOID'
  created_by: number
  created_by_email: string
  posted_by: number | null
  posted_by_email: string | null
  posted_at: string | null
  reversed_by: number | null
  reversed_by_email: string | null
  reversed_at: string | null
  reversal_reason: string
  reversal_of: string | null
  lines: JournalEntryLine[]
  total_debits: string
  total_credits: string
  is_balanced: boolean
  created_at: string
  updated_at: string
}

export interface TrialBalanceRow {
  account_code: string
  account_name: string
  account_type: string
  normal_balance: string
  debit_total: string
  credit_total: string
}

export interface TrialBalance {
  accounts: TrialBalanceRow[]
  grand_debit: string
  grand_credit: string
  is_balanced: boolean
  variance: string
}

export interface PnLRow {
  code: string
  name: string
  subtype: string
  balance: string
}

export interface ProfitLoss {
  revenue: PnLRow[]
  total_revenue: string
  cogs: PnLRow[]
  total_cogs: string
  gross_profit: string
  operating_expenses: PnLRow[]
  total_operating_expenses: string
  operating_profit: string
}

export interface BalanceSheetRow {
  code: string
  name: string
  subtype: string
  balance: string
}

export interface BalanceSheet {
  assets: BalanceSheetRow[]
  total_assets: string
  liabilities: BalanceSheetRow[]
  total_liabilities: string
  equity: BalanceSheetRow[]
  total_equity: string
  total_liabilities_and_equity: string
  is_balanced: boolean
  variance: string
}

export interface AccountingDashboard {
  total_revenue: string
  total_cogs: string
  gross_profit: string
  operating_profit: string
  total_assets: string
  total_liabilities: string
  total_equity: string
  balance_sheet_balanced: boolean
  trial_balance_balanced: boolean
  trial_balance_variance: string
  open_periods_count: number
}

export interface GeneralLedgerRow {
  date: string
  journal_number: string
  description: string
  debit: string
  credit: string
  balance: string
  account_code: string
  account_name: string
  source_type: string
  branch: string | null
  journal_entry_id: string
}

export interface AccountStatement {
  account_code: string
  account_name: string
  account_type: string
  normal_balance: string
  opening_balance: string
  transactions: {
    date: string
    journal_number: string
    description: string
    debit: string
    credit: string
    balance: string
  }[]
  closing_balance: string
  total_debits: string
  total_credits: string
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export const getAccountingDashboard = (restaurantId: string, periodId?: string) =>
  get<AccountingDashboard>('/accounting/dashboard/', {
    params: { restaurant: restaurantId, ...(periodId ? { period: periodId } : {}) },
  })

// ---------------------------------------------------------------------------
// Fiscal Years
// ---------------------------------------------------------------------------

export const listFiscalYears = (restaurantId?: string) =>
  get<FiscalYear[]>('/accounting/fiscal-years/', {
    params: restaurantId ? { restaurant: restaurantId } : undefined,
  })

export const createFiscalYear = (data: {
  restaurant: string
  name: string
  start_date: string
  end_date: string
}) => post<FiscalYear>('/accounting/fiscal-years/', data)

export const closeFiscalYear = (id: string) =>
  post<FiscalYear>(`/accounting/fiscal-years/${id}/close/`, {})

// ---------------------------------------------------------------------------
// Accounting Periods
// ---------------------------------------------------------------------------

export const listPeriods = (params?: Record<string, string>) =>
  get<AccountingPeriod[]>('/accounting/periods/', { params })

export const createPeriod = (data: {
  restaurant: string
  name: string
  start_date: string
  end_date: string
  fiscal_year?: string
}) => post<AccountingPeriod>('/accounting/periods/', data)

export const closePeriod = (id: string, note?: string) =>
  post<AccountingPeriod>(`/accounting/periods/${id}/close/`, { note: note ?? '' })

export const reopenPeriod = (id: string, note?: string) =>
  post<AccountingPeriod>(`/accounting/periods/${id}/reopen/`, { note: note ?? '' })

// ---------------------------------------------------------------------------
// Chart of Accounts
// ---------------------------------------------------------------------------

export const listAccounts = (params?: Record<string, string>) =>
  get<Account[]>('/accounting/accounts/', { params })

export const getAccountTree = (restaurantId: string) =>
  get<AccountTree[]>('/accounting/accounts/tree/', { params: { restaurant: restaurantId } })

export const getAccount = (id: string) =>
  get<Account>(`/accounting/accounts/${id}/`)

export const createAccount = (data: {
  restaurant: string
  code: string
  name: string
  account_type: string
  description?: string
  account_subtype?: string
  parent_account?: string | null
  is_group?: boolean
  is_postable?: boolean
  normal_balance?: string
}) => post<Account>('/accounting/accounts/', data)

export const updateAccount = (id: string, data: Partial<Account>) =>
  patch<Account>(`/accounting/accounts/${id}/`, data)

export const deactivateAccount = (id: string) =>
  post<Account>(`/accounting/accounts/${id}/deactivate/`, {})

export const getAccountStatement = (id: string, params?: Record<string, string>) =>
  get<AccountStatement>(`/accounting/accounts/${id}/statement/`, { params })

// ---------------------------------------------------------------------------
// Accounting Settings
// ---------------------------------------------------------------------------

export const getAccountingSettings = (restaurantId: string) =>
  get<AccountingSettings>('/accounting/settings/', { params: { restaurant: restaurantId } })

export const updateAccountingSettings = (restaurantId: string, data: Partial<AccountingSettings>) =>
  (fetch as unknown as typeof post)(`/accounting/settings/?restaurant=${restaurantId}`, data)

// ---------------------------------------------------------------------------
// Journal Entries
// ---------------------------------------------------------------------------

export const listJournalEntries = (params?: Record<string, string>) =>
  get<{ count: number; results: JournalEntry[] }>('/accounting/journals/', { params })

export const getJournalEntry = (id: string) =>
  get<JournalEntry>(`/accounting/journals/${id}/`)

export const createJournalEntry = (data: {
  restaurant: string
  accounting_period: string
  entry_date: string
  description: string
  source_type?: string
  lines: { account: string; description?: string; debit_amount?: string; credit_amount?: string }[]
}) => post<JournalEntry>('/accounting/journals/', data)

export const postJournalEntry = (id: string) =>
  post<JournalEntry>(`/accounting/journals/${id}/post/`, {})

export const reverseJournalEntry = (id: string, reason: string, reversalDate?: string) =>
  post<JournalEntry>(`/accounting/journals/${id}/reverse/`, {
    reason,
    reversal_date: reversalDate ?? null,
  })

export const voidJournalEntry = (id: string, reason?: string) =>
  post<JournalEntry>(`/accounting/journals/${id}/void/`, { reason: reason ?? '' })

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export const getGeneralLedger = (restaurantId: string, params?: Record<string, string>) =>
  get<{ results: GeneralLedgerRow[]; count: number }>('/accounting/general-ledger/', {
    params: { restaurant: restaurantId, ...params },
  })

export const getTrialBalance = (restaurantId: string, params?: Record<string, string>) =>
  get<TrialBalance>('/accounting/trial-balance/', {
    params: { restaurant: restaurantId, ...params },
  })

export const getProfitLoss = (restaurantId: string, params?: Record<string, string>) =>
  get<ProfitLoss>('/accounting/profit-loss/', {
    params: { restaurant: restaurantId, ...params },
  })

export const getBalanceSheet = (restaurantId: string, params?: Record<string, string>) =>
  get<BalanceSheet>('/accounting/balance-sheet/', {
    params: { restaurant: restaurantId, ...params },
  })

export const getCashFlow = (restaurantId: string, params?: Record<string, string>) =>
  get<{
    accounts: { account_code: string; account_name: string; inflows: string; outflows: string; net: string }[]
    total_inflows: string
    total_outflows: string
    net_cash_movement: string
  }>('/accounting/cash-flow/', {
    params: { restaurant: restaurantId, ...params },
  })
