// =============================================================================
// RestaurantFlow — Reporting Hooks
// Phase 14
// =============================================================================

import { useQuery } from '@tanstack/react-query'
import type { ReportFilters } from '@/services/reporting'
import * as reporting from '@/services/reporting'

const STALE = 60_000  // 1 minute for live KPIs

export function useDashboard(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'dashboard', filters],
    queryFn: () => reporting.getDashboard(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function useSalesSummary(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'sales-summary', filters],
    queryFn: () => reporting.getSalesSummary(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function useSalesTrend(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'sales-trend', filters],
    queryFn: () => reporting.getSalesTrend(filters),
    staleTime: 5 * 60_000,
    retry: 1,
  })
}

export function useHourlySales(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'hourly-sales', filters],
    queryFn: () => reporting.getHourlySales(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function useOrdersSummary(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'orders-summary', filters],
    queryFn: () => reporting.getOrdersSummary(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function useOrdersByType(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'orders-by-type', filters],
    queryFn: () => reporting.getOrdersByType(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function useTopSellingItems(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'top-selling', filters],
    queryFn: () => reporting.getTopSellingItems(filters),
    staleTime: 5 * 60_000,
    retry: 1,
  })
}

export function useCategoryPerformance(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'categories', filters],
    queryFn: () => reporting.getCategoryPerformance(filters),
    staleTime: 5 * 60_000,
    retry: 1,
  })
}

export function useBranchPerformance(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'branches', filters],
    queryFn: () => reporting.getBranchPerformance(filters),
    staleTime: 5 * 60_000,
    retry: 1,
  })
}

export function usePaymentSummary(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'payment-summary', filters],
    queryFn: () => reporting.getPaymentSummary(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function usePaymentMethods(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'payment-methods', filters],
    queryFn: () => reporting.getPaymentMethods(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function useKitchenPerformance(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'kitchen-performance', filters],
    queryFn: () => reporting.getKitchenPerformance(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function useInventorySummary(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'inventory-summary', filters],
    queryFn: () => reporting.getInventorySummary(filters),
    staleTime: 2 * 60_000,
    retry: 1,
  })
}

export function useExpenses(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'expenses', filters],
    queryFn: () => reporting.getExpenses(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function usePayables(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'payables', filters],
    queryFn: () => reporting.getPayables(filters),
    staleTime: STALE,
    retry: 1,
  })
}

export function useFinancialSummary(filters?: ReportFilters) {
  return useQuery({
    queryKey: ['reporting', 'financial-summary', filters],
    queryFn: () => reporting.getFinancialSummary(filters),
    staleTime: 60_000,
    retry: 1,
  })
}
