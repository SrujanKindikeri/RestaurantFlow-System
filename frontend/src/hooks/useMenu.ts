// =============================================================================
// RestaurantFlow — Menu Hooks
// Phase 5
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  TaxRate,
  TaxRateCreatePayload,
  TaxRateUpdatePayload,
  Category,
  CategoryCreatePayload,
  CategoryUpdatePayload,
  MenuItem,
  MenuItemDetail,
  MenuItemCreatePayload,
  MenuItemUpdatePayload,
  MenuItemPrice,
  MenuItemPriceCreatePayload,
  MenuItemPriceUpdatePayload,
  MenuItemBranch,
  MenuItemBranchCreatePayload,
  MenuItemBranchUpdatePayload,
  BranchCatalog,
  MenuDashboardStats,
  PaginatedResponse,
} from '@/types'
import {
  listTaxRates, getTaxRate, createTaxRate, updateTaxRate, disableTaxRate, enableTaxRate,
  listCategories, getCategory, createCategory, updateCategory, disableCategory, enableCategory,
  listMenuItems, getMenuItem, createMenuItem, updateMenuItem, disableMenuItem, enableMenuItem,
  listPrices, getPrice, createPrice, updatePrice, deactivatePrice,
  listAvailability, getAvailability, createAvailability, updateAvailability,
  getBranchCatalog,
  getMenuDashboard,
} from '@/services/menu'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const taxRateKeys = {
  all: ['tax-rates'] as const,
  lists: () => [...taxRateKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) => [...taxRateKeys.lists(), params] as const,
  details: () => [...taxRateKeys.all, 'detail'] as const,
  detail: (id: string) => [...taxRateKeys.details(), id] as const,
}

export const categoryKeys = {
  all: ['categories'] as const,
  lists: () => [...categoryKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) => [...categoryKeys.lists(), params] as const,
  details: () => [...categoryKeys.all, 'detail'] as const,
  detail: (id: string) => [...categoryKeys.details(), id] as const,
}

export const menuItemKeys = {
  all: ['menu-items'] as const,
  lists: () => [...menuItemKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) => [...menuItemKeys.lists(), params] as const,
  details: () => [...menuItemKeys.all, 'detail'] as const,
  detail: (id: string) => [...menuItemKeys.details(), id] as const,
}

export const priceKeys = {
  all: ['menu-prices'] as const,
  lists: () => [...priceKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) => [...priceKeys.lists(), params] as const,
  details: () => [...priceKeys.all, 'detail'] as const,
  detail: (id: string) => [...priceKeys.details(), id] as const,
}

export const availabilityKeys = {
  all: ['menu-availability'] as const,
  lists: () => [...availabilityKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) => [...availabilityKeys.lists(), params] as const,
  details: () => [...availabilityKeys.all, 'detail'] as const,
  detail: (id: string) => [...availabilityKeys.details(), id] as const,
}

export const catalogKeys = {
  all: ['branch-catalog'] as const,
  branch: (branchId: string) => [...catalogKeys.all, branchId] as const,
}

export const menuDashboardKeys = {
  all: ['menu-dashboard'] as const,
}

// ---------------------------------------------------------------------------
// Tax Rate hooks
// ---------------------------------------------------------------------------

export function useTaxRates(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<TaxRate>, Error>({
    queryKey: taxRateKeys.list(params),
    queryFn: () => listTaxRates(params),
  })
}

export function useTaxRate(id: string) {
  return useQuery<TaxRate, Error>({
    queryKey: taxRateKeys.detail(id),
    queryFn: () => getTaxRate(id),
    enabled: !!id,
  })
}

export function useCreateTaxRate() {
  const qc = useQueryClient()
  return useMutation<TaxRate, Error, TaxRateCreatePayload>({
    mutationFn: createTaxRate,
    onSuccess: () => qc.invalidateQueries({ queryKey: taxRateKeys.lists() }),
  })
}

export function useUpdateTaxRate(id: string) {
  const qc = useQueryClient()
  return useMutation<TaxRate, Error, TaxRateUpdatePayload>({
    mutationFn: (data) => updateTaxRate(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: taxRateKeys.detail(id) })
      qc.invalidateQueries({ queryKey: taxRateKeys.lists() })
    },
  })
}

export function useDisableTaxRate() {
  const qc = useQueryClient()
  return useMutation<TaxRate, Error, string>({
    mutationFn: disableTaxRate,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: taxRateKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: taxRateKeys.lists() })
    },
  })
}

export function useEnableTaxRate() {
  const qc = useQueryClient()
  return useMutation<TaxRate, Error, string>({
    mutationFn: enableTaxRate,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: taxRateKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: taxRateKeys.lists() })
    },
  })
}

// ---------------------------------------------------------------------------
// Category hooks
// ---------------------------------------------------------------------------

export function useCategories(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<Category>, Error>({
    queryKey: categoryKeys.list(params),
    queryFn: () => listCategories(params),
  })
}

export function useCategory(id: string) {
  return useQuery<Category, Error>({
    queryKey: categoryKeys.detail(id),
    queryFn: () => getCategory(id),
    enabled: !!id,
  })
}

export function useCreateCategory() {
  const qc = useQueryClient()
  return useMutation<Category, Error, CategoryCreatePayload>({
    mutationFn: createCategory,
    onSuccess: () => qc.invalidateQueries({ queryKey: categoryKeys.lists() }),
  })
}

export function useUpdateCategory(id: string) {
  const qc = useQueryClient()
  return useMutation<Category, Error, CategoryUpdatePayload>({
    mutationFn: (data) => updateCategory(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: categoryKeys.detail(id) })
      qc.invalidateQueries({ queryKey: categoryKeys.lists() })
    },
  })
}

export function useDisableCategory() {
  const qc = useQueryClient()
  return useMutation<Category, Error, string>({
    mutationFn: disableCategory,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: categoryKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: categoryKeys.lists() })
    },
  })
}

export function useEnableCategory() {
  const qc = useQueryClient()
  return useMutation<Category, Error, string>({
    mutationFn: enableCategory,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: categoryKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: categoryKeys.lists() })
    },
  })
}

// ---------------------------------------------------------------------------
// MenuItem hooks
// ---------------------------------------------------------------------------

export function useMenuItems(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<MenuItem>, Error>({
    queryKey: menuItemKeys.list(params),
    queryFn: () => listMenuItems(params),
  })
}

export function useMenuItem(id: string) {
  return useQuery<MenuItemDetail, Error>({
    queryKey: menuItemKeys.detail(id),
    queryFn: () => getMenuItem(id),
    enabled: !!id,
  })
}

export function useCreateMenuItem() {
  const qc = useQueryClient()
  return useMutation<MenuItem, Error, MenuItemCreatePayload>({
    mutationFn: createMenuItem,
    onSuccess: () => qc.invalidateQueries({ queryKey: menuItemKeys.lists() }),
  })
}

export function useUpdateMenuItem(id: string) {
  const qc = useQueryClient()
  return useMutation<MenuItem, Error, MenuItemUpdatePayload>({
    mutationFn: (data) => updateMenuItem(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: menuItemKeys.detail(id) })
      qc.invalidateQueries({ queryKey: menuItemKeys.lists() })
    },
  })
}

export function useDisableMenuItem() {
  const qc = useQueryClient()
  return useMutation<MenuItem, Error, string>({
    mutationFn: disableMenuItem,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: menuItemKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: menuItemKeys.lists() })
    },
  })
}

export function useEnableMenuItem() {
  const qc = useQueryClient()
  return useMutation<MenuItem, Error, string>({
    mutationFn: enableMenuItem,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: menuItemKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: menuItemKeys.lists() })
    },
  })
}

// ---------------------------------------------------------------------------
// Price hooks
// ---------------------------------------------------------------------------

export function usePrices(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<MenuItemPrice>, Error>({
    queryKey: priceKeys.list(params),
    queryFn: () => listPrices(params),
  })
}

export function usePrice(id: string) {
  return useQuery<MenuItemPrice, Error>({
    queryKey: priceKeys.detail(id),
    queryFn: () => getPrice(id),
    enabled: !!id,
  })
}

export function useCreatePrice() {
  const qc = useQueryClient()
  return useMutation<MenuItemPrice, Error, MenuItemPriceCreatePayload>({
    mutationFn: createPrice,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: priceKeys.lists() })
      qc.invalidateQueries({ queryKey: menuItemKeys.all })
    },
  })
}

export function useUpdatePrice(id: string) {
  const qc = useQueryClient()
  return useMutation<MenuItemPrice, Error, MenuItemPriceUpdatePayload>({
    mutationFn: (data) => updatePrice(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: priceKeys.detail(id) })
      qc.invalidateQueries({ queryKey: priceKeys.lists() })
      qc.invalidateQueries({ queryKey: menuItemKeys.all })
    },
  })
}

export function useDeactivatePrice() {
  const qc = useQueryClient()
  return useMutation<MenuItemPrice, Error, string>({
    mutationFn: deactivatePrice,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: priceKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: priceKeys.lists() })
      qc.invalidateQueries({ queryKey: menuItemKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// Availability hooks
// ---------------------------------------------------------------------------

export function useAvailabilityList(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<MenuItemBranch>, Error>({
    queryKey: availabilityKeys.list(params),
    queryFn: () => listAvailability(params),
  })
}

export function useAvailability(id: string) {
  return useQuery<MenuItemBranch, Error>({
    queryKey: availabilityKeys.detail(id),
    queryFn: () => getAvailability(id),
    enabled: !!id,
  })
}

export function useCreateAvailability() {
  const qc = useQueryClient()
  return useMutation<MenuItemBranch, Error, MenuItemBranchCreatePayload>({
    mutationFn: createAvailability,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: availabilityKeys.lists() })
      qc.invalidateQueries({ queryKey: menuItemKeys.all })
    },
  })
}

export function useUpdateAvailability(id: string) {
  const qc = useQueryClient()
  return useMutation<MenuItemBranch, Error, MenuItemBranchUpdatePayload>({
    mutationFn: (data) => updateAvailability(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: availabilityKeys.detail(id) })
      qc.invalidateQueries({ queryKey: availabilityKeys.lists() })
      qc.invalidateQueries({ queryKey: menuItemKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// Catalog hook
// ---------------------------------------------------------------------------

export function useBranchCatalog(branchId: string) {
  return useQuery<BranchCatalog, Error>({
    queryKey: catalogKeys.branch(branchId),
    queryFn: () => getBranchCatalog(branchId),
    enabled: !!branchId,
  })
}

// ---------------------------------------------------------------------------
// Dashboard hook
// ---------------------------------------------------------------------------

export function useMenuDashboard() {
  return useQuery<MenuDashboardStats, Error>({
    queryKey: menuDashboardKeys.all,
    queryFn: getMenuDashboard,
  })
}
