// =============================================================================
// RestaurantFlow — Branch Hooks
// Phase 2
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  Branch,
  BranchDetail,
  BranchCreatePayload,
  BranchUpdatePayload,
  PaginatedResponse,
} from '@/types'
import {
  listBranchesByRestaurant,
  listAllBranches,
  getBranch,
  createBranch,
  updateBranch,
  disableBranch,
  reactivateBranch,
} from '@/services/branches'
import { restaurantKeys } from '@/hooks/useRestaurants'
import { organizationKeys } from '@/hooks/useOrganizations'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const branchKeys = {
  all: ['branches'] as const,
  lists: () => [...branchKeys.all, 'list'] as const,
  listAll: (params?: Record<string, string | number>) =>
    [...branchKeys.lists(), 'all', params] as const,
  listByRestaurant: (restaurantId: string) =>
    [...branchKeys.lists(), 'restaurant', restaurantId] as const,
  details: () => [...branchKeys.all, 'detail'] as const,
  detail: (id: string) => [...branchKeys.details(), id] as const,
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useBranchesByRestaurant(restaurantId: string) {
  return useQuery<PaginatedResponse<Branch>, Error>({
    queryKey: branchKeys.listByRestaurant(restaurantId),
    queryFn: () => listBranchesByRestaurant(restaurantId),
    enabled: !!restaurantId,
  })
}

export function useAllBranches(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<Branch>, Error>({
    queryKey: branchKeys.listAll(params),
    queryFn: () => listAllBranches(params),
  })
}

export function useBranch(id: string) {
  return useQuery<BranchDetail, Error>({
    queryKey: branchKeys.detail(id),
    queryFn: () => getBranch(id),
    enabled: !!id,
  })
}

export function useCreateBranch(restaurantId: string) {
  const qc = useQueryClient()
  return useMutation<Branch, Error, BranchCreatePayload>({
    mutationFn: (data) => createBranch(restaurantId, data),
    onSuccess: (data) => {
      qc.invalidateQueries({
        queryKey: branchKeys.listByRestaurant(restaurantId),
      })
      qc.invalidateQueries({ queryKey: branchKeys.lists() })
      qc.invalidateQueries({
        queryKey: restaurantKeys.detail(restaurantId),
      })
      qc.invalidateQueries({
        queryKey: organizationKeys.detail(data.organization_id),
      })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useUpdateBranch(id: string) {
  const qc = useQueryClient()
  return useMutation<Branch, Error, BranchUpdatePayload>({
    mutationFn: (data) => updateBranch(id, data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: branchKeys.detail(id) })
      qc.invalidateQueries({ queryKey: branchKeys.lists() })
      qc.invalidateQueries({
        queryKey: restaurantKeys.detail(data.restaurant),
      })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useDisableBranch() {
  const qc = useQueryClient()
  return useMutation<Branch, Error, string>({
    mutationFn: disableBranch,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: branchKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: branchKeys.lists() })
      qc.invalidateQueries({
        queryKey: restaurantKeys.detail(data.restaurant),
      })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useReactivateBranch() {
  const qc = useQueryClient()
  return useMutation<Branch, Error, string>({
    mutationFn: reactivateBranch,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: branchKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: branchKeys.lists() })
      qc.invalidateQueries({
        queryKey: restaurantKeys.detail(data.restaurant),
      })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}
