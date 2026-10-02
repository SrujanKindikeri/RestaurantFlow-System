// =============================================================================
// RestaurantFlow — useRoles + usePermissions Hooks
// Phase 3
// =============================================================================

import { useQuery } from '@tanstack/react-query'
import { listRoles, getRole, listPermissions, type ListPermissionsParams } from '@/services/roles'

export function useRoles() {
  return useQuery({
    queryKey: ['roles', 'list'],
    queryFn: listRoles,
  })
}

export function useRole(id: string | undefined) {
  return useQuery({
    queryKey: ['roles', 'detail', id],
    queryFn: () => getRole(id!),
    enabled: !!id,
  })
}

export function usePermissions(params: ListPermissionsParams = {}) {
  return useQuery({
    queryKey: ['permissions', 'list', params],
    queryFn: () => listPermissions(params),
  })
}
