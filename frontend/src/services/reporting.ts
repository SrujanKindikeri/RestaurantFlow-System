// =============================================================================
// RestaurantFlow — Reporting API Service
// Phase 14
// =============================================================================

import { get } from '@/services/api'

// ---------------------------------------------------------------------------
// Filter params type
// ---------------------------------------------------------------------------

export interface ReportFilters {
  date_from?: string
  date_to?: string
  restaurant_id?: string
  branch_id?: string
  limit?: number
  sort_by?: string
  granularity?: 'daily' | 'weekly' | 'monthly'
}

// ---------------------------------------------------------------------------
// Response types
// ---------------------------------------------------------------------------

export interface ReportResponse<T> {
  period: { date_from: string; date_to: string }
  filters: Record<string, unknown>
  data: T
}

export interface SalesSummary {
  gross_sales: string
  discount_amount: string
  taxable_amount: string
  tax_amount: string
  rounding_amount: string
  net_sales: string
  number_of_bills: number
  average_bill_value: string | null
}

export interface SalesTrendItem {
  date: string
  gross_sales: string
  discounts: string
  tax: string
  net_sales: string
  bill_count: number
  order_count: number
  average_bill_value: string | null
}

export interface HourlySalesItem {
  hour: number
  sales: string
  bill_count: number
  order_count: number
}

export interface OrdersSummary {
  total_orders: number
  confirmed_orders: number
  cancelled_orders: number
  dine_in_orders: number
  takeaway_orders: number
  counter_orders: number
  average_order_value: string | null
}

export interface OrdersByTypeItem {
  order_type: string
  order_count: number
  sales: string
  percentage_of_orders: string
}

export interface TopSellingItem {
  rank: number
  menu_item_id: string
  menu_item_name: string
  category: string | null
  quantity_sold: string
  net_revenue: string
  number_of_orders: number
}

export interface CategoryPerformanceItem {
  category_id: string | null
  category: string
  quantity_sold: string
  gross_revenue: string
  net_revenue: string
  sales_percentage: string
  average_item_value: string | null
}

export interface BranchPerformanceItem {
  branch_id: string
  branch_name: string
  orders: number
  bills: number
  revenue: string
  payments: string
  refunds: string
  discounts: string
  taxes: string
  average_bill_value: string | null
  gross_profit: string | null
  gross_margin: string | null
}

export interface PaymentSummary {
  total_paid: string
  cash: string
  upi: string
  card: string
  other: string
  payment_count: number
  refund_amount: string
  refund_count: number
}

export interface PaymentMethodItem {
  payment_method: string
  total: string
  count: number
  percentage: string
}

export interface KitchenPerformance {
  orders_received: number
  orders_ready: number
  orders_cancelled: number
  orders_pending: number
  average_preparation_time_seconds: number | null
  median_preparation_time_seconds: number | null
  maximum_preparation_time_seconds: number | null
}

export interface InventorySummary {
  total_inventory_items: number
  low_stock_items: number
  out_of_stock_items: number
  stock_value_estimate: string
}

export interface DashboardKPIs {
  period: { date_from: string; date_to: string; today: string }
  sales: {
    today_net_sales: string
    today_bill_count: number
    today_average_bill_value: string | null
    yesterday_net_sales: string
    today_vs_yesterday_growth: string | null
    week_net_sales: string
    month_net_sales: string
    week_vs_prev_week_growth: string | null
    month_vs_prev_month_growth: string | null
  }
  orders: {
    today_total_orders: number
    today_confirmed_orders: number
    today_cancelled_orders: number
    today_average_order_value: string | null
  }
  products: {
    top_revenue_item: TopSellingItem | null
    top_quantity_item: TopSellingItem | null
    top_category: CategoryPerformanceItem | null
  }
  payments: {
    today_total_collected: string
    today_cash: string
    today_upi: string
    today_card: string
    today_other: string
    today_refund_amount: string
    today_refund_count: number
  }
  kitchen: {
    today_orders_received: number
    today_orders_ready: number
    today_orders_pending: number
    today_avg_prep_time_seconds: number | null
  }
  inventory: {
    total_items: number
    low_stock_count: number
    out_of_stock_count: number
    stock_value_estimate: string
  }
  financials: {
    monthly_expenses: string | null
    outstanding_payables: string | null
    overdue_payables: string | null
  }
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

const p = (filters?: ReportFilters) => {
  if (!filters) return undefined
  const params: Record<string, string | number> = {}
  if (filters.date_from) params.date_from = filters.date_from
  if (filters.date_to) params.date_to = filters.date_to
  if (filters.restaurant_id) params.restaurant_id = filters.restaurant_id
  if (filters.branch_id) params.branch_id = filters.branch_id
  if (filters.limit) params.limit = filters.limit
  if (filters.sort_by) params.sort_by = filters.sort_by
  if (filters.granularity) params.granularity = filters.granularity
  return Object.keys(params).length ? { params } : undefined
}

export const getDashboard = (filters?: ReportFilters) =>
  get<DashboardKPIs>('/reporting/dashboard/', p(filters))

export const getSalesSummary = (filters?: ReportFilters) =>
  get<ReportResponse<SalesSummary>>('/reporting/sales/summary/', p(filters))

export const getSalesTrend = (filters?: ReportFilters) =>
  get<ReportResponse<SalesTrendItem[]>>('/reporting/sales/trend/', p(filters))

export const getHourlySales = (filters?: ReportFilters) =>
  get<ReportResponse<HourlySalesItem[]>>('/reporting/sales/hourly/', p(filters))

export const getOrdersSummary = (filters?: ReportFilters) =>
  get<ReportResponse<OrdersSummary>>('/reporting/orders/summary/', p(filters))

export const getOrdersByType = (filters?: ReportFilters) =>
  get<ReportResponse<OrdersByTypeItem[]>>('/reporting/orders/by-type/', p(filters))

export const getMenuItems = (filters?: ReportFilters) =>
  get<ReportResponse<TopSellingItem[]>>('/reporting/menu/items/', p(filters))

export const getTopSellingItems = (filters?: ReportFilters) =>
  get<ReportResponse<TopSellingItem[]>>('/reporting/menu/top-selling/', p(filters))

export const getCategoryPerformance = (filters?: ReportFilters) =>
  get<ReportResponse<CategoryPerformanceItem[]>>('/reporting/menu/categories/', p(filters))

export const getBranchPerformance = (filters?: ReportFilters) =>
  get<ReportResponse<BranchPerformanceItem[]>>('/reporting/branches/performance/', p(filters))

export const getPaymentSummary = (filters?: ReportFilters) =>
  get<ReportResponse<PaymentSummary>>('/reporting/payments/summary/', p(filters))

export const getPaymentMethods = (filters?: ReportFilters) =>
  get<ReportResponse<PaymentMethodItem[]>>('/reporting/payments/methods/', p(filters))

export const getKitchenPerformance = (filters?: ReportFilters) =>
  get<ReportResponse<KitchenPerformance>>('/reporting/kitchen/performance/', p(filters))

export const getInventorySummary = (filters?: ReportFilters) =>
  get<ReportResponse<InventorySummary>>('/reporting/inventory/summary/', p(filters))

export const getExpenses = (filters?: ReportFilters) =>
  get<ReportResponse<Record<string, unknown>>>('/reporting/expenses/', p(filters))

export const getPayables = (filters?: ReportFilters) =>
  get<ReportResponse<Record<string, unknown>>>('/reporting/payables/', p(filters))

export const getFinancialSummary = (filters?: ReportFilters) =>
  get<ReportResponse<Record<string, unknown>>>('/reporting/financial-summary/', p(filters))

/** Build a download URL for CSV export */
export const getExportUrl = (reportType: string, filters?: ReportFilters): string => {
  const base = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api')
  const params = new URLSearchParams()
  if (filters?.date_from) params.set('date_from', filters.date_from)
  if (filters?.date_to) params.set('date_to', filters.date_to)
  if (filters?.branch_id) params.set('branch_id', filters.branch_id)
  const token = localStorage.getItem('access_token') ?? ''
  params.set('token', token)  // Note: server must support ?token= or caller adds auth header
  return `${base}/reporting/export/${reportType}/?${params.toString()}`
}
