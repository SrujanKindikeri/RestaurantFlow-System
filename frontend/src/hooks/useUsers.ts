// =============================================================================
// RestaurantFlow — useUsers Hooks
// Phase 3
// =============================================================================

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  listUsers,
  getUser,
  createUser,
  updateUser,
  disableUser,
  reactivateUser,
  assignRole,
  disableRoleAssignment,
  type ListUsersParams,
} from '@/services/users'
import type { UserCreatePayload, UserUpdatePayload, UserRoleAssignmentCreatePayload } from '@/types'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const keys = {
  all: ['users'] as const,
  list: (params: ListUsersParams) => ['users', 'list', params] as const,
  detail: (id: number) => ['users', 'detail', id] as const,
}

// ---------------------------------------------------------------------------
// Queries
// ---------------------------------------------------------------------------

export function useUsers(params: ListUsersParams = {}) {
  return useQuery({
    queryKey: keys.list(params),
    queryFn: () => listUsers(params),
  })
}

export function useUser(id: number | undefined) {
  return useQuery({
    queryKey: keys.detail(id!),
    queryFn: () => getUser(id!),
    enabled: !!id,
  })
}

// ---------------------------------------------------------------------------
// Mutations
// ---------------------------------------------------------------------------

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UserCreatePayload) => createUser(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.all })
    },
  })
}

export function useUpdateUser(id: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UserUpdatePayload) => updateUser(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(id) })
      qc.invalidateQueries({ queryKey: keys.all })
    },
  })
}

export function useDisableUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => disableUser(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.all })
    },
  })
}

export function useReactivateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => reactivateUser(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.all })
    },
  })
}

export function useAssignRole(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UserRoleAssignmentCreatePayload) => assignRole(userId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(userId) })
      qc.invalidateQueries({ queryKey: keys.all })
    },
  })
}

export function useDisableRoleAssignment(userId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (assignmentId: string) => disableRoleAssignment(assignmentId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.detail(userId) })
    },
  })
}
