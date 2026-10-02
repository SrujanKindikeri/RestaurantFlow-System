// =============================================================================
// RestaurantFlow — useHealth Hook
// =============================================================================

import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '@/services/health'
import type { HealthCheckResponse } from '@/types'

export const HEALTH_QUERY_KEY = ['health'] as const

export function useHealth() {
  return useQuery<HealthCheckResponse, Error>({
    queryKey: HEALTH_QUERY_KEY,
    queryFn: fetchHealth,
    // Refetch every 30 seconds to keep status live
    refetchInterval: 30 * 1000,
    // Don't fail silently — surface errors to the UI
    retry: 2,
  })
}
