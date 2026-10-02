// =============================================================================
// RestaurantFlow — Users Service
// Phase 3
// =============================================================================

import { get, post, patch } from './api'
import type {
  PaginatedResponse,
  User,
  UserDetail,
  UserCreatePayload,
  UserUpdatePayload,
  UserRoleAssignment,
  UserRoleAssignmentCreatePayload,
} from '@/types'

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export interface ListUsersParams {
  page?: number
  search?: string
}

export async function listUsers(params: ListUsersParams = {}): Promise<PaginatedResponse<User>> {
  return get<PaginatedResponse<User>>('/users/', { params })
}

export async function getUser(id: number): Promise<UserDetail> {
  return get<UserDetail>(`/users/${id}/`)
}

export async function createUser(data: UserCreatePayload): Promise<User> {
  return post<User>('/users/', data)
}

export async function updateUser(id: number, data: UserUpdatePayload): Promise<UserDetail> {
  return patch<UserDetail>(`/users/${id}/`, data)
}

export async function disableUser(id: number): Promise<{ detail: string }> {
  return post<{ detail: string }>(`/users/${id}/disable/`)
}

export async function reactivateUser(id: number): Promise<{ detail: string }> {
  return post<{ detail: string }>(`/users/${id}/reactivate/`)
}

// ---------------------------------------------------------------------------
// Role assignments
// ---------------------------------------------------------------------------

export async function listUserRoles(userId: number): Promise<PaginatedResponse<UserRoleAssignment>> {
  return get<PaginatedResponse<UserRoleAssignment>>(`/users/${userId}/roles/`)
}

export async function assignRole(
  userId: number,
  data: UserRoleAssignmentCreatePayload,
): Promise<UserRoleAssignment> {
  return post<UserRoleAssignment>(`/users/${userId}/roles/`, data)
}

export async function disableRoleAssignment(assignmentId: string): Promise<{ detail: string }> {
  return post<{ detail: string }>(`/user-role-assignments/${assignmentId}/disable/`)
}
