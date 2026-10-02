// =============================================================================
// RestaurantFlow — Branch API Service
// Phase 2
// =============================================================================

import { get, post, patch } from '@/services/api'
import type {
  Branch,
  BranchDetail,
  BranchSettings,
  BranchCreatePayload,
  BranchUpdatePayload,
  PaginatedResponse,
} from '@/types'

// ---------------------------------------------------------------------------
// Branches nested under a Restaurant
// ---------------------------------------------------------------------------

/** GET /api/restaurants/:restaurantId/branches/ */
export const listBranchesByRestaurant = (
  restaurantId: string,
  params?: Record<string, string | number>,
) =>
  get<PaginatedResponse<Branch>>(
    `/restaurants/${restaurantId}/branches/`,
    { params },
  )

/** POST /api/restaurants/:restaurantId/branches/ */
export const createBranch = (
  restaurantId: string,
  data: BranchCreatePayload,
) => post<Branch>(`/restaurants/${restaurantId}/branches/`, data)

// ---------------------------------------------------------------------------
// Branches standalone
// ---------------------------------------------------------------------------

/** GET /api/branches/ */
export const listAllBranches = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<Branch>>('/branches/', { params })

/** GET /api/branches/:id/ */
export const getBranch = (id: string) =>
  get<BranchDetail>(`/branches/${id}/`)

/** PATCH /api/branches/:id/ */
export const updateBranch = (id: string, data: BranchUpdatePayload) =>
  patch<Branch>(`/branches/${id}/`, data)

/** Soft-disable */
export const disableBranch = (id: string) =>
  patch<Branch>(`/branches/${id}/`, { is_active: false })

/** Reactivate */
export const reactivateBranch = (id: string) =>
  patch<Branch>(`/branches/${id}/`, { is_active: true })

// ---------------------------------------------------------------------------
// Branch Settings
// ---------------------------------------------------------------------------

/** GET /api/branches/:id/settings/ */
export const getBranchSettings = (branchId: string) =>
  get<BranchSettings>(`/branches/${branchId}/settings/`)

/** PATCH /api/branches/:id/settings/ */
export const updateBranchSettings = (
  branchId: string,
  data: Partial<BranchSettings>,
) => patch<BranchSettings>(`/branches/${branchId}/settings/`, data)
