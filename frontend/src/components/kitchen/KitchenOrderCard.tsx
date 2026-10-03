// =============================================================================
// RestaurantFlow — Kitchen Order Card
// Phase 7: KDS order card displayed in each status column
// =============================================================================

import { useState } from 'react'
import { cn } from '@/utils/cn'
import { KitchenOrderTimer } from './KitchenOrderTimer'
import { KitchenPriorityBadge, KitchenPriorityControl } from './KitchenPriorityBadge'
import type { KitchenOrder, KitchenOrderItem, KitchenPriority } from '@/types'

interface Props {
  order: KitchenOrder
  onAccept?: (id: string) => void
  onStart?: (id: string) => void
  onReady?: (id: string) => void
  onCancel?: (id: string) => void
  onItemStart?: (itemId: string) => void
  onItemReady?: (itemId: string) => void
  onPriorityChange?: (id: string, priority: KitchenPriority) => void
  canChangePriority?: boolean
  isLoading?: boolean
}

const FOOD_TYPE_ICON: Record<string, string> = {
  VEG:     '🟢',
  NON_VEG: '🔴',
  EGG:     '🟡',
  VEGAN:   '🌿',
  OTHER:   '⚪',
}

const ITEM_STATUS_STYLE: Record<string, string> = {
  NEW:       'text-gray-400',
  PREPARING: 'text-yellow-400',
  READY:     'text-green-400 line-through',
  CANCELLED: 'text-gray-600 line-through',
}

function OrderItemRow({ item, onStart, onReady }: {
  item: KitchenOrderItem
  onStart?: (id: string) => void
  onReady?: (id: string) => void
}) {
  const icon = FOOD_TYPE_ICON[item.food_type] ?? '⚪'
  const textStyle = ITEM_STATUS_STYLE[item.status] ?? 'text-gray-300'

  return (
    <li className="flex items-start justify-between gap-2 py-1 border-b border-gray-800/50 last:border-0">
      <div className="flex items-start gap-2 flex-1 min-w-0">
        <span className="text-xs mt-0.5 flex-shrink-0" aria-label={item.food_type}>{icon}</span>
        <div className="min-w-0">
          <p className={cn('text-sm font-medium leading-snug', textStyle)}>
            <span className="text-gray-300">{item.quantity} ×</span>{' '}
            {item.item_name_snapshot}
          </p>
          {item.notes && (
            <p className="text-xs text-amber-400 mt-0.5 italic">
              ✏ {item.notes}
            </p>
          )}
          {item.station && (
            <p className="text-[10px] text-gray-600 mt-0.5">{item.station}</p>
          )}
        </div>
      </div>
      {/* Per-item actions */}
      {item.status === 'NEW' && onStart && (
        <button
          onClick={() => onStart(item.id)}
          className="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-yellow-900/40 text-yellow-400 border border-yellow-700 hover:bg-yellow-800/50 transition-colors"
          aria-label={`Start ${item.item_name_snapshot}`}
        >
          START
        </button>
      )}
      {item.status === 'PREPARING' && onReady && (
        <button
          onClick={() => onReady(item.id)}
          className="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded bg-green-900/40 text-green-400 border border-green-700 hover:bg-green-800/50 transition-colors"
          aria-label={`Mark ${item.item_name_snapshot} ready`}
        >
          DONE
        </button>
      )}
    </li>
  )
}

export function KitchenOrderCard({
  order,
  onAccept,
  onStart,
  onReady,
  onCancel,
  onItemStart,
  onItemReady,
  onPriorityChange,
  canChangePriority = false,
  isLoading = false,
}: Props) {
  const [showCancel, setShowCancel] = useState(false)

  const orderTypeLabel = {
    DINE_IN:  'DINE-IN',
    TAKEAWAY: 'TAKEAWAY',
    COUNTER:  'COUNTER',
  }[order.order_type] ?? order.order_type

  const tableLabel = order.table_number
    ? ` · T${order.table_number}${order.table_section ? ` (${order.table_section})` : ''}`
    : ''
  const counterLabel = order.counter_code ? ` · ${order.counter_code}` : ''

  return (
    <article
      className={cn(
        'rounded-xl border bg-gray-900 flex flex-col overflow-hidden transition-shadow',
        order.priority === 'URGENT' && 'border-red-700 shadow-red-900/30 shadow-lg',
        order.priority === 'HIGH'   && 'border-orange-700',
        order.priority === 'NORMAL' && 'border-gray-800',
        order.status === 'READY'    && 'opacity-80',
      )}
      aria-label={`Kitchen order ${order.order_number}`}
    >
      {/* Header */}
      <header className="px-3 pt-3 pb-2 border-b border-gray-800 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-white text-sm">{order.order_number}</span>
            <KitchenPriorityBadge priority={order.priority} />
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {orderTypeLabel}{tableLabel}{counterLabel}
            {order.assigned_waiter_name && (
              <span className="ml-1">· {order.assigned_waiter_name}</span>
            )}
          </p>
        </div>
        <KitchenOrderTimer receivedAt={order.received_at} className="flex-shrink-0 text-right" />
      </header>

      {/* Items */}
      <ul className="px-3 py-2 flex-1 space-y-0" role="list" aria-label="Order items">
        {order.items.map(item => (
          <OrderItemRow
            key={item.id}
            item={item}
            onStart={onItemStart}
            onReady={onItemReady}
          />
        ))}
      </ul>

      {/* Kitchen note */}
      {order.kitchen_note && (
        <div className="px-3 pb-2">
          <p className="text-xs text-blue-400 italic bg-blue-900/20 rounded px-2 py-1">
            📝 {order.kitchen_note}
          </p>
        </div>
      )}

      {/* Order note */}
      {order.order_notes && (
        <div className="px-3 pb-2">
          <p className="text-xs text-gray-500 italic">Order note: {order.order_notes}</p>
        </div>
      )}

      {/* Priority control (managers only) */}
      {canChangePriority && order.status !== 'READY' && order.status !== 'CANCELLED' && onPriorityChange && (
        <div className="px-3 pb-2 flex items-center gap-2">
          <span className="text-xs text-gray-600">Priority:</span>
          <KitchenPriorityControl
            priority={order.priority}
            onChange={p => onPriorityChange(order.id, p)}
            disabled={isLoading}
          />
        </div>
      )}

      {/* Action buttons */}
      <footer className="px-3 pb-3 pt-2 border-t border-gray-800 flex flex-col gap-2">
        {order.status === 'NEW' && onAccept && (
          <button
            onClick={() => onAccept(order.id)}
            disabled={isLoading}
            className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label={`Accept order ${order.order_number}`}
          >
            ACCEPT
          </button>
        )}

        {order.status === 'ACCEPTED' && onStart && (
          <button
            onClick={() => onStart(order.id)}
            disabled={isLoading}
            className="w-full py-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label={`Start preparation for order ${order.order_number}`}
          >
            START PREP
          </button>
        )}

        {order.status === 'PREPARING' && onReady && (
          <button
            onClick={() => onReady(order.id)}
            disabled={isLoading}
            className="w-full py-2.5 rounded-lg bg-green-600 hover:bg-green-500 text-white text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label={`Mark order ${order.order_number} ready`}
          >
            ORDER READY
          </button>
        )}

        {order.status === 'READY' && (
          <div className="w-full py-2 rounded-lg bg-green-900/30 border border-green-700 text-green-400 text-sm font-semibold text-center">
            ✓ READY FOR PICKUP
          </div>
        )}

        {/* Cancel button (not for READY or already CANCELLED) */}
        {order.status !== 'READY' && order.status !== 'CANCELLED' && onCancel && (
          <>
            {!showCancel ? (
              <button
                onClick={() => setShowCancel(true)}
                className="w-full py-1.5 rounded-lg border border-gray-700 text-gray-500 text-xs hover:border-red-700 hover:text-red-400 transition-colors"
                aria-label={`Cancel order ${order.order_number}`}
              >
                Cancel
              </button>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => { onCancel(order.id); setShowCancel(false) }}
                  disabled={isLoading}
                  className="flex-1 py-1.5 rounded-lg bg-red-700 hover:bg-red-600 text-white text-xs font-semibold transition-colors disabled:opacity-50"
                >
                  Confirm Cancel
                </button>
                <button
                  onClick={() => setShowCancel(false)}
                  className="flex-1 py-1.5 rounded-lg border border-gray-700 text-gray-400 text-xs hover:bg-gray-800 transition-colors"
                >
                  Back
                </button>
              </div>
            )}
          </>
        )}
      </footer>
    </article>
  )
}
