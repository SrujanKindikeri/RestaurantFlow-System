// =============================================================================
// RestaurantFlow — Bill Status Badge
// Phase 8
// =============================================================================

import { cn } from '@/utils/cn'
import type { BillStatus } from '@/types'

interface Props {
  status: BillStatus
  className?: string
}

const CONFIG: Record<BillStatus, { label: string; cls: string }> = {
  DRAFT:     { label: 'Draft',     cls: 'bg-gray-700 text-gray-300 border-gray-600' },
  FINALIZED: { label: 'Finalized', cls: 'bg-green-900/60 text-green-400 border-green-700' },
  CANCELLED: { label: 'Cancelled', cls: 'bg-red-900/60 text-red-400 border-red-700' },
  VOID:      { label: 'Void',      cls: 'bg-gray-800 text-gray-500 border-gray-700' },
}

export function BillStatusBadge({ status, className }: Props) {
  const cfg = CONFIG[status] ?? CONFIG.DRAFT
  return (
    <span
      className={cn(
        'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border',
        cfg.cls,
        className,
      )}
    >
      {cfg.label}
    </span>
  )
}
