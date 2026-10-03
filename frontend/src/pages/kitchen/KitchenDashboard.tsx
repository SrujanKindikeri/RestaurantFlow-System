// =============================================================================
// RestaurantFlow — Kitchen Dashboard (KDS)
// Phase 7
//
// Full-screen kitchen display showing order cards in status columns.
// Real-time updates via WebSocket.
// No financial data displayed.
// =============================================================================

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { KitchenStatusColumn } from '@/components/kitchen/KitchenStatusColumn'
import { KitchenFilters, type KitchenFilterState } from '@/components/kitchen/KitchenFilters'
import { KitchenConnectionStatus } from '@/components/kitchen/KitchenConnectionStatus'
import { useKitchenWebSocket } from '@/hooks/useKitchenWebSocket'
import {
  useAcceptKitchenOrder,
  useStartKitchenOrder,
  useReadyKitchenOrder,
  useCancelKitchenOrder,
  useUpdateKitchenPriority,
  useStartKitchenItem,
  useReadyKitchenItem,
} from '@/hooks/useKitchen'
import { listKitchenOrders } from '@/services/kitchen'
import type {
  KitchenOrder,
  KitchenOrderStatus,
  KitchenPriority,
  KitchenEventMessage,
  KitchenSyncMessage,
} from '@/types'

// Sound notification (simple beep via Web Audio API)
function playNewOrderSound() {
  try {
    const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.frequency.value = 880
    gain.gain.setValueAtTime(0.3, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5)
    osc.start(ctx.currentTime)
    osc.stop(ctx.currentTime + 0.5)
  } catch {
    // Audio not available — ignore silently
  }
}

const LIVE_STATUSES: KitchenOrderStatus[] = ['NEW', 'ACCEPTED', 'PREPARING', 'READY']

export function KitchenDashboard() {
  const { user } = useAuth()
  const token = localStorage.getItem('access_token')

  // Branch from user's first accessible branch
  // In production, this should come from a branch selector or URL param
  const branchId = useRef<string | null>(null)
  const [orders, setOrders] = useState<KitchenOrder[]>([])
  const [isInitialLoading, setIsInitialLoading] = useState(true)
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [soundEnabled, setSoundEnabled] = useState(true)
  const [filters, setFilters] = useState<KitchenFilterState>({
    status: 'ALL',
    orderType: 'ALL',
    priority: 'ALL',
  })

  const canChangePriority = user?.scope?.permissions?.includes('kitchen.priority_update') ?? false

  // ---- Mutations ----
  const acceptMutation  = useAcceptKitchenOrder()
  const startMutation   = useStartKitchenOrder()
  const readyMutation   = useReadyKitchenOrder()
  const cancelMutation  = useCancelKitchenOrder()
  const priorityMutation = useUpdateKitchenPriority()
  const itemStartMutation = useStartKitchenItem()
  const itemReadyMutation = useReadyKitchenItem()

  // ---- Initial REST fetch ----
  useEffect(() => {
    setIsInitialLoading(true)
    listKitchenOrders({
      include_cancelled: false,
    })
      .then(data => {
        setOrders(data.results)
        if (data.results.length > 0 && !branchId.current) {
          branchId.current = data.results[0].branch
        }
      })
      .catch(() => {})
      .finally(() => setIsInitialLoading(false))
  }, [])

  // ---- WebSocket handlers ----
  const handleEvent = useCallback((msg: KitchenEventMessage) => {
    const p = msg.payload
    setOrders(prev => {
      const idx = prev.findIndex(o => o.id === p.kitchen_order_id)
      if (idx === -1) {
        // New order — trigger a fresh fetch for the full order data
        listKitchenOrders({ include_cancelled: false })
          .then(data => setOrders(data.results))
          .catch(() => {})
        if (p.event === 'kitchen.order.created' && soundEnabled) {
          playNewOrderSound()
        }
        return prev
      }
      const updated = [...prev]
      updated[idx] = { ...updated[idx], status: p.status, priority: p.priority }
      return updated
    })
  }, [soundEnabled])

  const handleSync = useCallback((msg: KitchenSyncMessage) => {
    setOrders(msg.orders)
  }, [])

  const { status: wsStatus, requestSync } = useKitchenWebSocket({
    branchId: branchId.current,
    token,
    onEvent: handleEvent,
    onSync: handleSync,
    enabled: !!branchId.current,
  })

  // ---- Filtered orders ----
  const filteredOrders = useMemo(() => {
    return orders.filter(o => {
      if (filters.status !== 'ALL' && o.status !== filters.status) return false
      if (filters.orderType !== 'ALL' && o.order_type !== filters.orderType) return false
      if (filters.priority !== 'ALL' && o.priority !== filters.priority) return false
      return true
    })
  }, [orders, filters])

  const ordersForStatus = useCallback(
    (s: KitchenOrderStatus) => filteredOrders.filter(o => o.status === s),
    [filteredOrders],
  )

  // ---- Mutation wrappers with optimistic loading state ----
  const withLoading = (id: string, fn: () => Promise<unknown>) => {
    setLoadingId(id)
    fn()
      .then(() => {
        // Refresh full list after mutation to get server-authoritative state
        return listKitchenOrders({ include_cancelled: false })
      })
      .then(data => { if (data) setOrders(data.results) })
      .catch(() => {})
      .finally(() => setLoadingId(null))
  }

  const handleAccept  = (id: string) => withLoading(id, () => acceptMutation.mutateAsync(id))
  const handleStart   = (id: string) => withLoading(id, () => startMutation.mutateAsync(id))
  const handleReady   = (id: string) => withLoading(id, () => readyMutation.mutateAsync(id))
  const handleCancel  = (id: string) => withLoading(id, () => cancelMutation.mutateAsync({ id }))
  const handleItemStart = (itemId: string) => itemStartMutation.mutate(itemId, {
    onSuccess: () => {
      listKitchenOrders({ include_cancelled: false })
        .then(data => setOrders(data.results))
        .catch(() => {})
    },
  })
  const handleItemReady = (itemId: string) => itemReadyMutation.mutate(itemId, {
    onSuccess: () => {
      listKitchenOrders({ include_cancelled: false })
        .then(data => setOrders(data.results))
        .catch(() => {})
    },
  })
  const handlePriority = (id: string, priority: KitchenPriority) =>
    withLoading(id, () => priorityMutation.mutateAsync({ id, priority }))

  if (isInitialLoading) {
    return (
      <div className="flex items-center justify-center h-96 text-gray-500">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500 mx-auto mb-3" />
          <p>Loading kitchen orders…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full min-h-0 gap-0">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-900 border-b border-gray-800 flex-shrink-0">
        <div>
          <h1 className="text-base font-bold text-white">Kitchen Display</h1>
          <p className="text-xs text-gray-500">
            {new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'short', day: 'numeric' })}
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* Sound toggle */}
          <button
            onClick={() => setSoundEnabled(v => !v)}
            className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1.5 transition-colors"
            aria-label={soundEnabled ? 'Disable sound notifications' : 'Enable sound notifications'}
            aria-pressed={soundEnabled}
          >
            <span>{soundEnabled ? '🔔' : '🔕'}</span>
            <span>{soundEnabled ? 'Sound On' : 'Sound Off'}</span>
          </button>
          <KitchenConnectionStatus status={wsStatus} onRequestSync={requestSync} />
        </div>
      </div>

      {/* Filters */}
      <div className="px-4 border-b border-gray-800 bg-gray-900/50 flex-shrink-0">
        <KitchenFilters
          filters={filters}
          onChange={setFilters}
          totalCount={filteredOrders.length}
        />
      </div>

      {/* Columns */}
      <div className="flex-1 min-h-0 overflow-x-auto">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 p-4 h-full" style={{ minWidth: '640px' }}>
          {LIVE_STATUSES.map(s => (
            <KitchenStatusColumn
              key={s}
              status={s}
              orders={ordersForStatus(s)}
              onAccept={handleAccept}
              onStart={handleStart}
              onReady={handleReady}
              onCancel={handleCancel}
              onItemStart={handleItemStart}
              onItemReady={handleItemReady}
              onPriorityChange={handlePriority}
              canChangePriority={canChangePriority}
              loadingId={loadingId}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
