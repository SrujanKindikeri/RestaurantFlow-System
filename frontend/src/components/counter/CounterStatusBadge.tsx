// =============================================================================
// RestaurantFlow — Counter Status Badge
// Phase 4
// =============================================================================

import { cn } from '@/utils/cn'
import type { CounterStatus, SessionStatus } from '@/types'

interface CounterStatusBadgeProps {
  status: CounterStatus
}

const counterStatusConfig: Record<CounterStatus, { label: string; className: string }> = {
  ACTIVE:      { label: 'Active',      className: 'bg-green-500/10 text-green-400 border-green-500/20' },
  INACTIVE:    { label: 'Inactive',    className: 'bg-gray-500/10 text-gray-400 border-gray-500/20' },
  MAINTENANCE: { label: 'Maintenance', className: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' },
}

export function CounterStatusBadge({ status }: CounterStatusBadgeProps) {
  const config = counterStatusConfig[status] ?? counterStatusConfig.INACTIVE
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border',
        config.className,
      )}
    >
      {config.label}
    </span>
  )
}

interface SessionStatusBadgeProps {
  status: SessionStatus
}

const sessionStatusConfig: Record<SessionStatus, { label: string; className: string }> = {
  OPEN:         { label: 'Open',         className: 'bg-brand-500/10 text-brand-400 border-brand-500/20' },
  CLOSED:       { label: 'Closed',       className: 'bg-gray-500/10 text-gray-400 border-gray-500/20' },
  FORCE_CLOSED: { label: 'Force Closed', className: 'bg-red-500/10 text-red-400 border-red-500/20' },
}

export function SessionStatusBadge({ status }: SessionStatusBadgeProps) {
  const config = sessionStatusConfig[status] ?? sessionStatusConfig.CLOSED
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border',
        config.className,
      )}
    >
      {config.label}
    </span>
  )
}

/** Inline coloured dot for counter status in table rows */
export function CounterStatusDot({ status }: { status: CounterStatus }) {
  const colors: Record<CounterStatus, string> = {
    ACTIVE:      'bg-green-400',
    INACTIVE:    'bg-gray-500',
    MAINTENANCE: 'bg-yellow-400',
  }
  return (
    <span
      className={cn('inline-block w-2 h-2 rounded-full', colors[status] ?? 'bg-gray-500')}
      aria-hidden="true"
    />
  )
}
