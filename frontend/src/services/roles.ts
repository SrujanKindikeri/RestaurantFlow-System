// =============================================================================
// RestaurantFlow — Roles & Permissions Service
// Phase 3
// =============================================================================

import { get } from './api'
import type { PaginatedResponse, Role, Permission } from '@/types'

export async function listRoles(): Promise<PaginatedResponse<Role>> {
  return get<PaginatedResponse<Role>>('/roles/')
}

export async function getRole(id: string): Promise<Role> {
  return get<Role>(`/roles/${id}/`)
}

export interface ListPermissionsParams {
  module?: string
}

export async function listPermissions(
  params: ListPermissionsParams = {},
): Promise<PaginatedResponse<Permission>> {
  return get<PaginatedResponse<Permission>>('/permissions/', { params })
}
