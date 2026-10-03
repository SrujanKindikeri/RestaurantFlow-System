// =============================================================================
// RestaurantFlow — Kitchen Priority Badge + Control
// Phase 7
// =============================================================================

import { cn } from '@/utils/cn'
import type { KitchenPriority } from '@/types'

interface BadgeProps {
  priority: KitchenPriority
  size?: 'sm' | 'md'
}

const PRIORITY_STYLES: Record<KitchenPriority, { badge: string; label: string }> = {
  NORMAL: { badge: 'bg-gray-800 text-gray-400 border-gray-700',    label: 'Normal' },
  HIGH:   { badge: 'bg-orange-900/50 text-orange-400 border-orange-700', label: 'High' },
  URGENT: { badge: 'bg-red-900/50 text-red-400 border-red-700 animate-pulse', label: '🔴 URGENT' },
}

export function KitchenPriorityBadge({ priority, size = 'sm' }: BadgeProps) {
  const cfg = PRIORITY_STYLES[priority]
  return (
    <span
      className={cn(
        'inline-flex items-center font-semibold rounded border uppercase tracking-wide',
        size === 'sm' ? 'px-1.5 py-0.5 text-[10px]' : 'px-2 py-1 text-xs',
        cfg.badge,
      )}
    >
      {cfg.label}
    </span>
  )
}

// ---- Priority Control (dropdown for managers) ----

interface ControlProps {
  priority: KitchenPriority
  onChange: (p: KitchenPriority) => void
  disabled?: boolean
}

export function KitchenPriorityControl({ priority, onChange, disabled }: ControlProps) {
  return (
    <select
      value={priority}
      onChange={e => onChange(e.target.value as KitchenPriority)}
      disabled={disabled}
      aria-label="Change order priority"
      className={cn(
        'bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1',
        'focus:outline-none focus:ring-1 focus:ring-brand-500',
        disabled && 'opacity-50 cursor-not-allowed',
      )}
    >
      <option value="NORMAL">Normal</option>
      <option value="HIGH">High</option>
      <option value="URGENT">Urgent</option>
    </select>
  )
}
