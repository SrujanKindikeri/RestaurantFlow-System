// =============================================================================
// RestaurantFlow — Health Service
// =============================================================================

import { get } from './api'
import type { HealthCheckResponse } from '@/types'

/**
 * Call GET /api/health/ to check backend connectivity.
 */
export const fetchHealth = (): Promise<HealthCheckResponse> => get<HealthCheckResponse>('/health/')
