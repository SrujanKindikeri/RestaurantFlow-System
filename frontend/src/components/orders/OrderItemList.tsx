// =============================================================================
// RestaurantFlow — Order Item List (editable on DRAFT, read-only otherwise)
// Phase 6
// =============================================================================

import type { OrderItem, OrderStatus } from '@/types'

interface OrderItemListProps {
  items: OrderItem[]
  orderStatus: OrderStatus
  onUpdateQuantity?: (itemId: string, delta: number) => void
  onRemove?: (itemId: string) => void
}

export function OrderItemList({
  items,
  orderStatus,
  onUpdateQuantity,
  onRemove,
}: OrderItemListProps) {
  const isDraft = orderStatus === 'DRAFT'

  if (items.length === 0) {
    return (
      <div className="py-8 text-center text-gray-500 text-sm">
        No items yet. Add items from the menu.
      </div>
    )
  }

  return (
    <ul className="divide-y divide-gray-800/60" role="list">
      {items.map((item) => (
        <li key={item.id} className="flex items-center gap-3 py-2.5">
          {/* Name + notes */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-gray-200 truncate">
              {item.item_name_snapshot}
            </p>
            {item.notes && (
              <p className="text-[10px] text-gray-500 truncate italic">{item.notes}</p>
            )}
            <p className="text-[10px] text-gray-600">
              ₹{parseFloat(item.unit_price_snapshot).toFixed(2)} ×{' '}
              {parseFloat(item.quantity).toFixed(item.quantity.includes('.') ? 3 : 0)}
            </p>
          </div>

          {/* Quantity controls (DRAFT only) */}
          {isDraft ? (
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                type="button"
                onClick={() => onUpdateQuantity?.(item.id, -1)}
                aria-label={`Decrease ${item.item_name_snapshot} quantity`}
                className="w-6 h-6 rounded flex items-center justify-center bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
              >
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20 12H4" />
                </svg>
              </button>
              <span className="w-7 text-center text-sm font-medium text-gray-200">
                {parseFloat(item.quantity) % 1 === 0
                  ? parseInt(item.quantity).toString()
                  : parseFloat(item.quantity).toFixed(1)}
              </span>
              <button
                type="button"
                onClick={() => onUpdateQuantity?.(item.id, 1)}
                aria-label={`Increase ${item.item_name_snapshot} quantity`}
                className="w-6 h-6 rounded flex items-center justify-center bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
              >
                <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          ) : (
            <span className="text-sm text-gray-400 flex-shrink-0">
              ×{parseFloat(item.quantity) % 1 === 0
                ? parseInt(item.quantity).toString()
                : parseFloat(item.quantity).toFixed(1)}
            </span>
          )}

          {/* Line total */}
          <span className="text-sm font-semibold text-gray-200 w-20 text-right flex-shrink-0">
            ₹{parseFloat(item.line_total).toFixed(2)}
          </span>

          {/* Remove (DRAFT only) */}
          {isDraft && (
            <button
              type="button"
              onClick={() => onRemove?.(item.id)}
              aria-label={`Remove ${item.item_name_snapshot}`}
              className="flex-shrink-0 p-1 rounded text-gray-600 hover:text-red-400 hover:bg-red-900/20 transition-colors"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </li>
      ))}
    </ul>
  )
}
