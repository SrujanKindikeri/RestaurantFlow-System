// =============================================================================
// RestaurantFlow — Order Status Badge
// Phase 6
// =============================================================================

import { cn } from '@/utils/cn'
import type { OrderStatus, OrderType } from '@/types'

const STATUS_CONFIG: Record<OrderStatus, { label: string; classes: string }> = {
  DRAFT:     { label: 'Draft',     classes: 'bg-gray-700 text-gray-300 border-gray-600' },
  CONFIRMED: { label: 'Confirmed', classes: 'bg-blue-900/60 text-blue-300 border-blue-700' },
  CANCELLED: { label: 'Cancelled', classes: 'bg-red-900/60 text-red-400 border-red-800' },
}

const TYPE_CONFIG: Record<OrderType, { label: string; classes: string }> = {
  DINE_IN:  { label: 'Dine In',  classes: 'bg-brand-900/50 text-brand-300 border-brand-700' },
  TAKEAWAY: { label: 'Takeaway', classes: 'bg-yellow-900/50 text-yellow-300 border-yellow-700' },
  COUNTER:  { label: 'Counter',  classes: 'bg-purple-900/50 text-purple-300 border-purple-700' },
}

interface OrderStatusBadgeProps {
  status: OrderStatus
  className?: string
}

export function OrderStatusBadge({ status, className }: OrderStatusBadgeProps) {
  const config = STATUS_CONFIG[status] ?? { label: status, classes: 'bg-gray-700 text-gray-300 border-gray-600' }
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
        config.classes,
        className,
      )}
    >
      {config.label}
    </span>
  )
}

interface OrderTypeBadgeProps {
  type: OrderType
  className?: string
}

export function OrderTypeBadge({ type, className }: OrderTypeBadgeProps) {
  const config = TYPE_CONFIG[type] ?? { label: type, classes: 'bg-gray-700 text-gray-300 border-gray-600' }
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
        config.classes,
        className,
      )}
    >
      {config.label}
    </span>
  )
}
