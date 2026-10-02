// =============================================================================
// RestaurantFlow — Status Indicator Component
// =============================================================================

import { cn } from '@/utils/cn'

type Status = 'connected' | 'disconnected' | 'loading'

interface StatusIndicatorProps {
  status: Status
  label: string
  sublabel?: string
}

const statusConfig: Record<Status, { dot: string; text: string; badge: string }> = {
  connected: {
    dot: 'bg-brand-500 shadow-[0_0_8px_2px_rgba(34,197,94,0.4)]',
    text: 'text-brand-400',
    badge: 'Connected',
  },
  disconnected: {
    dot: 'bg-red-500 shadow-[0_0_8px_2px_rgba(239,68,68,0.4)]',
    text: 'text-red-400',
    badge: 'Unreachable',
  },
  loading: {
    dot: 'bg-yellow-500 animate-pulse',
    text: 'text-yellow-400',
    badge: 'Checking…',
  },
}

export function StatusIndicator({ status, label, sublabel }: StatusIndicatorProps) {
  const config = statusConfig[status]

  return (
    <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-gray-800/50 border border-gray-700/50">
      <div className="flex flex-col gap-0.5">
        <span className="text-sm font-medium text-gray-200">{label}</span>
        {sublabel && <span className="text-xs text-gray-500">{sublabel}</span>}
      </div>
      <div className="flex items-center gap-2">
        <span className={cn('text-xs font-medium', config.text)}>{config.badge}</span>
        <span
          className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', config.dot)}
          role="status"
          aria-label={`${label}: ${config.badge}`}
        />
      </div>
    </div>
  )
}
