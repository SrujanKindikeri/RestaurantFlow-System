// =============================================================================
// RestaurantFlow — Restaurant API Service
// Phase 2
// =============================================================================

import { get, post, patch } from '@/services/api'
import type {
  Restaurant,
  RestaurantDetail,
  RestaurantSettings,
  RestaurantCreatePayload,
  RestaurantUpdatePayload,
  PaginatedResponse,
} from '@/types'

// ---------------------------------------------------------------------------
// Restaurants nested under an Organization
// ---------------------------------------------------------------------------

/** GET /api/organizations/:orgId/restaurants/ */
export const listRestaurantsByOrg = (
  orgId: string,
  params?: Record<string, string | number>,
) =>
  get<PaginatedResponse<Restaurant>>(`/organizations/${orgId}/restaurants/`, {
    params,
  })

/** POST /api/organizations/:orgId/restaurants/ */
export const createRestaurant = (
  orgId: string,
  data: RestaurantCreatePayload,
) => post<Restaurant>(`/organizations/${orgId}/restaurants/`, data)

// ---------------------------------------------------------------------------
// Restaurants standalone
// ---------------------------------------------------------------------------

/** GET /api/restaurants/ */
export const listAllRestaurants = (params?: Record<string, string | number>) =>
  get<PaginatedResponse<Restaurant>>('/restaurants/', { params })

/** GET /api/restaurants/:id/ */
export const getRestaurant = (id: string) =>
  get<RestaurantDetail>(`/restaurants/${id}/`)

/** PATCH /api/restaurants/:id/ */
export const updateRestaurant = (id: string, data: RestaurantUpdatePayload) =>
  patch<Restaurant>(`/restaurants/${id}/`, data)

/** Soft-disable */
export const disableRestaurant = (id: string) =>
  patch<Restaurant>(`/restaurants/${id}/`, { is_active: false })

/** Reactivate */
export const reactivateRestaurant = (id: string) =>
  patch<Restaurant>(`/restaurants/${id}/`, { is_active: true })

// ---------------------------------------------------------------------------
// Restaurant Settings
// ---------------------------------------------------------------------------

/** GET /api/restaurants/:id/settings/ */
export const getRestaurantSettings = (restaurantId: string) =>
  get<RestaurantSettings>(`/restaurants/${restaurantId}/settings/`)

/** PATCH /api/restaurants/:id/settings/ */
export const updateRestaurantSettings = (
  restaurantId: string,
  data: Partial<RestaurantSettings>,
) => patch<RestaurantSettings>(`/restaurants/${restaurantId}/settings/`, data)
