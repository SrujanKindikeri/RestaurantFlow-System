// =============================================================================
// RestaurantFlow — Kitchen State Hook
// Phase 7
//
// Owns the kitchen orders state for the KDS.
// Combines:
//   - Initial REST fetch (useQuery)
//   - Live WebSocket updates (useKitchenWebSocket)
//   - Reconciliation after reconnect (REST sync)
//   - Action mutations (accept, start, ready, cancel, priority)
// =============================================================================

import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useKitchenWebSocket } from './useKitchenWebSocket'
import type {
  KitchenOrder,
  KitchenOrdersParams,
  KitchenEventMessage,
  KitchenSyncMessage,
} from '@/types'
import {
  listKitchenOrders,
  acceptKitchenOrder,
  startKitchenOrder,
  readyKitchenOrder,
  cancelKitchenOrder,
  updateKitchenPriority,
  startKitchenItem,
  readyKitchenItem,
  listKitchenHistory,
} from '@/services/kitchen'

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------
export const kitchenKeys = {
  all: ['kitchen'] as const,
  orders: (params?: KitchenOrdersParams) => ['kitchen', 'orders', params] as const,
  order: (id: string) => ['kitchen', 'order', id] as const,
  history: (params?: object) => ['kitchen', 'history', params] as const,
}

// ---------------------------------------------------------------------------
// useKitchenOrders — live KDS list with WebSocket sync
// ---------------------------------------------------------------------------
export function useKitchenOrders(params?: KitchenOrdersParams) {
  const qc = useQueryClient()
  const token = localStorage.getItem('access_token')

  // State: merged orders from REST + WebSocket
  const [liveOrders, setLiveOrders] = useState<KitchenOrder[]>([])
  const initializedRef = useRef(false)

  // Initial REST fetch
  const query = useQuery({
    queryKey: kitchenKeys.orders(params),
    queryFn: () => listKitchenOrders(params),
    refetchInterval: false, // WebSocket drives updates
    staleTime: 60_000,
  })

  // Populate live state from REST data on first load
  useEffect(() => {
    if (query.data?.results && !initializedRef.current) {
      setLiveOrders(query.data.results)
      initializedRef.current = true
    }
  }, [query.data])

  // Handle incoming WebSocket event
  const handleEvent = useCallback((msg: KitchenEventMessage) => {
    const payload = msg.payload
    setLiveOrders(prev => {
      const idx = prev.findIndex(o => o.id === payload.kitchen_order_id)
      if (idx === -1) {
        // New order arrived — trigger a REST refetch to get full data
        qc.invalidateQueries({ queryKey: kitchenKeys.orders(params) })
        return prev
      }
      // Update the existing order's status/priority
      const updated = [...prev]
      updated[idx] = {
        ...updated[idx],
        status: payload.status,
        priority: payload.priority,
      }
      return updated
    })
    // Invalidate the individual order cache too
    qc.invalidateQueries({ queryKey: kitchenKeys.order(payload.kitchen_order_id) })
  }, [qc, params])

  // Handle WebSocket sync (full state on reconnect)
  const handleSync = useCallback((msg: KitchenSyncMessage) => {
    setLiveOrders(msg.orders)
    // Sync local query cache
    qc.setQueryData(kitchenKeys.orders(params), {
      count: msg.orders.length,
      next: null,
      previous: null,
      results: msg.orders,
    })
  }, [qc, params])

  // Extract branchId from first order or query params
  const branchId = params?.branch ?? null

  const { status: wsStatus, requestSync } = useKitchenWebSocket({
    branchId,
    token,
    onEvent: handleEvent,
    onSync: handleSync,
    enabled: !!branchId,
  })

  return {
    orders: liveOrders,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
    wsStatus,
    requestSync,
  }
}

// ---------------------------------------------------------------------------
// useKitchenHistory
// ---------------------------------------------------------------------------
export function useKitchenHistory(params?: object) {
  return useQuery({
    queryKey: kitchenKeys.history(params),
    queryFn: () => listKitchenHistory(params),
    staleTime: 30_000,
  })
}

// ---------------------------------------------------------------------------
// Action mutations
// ---------------------------------------------------------------------------

export function useAcceptKitchenOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => acceptKitchenOrder(id),
    onSuccess: (data) => {
      qc.setQueryData(kitchenKeys.order(data.id), data)
      qc.invalidateQueries({ queryKey: kitchenKeys.all })
    },
  })
}

export function useStartKitchenOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => startKitchenOrder(id),
    onSuccess: (data) => {
      qc.setQueryData(kitchenKeys.order(data.id), data)
      qc.invalidateQueries({ queryKey: kitchenKeys.all })
    },
  })
}

export function useReadyKitchenOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => readyKitchenOrder(id),
    onSuccess: (data) => {
      qc.setQueryData(kitchenKeys.order(data.id), data)
      qc.invalidateQueries({ queryKey: kitchenKeys.all })
    },
  })
}

export function useCancelKitchenOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) =>
      cancelKitchenOrder(id, reason),
    onSuccess: (data) => {
      qc.setQueryData(kitchenKeys.order(data.id), data)
      qc.invalidateQueries({ queryKey: kitchenKeys.all })
    },
  })
}

export function useUpdateKitchenPriority() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, priority }: { id: string; priority: string }) =>
      updateKitchenPriority(id, priority),
    onSuccess: (data) => {
      qc.setQueryData(kitchenKeys.order(data.id), data)
      qc.invalidateQueries({ queryKey: kitchenKeys.all })
    },
  })
}

export function useStartKitchenItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => startKitchenItem(itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kitchenKeys.all })
    },
  })
}

export function useReadyKitchenItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (itemId: string) => readyKitchenItem(itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kitchenKeys.all })
    },
  })
}
