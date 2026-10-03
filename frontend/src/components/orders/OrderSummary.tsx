// =============================================================================
// RestaurantFlow — Order Summary Panel
// Phase 6 — Shows totals (preview only, not billing)
// =============================================================================

import type { OrderItem } from '@/types'

interface OrderSummaryProps {
  items: OrderItem[]
  note?: string
}

export function OrderSummary({ items, note }: OrderSummaryProps) {
  const subtotal = items.reduce(
    (acc, item) => acc + parseFloat(item.line_total),
    0,
  )

  return (
    <div className="border-t border-gray-800 pt-3 mt-3 space-y-1.5">
      <div className="flex justify-between text-sm text-gray-400">
        <span>Items</span>
        <span>{items.length}</span>
      </div>
      <div className="flex justify-between text-sm font-semibold text-gray-200">
        <span>Preview Total</span>
        <span>₹{subtotal.toFixed(2)}</span>
      </div>
      {note && (
        <p className="text-[10px] text-gray-600 mt-1">{note}</p>
      )}
      <p className="text-[10px] text-gray-700">
        * Preview total — final bill will be generated at checkout
      </p>
    </div>
  )
}
