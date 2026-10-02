// =============================================================================
// RestaurantFlow — Organization API Service
// Phase 2
//
// All calls go through the centralised Axios instance in api.ts which
// handles JWT attachment and token refresh automatically.
// =============================================================================

import { get, post, patch } from '@/services/api'
import type {
  Organization,
  OrganizationDetail,
  OrganizationCreatePayload,
  OrganizationUpdatePayload,
  OrganizationStats,
  PaginatedResponse,
} from '@/types'

const BASE = '/organizations'

// ---------------------------------------------------------------------------
// Organizations
// ---------------------------------------------------------------------------

/** GET /api/organizations/ */
export const listOrganizations = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<Organization>>(BASE + '/', { params })

/** GET /api/organizations/stats/ */
export const fetchOrganizationStats = () =>
  get<OrganizationStats>(`${BASE}/stats/`)

/** GET /api/organizations/:id/ */
export const getOrganization = (id: string) =>
  get<OrganizationDetail>(`${BASE}/${id}/`)

/** POST /api/organizations/ */
export const createOrganization = (data: OrganizationCreatePayload) =>
  post<Organization>(BASE + '/', data)

/** PATCH /api/organizations/:id/ */
export const updateOrganization = (id: string, data: OrganizationUpdatePayload) =>
  patch<Organization>(`${BASE}/${id}/`, data)

/** Soft-disable: PATCH is_active = false */
export const disableOrganization = (id: string) =>
  patch<Organization>(`${BASE}/${id}/`, { is_active: false })

/** Reactivate: PATCH is_active = true */
export const reactivateOrganization = (id: string) =>
  patch<Organization>(`${BASE}/${id}/`, { is_active: true })
