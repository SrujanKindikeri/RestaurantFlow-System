// =============================================================================
// RestaurantFlow — Kitchen Status Column
// Phase 7: One column per status in the KDS board view
// =============================================================================

import { cn } from '@/utils/cn'
import { KitchenOrderCard } from './KitchenOrderCard'
import type { KitchenOrder, KitchenOrderStatus, KitchenPriority } from '@/types'

interface Props {
  status: KitchenOrderStatus
  orders: KitchenOrder[]
  onAccept?: (id: string) => void
  onStart?: (id: string) => void
  onReady?: (id: string) => void
  onCancel?: (id: string) => void
  onItemStart?: (itemId: string) => void
  onItemReady?: (itemId: string) => void
  onPriorityChange?: (id: string, priority: KitchenPriority) => void
  canChangePriority?: boolean
  loadingId?: string | null
}

const COLUMN_CONFIG: Record<KitchenOrderStatus, {
  label: string
  headerBg: string
  headerText: string
  countBg: string
}> = {
  NEW:       { label: 'New',       headerBg: 'bg-blue-900/30',   headerText: 'text-blue-400',   countBg: 'bg-blue-800/60' },
  ACCEPTED:  { label: 'Accepted',  headerBg: 'bg-orange-900/30', headerText: 'text-orange-400', countBg: 'bg-orange-800/60' },
  PREPARING: { label: 'Preparing', headerBg: 'bg-purple-900/30', headerText: 'text-purple-400', countBg: 'bg-purple-800/60' },
  READY:     { label: 'Ready',     headerBg: 'bg-green-900/30',  headerText: 'text-green-400',  countBg: 'bg-green-800/60' },
  CANCELLED: { label: 'Cancelled', headerBg: 'bg-gray-900/30',   headerText: 'text-gray-500',   countBg: 'bg-gray-800/60' },
}

export function KitchenStatusColumn({
  status,
  orders,
  onAccept,
  onStart,
  onReady,
  onCancel,
  onItemStart,
  onItemReady,
  onPriorityChange,
  canChangePriority,
  loadingId,
}: Props) {
  const cfg = COLUMN_CONFIG[status]

  return (
    <section
      className="flex flex-col min-w-0 min-h-0"
      aria-label={`${cfg.label} orders column`}
    >
      {/* Column header */}
      <div className={cn('flex items-center justify-between px-3 py-2.5 rounded-t-lg border-b border-gray-800', cfg.headerBg)}>
        <h2 className={cn('font-semibold text-sm uppercase tracking-wider', cfg.headerText)}>
          {cfg.label}
        </h2>
        <span
          className={cn('text-xs font-bold rounded-full px-2 py-0.5 min-w-[1.5rem] text-center', cfg.countBg, cfg.headerText)}
          aria-label={`${orders.length} ${cfg.label.toLowerCase()} orders`}
        >
          {orders.length}
        </span>
      </div>

      {/* Order cards */}
      <div
        className="flex-1 overflow-y-auto space-y-3 p-3 bg-gray-950/50 rounded-b-lg min-h-0"
        style={{ maxHeight: 'calc(100vh - 13rem)' }}
      >
        {orders.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-24 text-gray-700">
            <span className="text-2xl mb-1">—</span>
            <span className="text-xs">No {cfg.label.toLowerCase()} orders</span>
          </div>
        ) : (
          orders.map(order => (
            <KitchenOrderCard
              key={order.id}
              order={order}
              onAccept={status === 'NEW' ? onAccept : undefined}
              onStart={status === 'ACCEPTED' ? onStart : undefined}
              onReady={status === 'PREPARING' ? onReady : undefined}
              onCancel={onCancel}
              onItemStart={onItemStart}
              onItemReady={onItemReady}
              onPriorityChange={onPriorityChange}
              canChangePriority={canChangePriority}
              isLoading={loadingId === order.id}
            />
          ))
        )}
      </div>
    </section>
  )
}
