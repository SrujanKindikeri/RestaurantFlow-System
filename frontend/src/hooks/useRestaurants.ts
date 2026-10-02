// =============================================================================
// RestaurantFlow — Restaurant Hooks
// Phase 2
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  Restaurant,
  RestaurantDetail,
  RestaurantCreatePayload,
  RestaurantUpdatePayload,
  PaginatedResponse,
} from '@/types'
import {
  listRestaurantsByOrg,
  listAllRestaurants,
  getRestaurant,
  createRestaurant,
  updateRestaurant,
  disableRestaurant,
  reactivateRestaurant,
} from '@/services/restaurants'
import { organizationKeys } from '@/hooks/useOrganizations'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const restaurantKeys = {
  all: ['restaurants'] as const,
  lists: () => [...restaurantKeys.all, 'list'] as const,
  listAll: (params?: Record<string, string | number>) =>
    [...restaurantKeys.lists(), 'all', params] as const,
  listByOrg: (orgId: string) =>
    [...restaurantKeys.lists(), 'org', orgId] as const,
  details: () => [...restaurantKeys.all, 'detail'] as const,
  detail: (id: string) => [...restaurantKeys.details(), id] as const,
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useRestaurantsByOrg(orgId: string) {
  return useQuery<PaginatedResponse<Restaurant>, Error>({
    queryKey: restaurantKeys.listByOrg(orgId),
    queryFn: () => listRestaurantsByOrg(orgId),
    enabled: !!orgId,
  })
}

export function useAllRestaurants(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<Restaurant>, Error>({
    queryKey: restaurantKeys.listAll(params),
    queryFn: () => listAllRestaurants(params),
  })
}

export function useRestaurant(id: string) {
  return useQuery<RestaurantDetail, Error>({
    queryKey: restaurantKeys.detail(id),
    queryFn: () => getRestaurant(id),
    enabled: !!id,
  })
}

export function useCreateRestaurant(orgId: string) {
  const qc = useQueryClient()
  return useMutation<Restaurant, Error, RestaurantCreatePayload>({
    mutationFn: (data) => createRestaurant(orgId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: restaurantKeys.listByOrg(orgId) })
      qc.invalidateQueries({ queryKey: restaurantKeys.lists() })
      qc.invalidateQueries({ queryKey: organizationKeys.detail(orgId) })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useUpdateRestaurant(id: string) {
  const qc = useQueryClient()
  return useMutation<Restaurant, Error, RestaurantUpdatePayload>({
    mutationFn: (data) => updateRestaurant(id, data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: restaurantKeys.detail(id) })
      qc.invalidateQueries({ queryKey: restaurantKeys.lists() })
      qc.invalidateQueries({
        queryKey: organizationKeys.detail(data.organization),
      })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useDisableRestaurant() {
  const qc = useQueryClient()
  return useMutation<Restaurant, Error, string>({
    mutationFn: disableRestaurant,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: restaurantKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: restaurantKeys.lists() })
      qc.invalidateQueries({
        queryKey: organizationKeys.detail(data.organization),
      })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useReactivateRestaurant() {
  const qc = useQueryClient()
  return useMutation<Restaurant, Error, string>({
    mutationFn: reactivateRestaurant,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: restaurantKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: restaurantKeys.lists() })
      qc.invalidateQueries({
        queryKey: organizationKeys.detail(data.organization),
      })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}
