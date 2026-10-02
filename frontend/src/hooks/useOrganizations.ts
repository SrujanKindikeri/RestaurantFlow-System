// =============================================================================
// RestaurantFlow — Organization Hooks
// Phase 2
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  Organization,
  OrganizationDetail,
  OrganizationCreatePayload,
  OrganizationUpdatePayload,
  OrganizationStats,
  PaginatedResponse,
} from '@/types'
import {
  listOrganizations,
  fetchOrganizationStats,
  getOrganization,
  createOrganization,
  updateOrganization,
  disableOrganization,
  reactivateOrganization,
} from '@/services/organizations'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const organizationKeys = {
  all: ['organizations'] as const,
  lists: () => [...organizationKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) =>
    [...organizationKeys.lists(), params] as const,
  details: () => [...organizationKeys.all, 'detail'] as const,
  detail: (id: string) => [...organizationKeys.details(), id] as const,
  stats: () => [...organizationKeys.all, 'stats'] as const,
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useOrganizations(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<Organization>, Error>({
    queryKey: organizationKeys.list(params),
    queryFn: () => listOrganizations(params),
  })
}

export function useOrganizationStats() {
  return useQuery<OrganizationStats, Error>({
    queryKey: organizationKeys.stats(),
    queryFn: fetchOrganizationStats,
    staleTime: 30_000,
  })
}

export function useOrganization(id: string) {
  return useQuery<OrganizationDetail, Error>({
    queryKey: organizationKeys.detail(id),
    queryFn: () => getOrganization(id),
    enabled: !!id,
  })
}

export function useCreateOrganization() {
  const qc = useQueryClient()
  return useMutation<Organization, Error, OrganizationCreatePayload>({
    mutationFn: createOrganization,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: organizationKeys.lists() })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useUpdateOrganization(id: string) {
  const qc = useQueryClient()
  return useMutation<Organization, Error, OrganizationUpdatePayload>({
    mutationFn: (data) => updateOrganization(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: organizationKeys.detail(id) })
      qc.invalidateQueries({ queryKey: organizationKeys.lists() })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useDisableOrganization() {
  const qc = useQueryClient()
  return useMutation<Organization, Error, string>({
    mutationFn: disableOrganization,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: organizationKeys.detail(id) })
      qc.invalidateQueries({ queryKey: organizationKeys.lists() })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}

export function useReactivateOrganization() {
  const qc = useQueryClient()
  return useMutation<Organization, Error, string>({
    mutationFn: reactivateOrganization,
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: organizationKeys.detail(id) })
      qc.invalidateQueries({ queryKey: organizationKeys.lists() })
      qc.invalidateQueries({ queryKey: organizationKeys.stats() })
    },
  })
}
