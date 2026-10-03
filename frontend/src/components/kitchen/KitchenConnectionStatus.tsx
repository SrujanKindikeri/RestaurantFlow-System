// =============================================================================
// RestaurantFlow — Kitchen Connection Status Indicator
// Phase 7
// =============================================================================

import { cn } from '@/utils/cn'
import type { WsStatus } from '@/hooks/useKitchenWebSocket'

interface Props {
  status: WsStatus
  onRequestSync?: () => void
}

const CONFIG: Record<WsStatus, { label: string; dot: string; text: string }> = {
  CONNECTED:    { label: 'Live',         dot: 'bg-green-400 animate-pulse', text: 'text-green-400' },
  CONNECTING:   { label: 'Connecting…',  dot: 'bg-yellow-400 animate-ping',  text: 'text-yellow-400' },
  DISCONNECTED: { label: 'Reconnecting…',dot: 'bg-orange-400 animate-ping',  text: 'text-orange-400' },
  ERROR:        { label: 'Disconnected', dot: 'bg-red-400',                  text: 'text-red-400' },
}

export function KitchenConnectionStatus({ status, onRequestSync }: Props) {
  const cfg = CONFIG[status]

  return (
    <div className="flex items-center gap-3">
      <span className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2">
          <span className={cn('absolute inline-flex h-full w-full rounded-full opacity-75', cfg.dot)} />
          <span className={cn('relative inline-flex rounded-full h-2 w-2', cfg.dot.replace('animate-pulse', '').replace('animate-ping', ''))} />
        </span>
        <span className={cn('text-xs font-medium', cfg.text)}>{cfg.label}</span>
      </span>

      {(status === 'DISCONNECTED' || status === 'ERROR') && onRequestSync && (
        <button
          onClick={onRequestSync}
          className="text-xs text-gray-500 hover:text-gray-300 underline transition-colors"
          aria-label="Manually sync kitchen state"
        >
          Sync now
        </button>
      )}
    </div>
  )
}
