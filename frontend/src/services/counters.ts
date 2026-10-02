// =============================================================================
// RestaurantFlow — Counter API Service
// Phase 4
// =============================================================================

import { get, post, patch } from '@/services/api'
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

// ---------------------------------------------------------------------------
// Counters
// ---------------------------------------------------------------------------

/** GET /api/counters/ */
export const listCounters = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<Counter>>('/counters/', { params })

/** GET /api/counters/:id/ */
export const getCounter = (id: string) =>
  get<CounterDetail>(`/counters/${id}/`)

/** POST /api/counters/ */
export const createCounter = (data: CounterCreatePayload) =>
  post<Counter>('/counters/', data)

/** PATCH /api/counters/:id/ */
export const updateCounter = (id: string, data: CounterUpdatePayload) =>
  patch<Counter>(`/counters/${id}/`, data)

/** POST /api/counters/:id/disable/ */
export const disableCounter = (id: string) =>
  post<Counter>(`/counters/${id}/disable/`)

/** POST /api/counters/:id/reactivate/ */
export const reactivateCounter = (id: string) =>
  post<Counter>(`/counters/${id}/reactivate/`)

// ---------------------------------------------------------------------------
// Counter Sessions
// ---------------------------------------------------------------------------

/** GET /api/counter-sessions/ */
export const listSessions = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<CounterSession>>('/counter-sessions/', { params })

/** GET /api/counter-sessions/:id/ */
export const getSession = (id: string) =>
  get<CounterSession>(`/counter-sessions/${id}/`)

/** POST /api/counters/:id/sessions/open/ */
export const openSession = (counterId: string, data: OpenSessionPayload) =>
  post<CounterSession>(`/counters/${counterId}/sessions/open/`, data)

/** POST /api/counter-sessions/:id/close/ */
export const closeSession = (sessionId: string, data: CloseSessionPayload) =>
  post<CounterSession>(`/counter-sessions/${sessionId}/close/`, data)

/** POST /api/counter-sessions/:id/force-close/ */
export const forceCloseSession = (sessionId: string, data: ForceCloseSessionPayload) =>
  post<CounterSession>(`/counter-sessions/${sessionId}/force-close/`, data)

// ---------------------------------------------------------------------------
// Counter Assignments
// ---------------------------------------------------------------------------

/** GET /api/counter-assignments/ */
export const listAssignments = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<CounterAssignment>>('/counter-assignments/', { params })

/** POST /api/counter-assignments/ */
export const createAssignment = (data: CounterAssignmentCreatePayload) =>
  post<CounterAssignment>('/counter-assignments/', data)

/** PATCH /api/counter-assignments/:id/ */
export const updateAssignment = (id: string, data: Partial<CounterAssignmentCreatePayload>) =>
  patch<CounterAssignment>(`/counter-assignments/${id}/`, data)

/** POST /api/counter-assignments/:id/deactivate/ */
export const deactivateAssignment = (id: string) =>
  post<CounterAssignment>(`/counter-assignments/${id}/deactivate/`)

// ---------------------------------------------------------------------------
// Shifts
// ---------------------------------------------------------------------------

/** GET /api/shifts/ */
export const listShifts = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<Shift>>('/shifts/', { params })

/** POST /api/shifts/ */
export const createShift = (data: ShiftCreatePayload) =>
  post<Shift>('/shifts/', data)

/** PATCH /api/shifts/:id/ */
export const updateShift = (id: string, data: Partial<ShiftCreatePayload>) =>
  patch<Shift>(`/shifts/${id}/`, data)

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

/** GET /api/counter-dashboard/?branch=<uuid> */
export const getCounterDashboard = (branchId?: string) =>
  get<CounterDashboardResponse>('/counter-dashboard/', {
    params: branchId ? { branch: branchId } : undefined,
  })
