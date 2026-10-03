// =============================================================================
// RestaurantFlow — Kitchen Filters
// Phase 7: Filter bar for status, order type, priority
// =============================================================================

import { cn } from '@/utils/cn'
import type { KitchenOrderStatus, KitchenPriority } from '@/types'

export interface KitchenFilterState {
  status: KitchenOrderStatus | 'ALL'
  orderType: 'ALL' | 'DINE_IN' | 'TAKEAWAY' | 'COUNTER'
  priority: KitchenPriority | 'ALL'
}

interface Props {
  filters: KitchenFilterState
  onChange: (f: KitchenFilterState) => void
  totalCount?: number
}

function FilterPill<T extends string>({
  value, current, label, onClick, colorClass,
}: {
  value: T
  current: T
  label: string
  onClick: (v: T) => void
  colorClass?: string
}) {
  const active = value === current
  return (
    <button
      onClick={() => onClick(value)}
      className={cn(
        'px-3 py-1 rounded-full text-xs font-medium border transition-colors whitespace-nowrap',
        active
          ? cn('border-transparent text-white', colorClass ?? 'bg-brand-600')
          : 'border-gray-700 text-gray-500 hover:text-gray-300 hover:border-gray-600',
      )}
      aria-pressed={active}
      aria-label={`Filter by ${label}`}
    >
      {label}
    </button>
  )
}

export function KitchenFilters({ filters, onChange, totalCount }: Props) {
  const set = <K extends keyof KitchenFilterState>(key: K, val: KitchenFilterState[K]) =>
    onChange({ ...filters, [key]: val })

  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-3 py-2">
      {/* Status */}
      <div className="flex items-center gap-1.5 flex-wrap" role="group" aria-label="Filter by status">
        <span className="text-[10px] text-gray-600 uppercase tracking-wider mr-1">Status</span>
        <FilterPill value="ALL"       current={filters.status} label="All"       onClick={v => set('status', v)} colorClass="bg-gray-700" />
        <FilterPill value="NEW"       current={filters.status} label="New"       onClick={v => set('status', v)} colorClass="bg-blue-700" />
        <FilterPill value="ACCEPTED"  current={filters.status} label="Accepted"  onClick={v => set('status', v)} colorClass="bg-orange-700" />
        <FilterPill value="PREPARING" current={filters.status} label="Preparing" onClick={v => set('status', v)} colorClass="bg-purple-700" />
        <FilterPill value="READY"     current={filters.status} label="Ready"     onClick={v => set('status', v)} colorClass="bg-green-700" />
      </div>

      {/* Separator */}
      <div className="hidden sm:block h-4 w-px bg-gray-800" aria-hidden="true" />

      {/* Order type */}
      <div className="flex items-center gap-1.5 flex-wrap" role="group" aria-label="Filter by order type">
        <span className="text-[10px] text-gray-600 uppercase tracking-wider mr-1">Type</span>
        <FilterPill value="ALL"      current={filters.orderType} label="All"      onClick={v => set('orderType', v)} colorClass="bg-gray-700" />
        <FilterPill value="DINE_IN"  current={filters.orderType} label="Dine-In"  onClick={v => set('orderType', v)} colorClass="bg-indigo-700" />
        <FilterPill value="TAKEAWAY" current={filters.orderType} label="Takeaway" onClick={v => set('orderType', v)} colorClass="bg-teal-700" />
        <FilterPill value="COUNTER"  current={filters.orderType} label="Counter"  onClick={v => set('orderType', v)} colorClass="bg-cyan-700" />
      </div>

      {/* Separator */}
      <div className="hidden sm:block h-4 w-px bg-gray-800" aria-hidden="true" />

      {/* Priority */}
      <div className="flex items-center gap-1.5 flex-wrap" role="group" aria-label="Filter by priority">
        <span className="text-[10px] text-gray-600 uppercase tracking-wider mr-1">Priority</span>
        <FilterPill value="ALL"    current={filters.priority} label="All"    onClick={v => set('priority', v)} colorClass="bg-gray-700" />
        <FilterPill value="NORMAL" current={filters.priority} label="Normal" onClick={v => set('priority', v)} colorClass="bg-gray-700" />
        <FilterPill value="HIGH"   current={filters.priority} label="High"   onClick={v => set('priority', v)} colorClass="bg-orange-700" />
        <FilterPill value="URGENT" current={filters.priority} label="Urgent" onClick={v => set('priority', v)} colorClass="bg-red-700" />
      </div>

      {/* Count */}
      {totalCount !== undefined && (
        <span className="ml-auto text-xs text-gray-600 tabular-nums">
          {totalCount} order{totalCount !== 1 ? 's' : ''}
        </span>
      )}
    </div>
  )
}
