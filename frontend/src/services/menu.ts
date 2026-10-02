// =============================================================================
// RestaurantFlow — Menu API Service
// Phase 5
// =============================================================================

import { get, post, patch } from '@/services/api'
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

// ---------------------------------------------------------------------------
// Tax Rates
// ---------------------------------------------------------------------------

/** GET /api/menu/tax-rates/ */
export const listTaxRates = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<TaxRate>>('/menu/tax-rates/', { params })

/** GET /api/menu/tax-rates/:id/ */
export const getTaxRate = (id: string) =>
  get<TaxRate>(`/menu/tax-rates/${id}/`)

/** POST /api/menu/tax-rates/ */
export const createTaxRate = (data: TaxRateCreatePayload) =>
  post<TaxRate>('/menu/tax-rates/', data)

/** PATCH /api/menu/tax-rates/:id/ */
export const updateTaxRate = (id: string, data: TaxRateUpdatePayload) =>
  patch<TaxRate>(`/menu/tax-rates/${id}/`, data)

/** POST /api/menu/tax-rates/:id/disable/ */
export const disableTaxRate = (id: string) =>
  post<TaxRate>(`/menu/tax-rates/${id}/disable/`)

/** POST /api/menu/tax-rates/:id/enable/ */
export const enableTaxRate = (id: string) =>
  post<TaxRate>(`/menu/tax-rates/${id}/enable/`)

// ---------------------------------------------------------------------------
// Categories
// ---------------------------------------------------------------------------

/** GET /api/menu/categories/ */
export const listCategories = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<Category>>('/menu/categories/', { params })

/** GET /api/menu/categories/:id/ */
export const getCategory = (id: string) =>
  get<Category>(`/menu/categories/${id}/`)

/** POST /api/menu/categories/ */
export const createCategory = (data: CategoryCreatePayload) =>
  post<Category>('/menu/categories/', data)

/** PATCH /api/menu/categories/:id/ */
export const updateCategory = (id: string, data: CategoryUpdatePayload) =>
  patch<Category>(`/menu/categories/${id}/`, data)

/** POST /api/menu/categories/:id/disable/ */
export const disableCategory = (id: string) =>
  post<Category>(`/menu/categories/${id}/disable/`)

/** POST /api/menu/categories/:id/enable/ */
export const enableCategory = (id: string) =>
  post<Category>(`/menu/categories/${id}/enable/`)

// ---------------------------------------------------------------------------
// Menu Items
// ---------------------------------------------------------------------------

/** GET /api/menu/items/ */
export const listMenuItems = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<MenuItem>>('/menu/items/', { params })

/** GET /api/menu/items/:id/ */
export const getMenuItem = (id: string) =>
  get<MenuItemDetail>(`/menu/items/${id}/`)

/** POST /api/menu/items/ */
export const createMenuItem = (data: MenuItemCreatePayload) =>
  post<MenuItem>('/menu/items/', data)

/** PATCH /api/menu/items/:id/ */
export const updateMenuItem = (id: string, data: MenuItemUpdatePayload) =>
  patch<MenuItem>(`/menu/items/${id}/`, data)

/** POST /api/menu/items/:id/disable/ */
export const disableMenuItem = (id: string) =>
  post<MenuItem>(`/menu/items/${id}/disable/`)

/** POST /api/menu/items/:id/enable/ */
export const enableMenuItem = (id: string) =>
  post<MenuItem>(`/menu/items/${id}/enable/`)

// ---------------------------------------------------------------------------
// Prices
// ---------------------------------------------------------------------------

/** GET /api/menu/prices/ */
export const listPrices = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<MenuItemPrice>>('/menu/prices/', { params })

/** GET /api/menu/prices/:id/ */
export const getPrice = (id: string) =>
  get<MenuItemPrice>(`/menu/prices/${id}/`)

/** POST /api/menu/prices/ */
export const createPrice = (data: MenuItemPriceCreatePayload) =>
  post<MenuItemPrice>('/menu/prices/', data)

/** PATCH /api/menu/prices/:id/ */
export const updatePrice = (id: string, data: MenuItemPriceUpdatePayload) =>
  patch<MenuItemPrice>(`/menu/prices/${id}/`, data)

/** POST /api/menu/prices/:id/deactivate/ */
export const deactivatePrice = (id: string) =>
  post<MenuItemPrice>(`/menu/prices/${id}/deactivate/`)

// ---------------------------------------------------------------------------
// Branch Availability
// ---------------------------------------------------------------------------

/** GET /api/menu/availability/ */
export const listAvailability = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<MenuItemBranch>>('/menu/availability/', { params })

/** GET /api/menu/availability/:id/ */
export const getAvailability = (id: string) =>
  get<MenuItemBranch>(`/menu/availability/${id}/`)

/** POST /api/menu/availability/ */
export const createAvailability = (data: MenuItemBranchCreatePayload) =>
  post<MenuItemBranch>('/menu/availability/', data)

/** PATCH /api/menu/availability/:id/ */
export const updateAvailability = (id: string, data: MenuItemBranchUpdatePayload) =>
  patch<MenuItemBranch>(`/menu/availability/${id}/`, data)

// ---------------------------------------------------------------------------
// Branch Catalog
// ---------------------------------------------------------------------------

/** GET /api/menu/branches/:id/catalog/ */
export const getBranchCatalog = (branchId: string) =>
  get<BranchCatalog>(`/menu/branches/${branchId}/catalog/`)

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

/** GET /api/menu/dashboard/ */
export const getMenuDashboard = () =>
  get<MenuDashboardStats>('/menu/dashboard/')
