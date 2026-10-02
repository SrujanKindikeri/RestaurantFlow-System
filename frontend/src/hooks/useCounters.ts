// =============================================================================
// RestaurantFlow — Counter Hooks
// Phase 4
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import type {
  Counter,
  CounterDetail,
  CounterCreatePayload,
  CounterUpdatePayload,
  CounterAssignment,
  CounterAssignmentCreatePayload,
  CounterSession,
  OpenSessionPayload,
  CloseSessionPayload,
  ForceCloseSessionPayload,
  Shift,
  ShiftCreatePayload,
  CounterDashboardResponse,
  PaginatedResponse,
} from '@/types'
import {
  listCounters,
  getCounter,
  createCounter,
  updateCounter,
  disableCounter,
  reactivateCounter,
  listSessions,
  getSession,
  openSession,
  closeSession,
  forceCloseSession,
  listAssignments,
  createAssignment,
  deactivateAssignment,
  listShifts,
  createShift,
  getCounterDashboard,
} from '@/services/counters'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

export const counterKeys = {
  all: ['counters'] as const,
  lists: () => [...counterKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) =>
    [...counterKeys.lists(), params] as const,
  details: () => [...counterKeys.all, 'detail'] as const,
  detail: (id: string) => [...counterKeys.details(), id] as const,
  dashboard: (branchId?: string) =>
    [...counterKeys.all, 'dashboard', branchId] as const,
}

export const sessionKeys = {
  all: ['counter-sessions'] as const,
  lists: () => [...sessionKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) =>
    [...sessionKeys.lists(), params] as const,
  details: () => [...sessionKeys.all, 'detail'] as const,
  detail: (id: string) => [...sessionKeys.details(), id] as const,
}

export const assignmentKeys = {
  all: ['counter-assignments'] as const,
  lists: () => [...assignmentKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) =>
    [...assignmentKeys.lists(), params] as const,
  detail: (id: string) => [...assignmentKeys.all, 'detail', id] as const,
}

export const shiftKeys = {
  all: ['shifts'] as const,
  lists: () => [...shiftKeys.all, 'list'] as const,
  list: (params?: Record<string, string | number>) =>
    [...shiftKeys.lists(), params] as const,
}

// ---------------------------------------------------------------------------
// Counter hooks
// ---------------------------------------------------------------------------

export function useCounters(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<Counter>, Error>({
    queryKey: counterKeys.list(params),
    queryFn: () => listCounters(params),
  })
}

export function useCounter(id: string) {
  return useQuery<CounterDetail, Error>({
    queryKey: counterKeys.detail(id),
    queryFn: () => getCounter(id),
    enabled: !!id,
  })
}

export function useCounterDashboard(branchId?: string) {
  return useQuery<CounterDashboardResponse, Error>({
    queryKey: counterKeys.dashboard(branchId),
    queryFn: () => getCounterDashboard(branchId),
    refetchInterval: 30_000, // refresh every 30s for live status
  })
}

export function useCreateCounter() {
  const qc = useQueryClient()
  return useMutation<Counter, Error, CounterCreatePayload>({
    mutationFn: createCounter,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: counterKeys.lists() })
      qc.invalidateQueries({ queryKey: counterKeys.all })
    },
  })
}

export function useUpdateCounter(id: string) {
  const qc = useQueryClient()
  return useMutation<Counter, Error, CounterUpdatePayload>({
    mutationFn: (data) => updateCounter(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: counterKeys.detail(id) })
      qc.invalidateQueries({ queryKey: counterKeys.lists() })
    },
  })
}

export function useDisableCounter() {
  const qc = useQueryClient()
  return useMutation<Counter, Error, string>({
    mutationFn: disableCounter,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: counterKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: counterKeys.lists() })
      qc.invalidateQueries({ queryKey: counterKeys.all })
    },
  })
}

export function useReactivateCounter() {
  const qc = useQueryClient()
  return useMutation<Counter, Error, string>({
    mutationFn: reactivateCounter,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: counterKeys.detail(data.id) })
      qc.invalidateQueries({ queryKey: counterKeys.lists() })
      qc.invalidateQueries({ queryKey: counterKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// Session hooks
// ---------------------------------------------------------------------------

export function useSessions(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<CounterSession>, Error>({
    queryKey: sessionKeys.list(params),
    queryFn: () => listSessions(params),
  })
}

export function useSession(id: string) {
  return useQuery<CounterSession, Error>({
    queryKey: sessionKeys.detail(id),
    queryFn: () => getSession(id),
    enabled: !!id,
  })
}

export function useOpenSession(counterId: string) {
  const qc = useQueryClient()
  return useMutation<CounterSession, Error, OpenSessionPayload>({
    mutationFn: (data) => openSession(counterId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: counterKeys.detail(counterId) })
      qc.invalidateQueries({ queryKey: counterKeys.all })
      qc.invalidateQueries({ queryKey: sessionKeys.lists() })
    },
  })
}

export function useCloseSession(sessionId: string) {
  const qc = useQueryClient()
  return useMutation<CounterSession, Error, CloseSessionPayload>({
    mutationFn: (data) => closeSession(sessionId, data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: sessionKeys.detail(sessionId) })
      qc.invalidateQueries({ queryKey: sessionKeys.lists() })
      qc.invalidateQueries({ queryKey: counterKeys.detail(data.counter) })
      qc.invalidateQueries({ queryKey: counterKeys.all })
    },
  })
}

export function useForceCloseSession(sessionId: string) {
  const qc = useQueryClient()
  return useMutation<CounterSession, Error, ForceCloseSessionPayload>({
    mutationFn: (data) => forceCloseSession(sessionId, data),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: sessionKeys.detail(sessionId) })
      qc.invalidateQueries({ queryKey: sessionKeys.lists() })
      qc.invalidateQueries({ queryKey: counterKeys.detail(data.counter) })
      qc.invalidateQueries({ queryKey: counterKeys.all })
    },
  })
}

// ---------------------------------------------------------------------------
// Assignment hooks
// ---------------------------------------------------------------------------

export function useAssignments(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<CounterAssignment>, Error>({
    queryKey: assignmentKeys.list(params),
    queryFn: () => listAssignments(params),
  })
}

export function useCreateAssignment() {
  const qc = useQueryClient()
  return useMutation<CounterAssignment, Error, CounterAssignmentCreatePayload>({
    mutationFn: createAssignment,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: assignmentKeys.lists() })
      qc.invalidateQueries({ queryKey: counterKeys.detail(data.counter) })
    },
  })
}

export function useDeactivateAssignment() {
  const qc = useQueryClient()
  return useMutation<CounterAssignment, Error, string>({
    mutationFn: deactivateAssignment,
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: assignmentKeys.lists() })
      qc.invalidateQueries({ queryKey: counterKeys.detail(data.counter) })
    },
  })
}

// ---------------------------------------------------------------------------
// Shift hooks
// ---------------------------------------------------------------------------

export function useShifts(params?: Record<string, string | number>) {
  return useQuery<PaginatedResponse<Shift>, Error>({
    queryKey: shiftKeys.list(params),
    queryFn: () => listShifts(params),
  })
}

export function useCreateShift() {
  const qc = useQueryClient()
  return useMutation<Shift, Error, ShiftCreatePayload>({
    mutationFn: createShift,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: shiftKeys.lists() })
    },
  })
}
