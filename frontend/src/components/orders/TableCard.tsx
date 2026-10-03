// =============================================================================
// RestaurantFlow — Table Card Component
// Phase 6 — Used in the Tables Dashboard grid
// =============================================================================

import { cn } from '@/utils/cn'
import type { DiningTable } from '@/types'

interface TableCardProps {
  table: DiningTable
  onClick?: (table: DiningTable) => void
  selected?: boolean
}

export function TableCard({ table, onClick, selected }: TableCardProps) {
  const isOccupied = table.is_occupied
  const isInactive = table.status === 'INACTIVE'

  return (
    <button
      type="button"
      onClick={() => onClick?.(table)}
      disabled={isInactive}
      aria-label={`Table ${table.table_number}${isOccupied ? ', occupied' : ', available'}`}
      className={cn(
        'relative flex flex-col items-start gap-1 rounded-xl border p-3 text-left transition-all',
        'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        isInactive
          ? 'opacity-40 cursor-not-allowed border-gray-700 bg-gray-800/30'
          : selected
          ? 'border-brand-500 bg-brand-900/20 ring-1 ring-brand-500/40'
          : isOccupied
          ? 'border-red-700/60 bg-red-900/10 hover:bg-red-900/20 cursor-pointer'
          : 'border-gray-700/60 bg-gray-800/40 hover:bg-gray-800/70 hover:border-gray-600 cursor-pointer',
      )}
    >
      {/* Status dot */}
      <span
        className={cn(
          'absolute top-2.5 right-2.5 w-2.5 h-2.5 rounded-full',
          isInactive
            ? 'bg-gray-600'
            : isOccupied
            ? 'bg-red-500 shadow-[0_0_6px_1px_rgba(239,68,68,0.5)]'
            : 'bg-emerald-500 shadow-[0_0_6px_1px_rgba(52,211,153,0.5)]',
        )}
        aria-hidden="true"
      />

      {/* Table number */}
      <span className="text-base font-bold text-gray-100 leading-none">
        {table.table_number}
      </span>

      {/* Name if present */}
      {table.name && (
        <span className="text-[10px] text-gray-500 truncate max-w-full">
          {table.name}
        </span>
      )}

      {/* Capacity */}
      <span className="text-xs text-gray-400 flex items-center gap-1">
        <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        {table.capacity}
      </span>

      {/* Occupied info */}
      {isOccupied && table.active_order && (
        <span className="text-[10px] text-red-400 truncate max-w-full">
          #{table.active_order.order_number}
        </span>
      )}

      {/* Status label */}
      <span
        className={cn(
          'text-[10px] font-medium uppercase tracking-wide',
          isInactive ? 'text-gray-600' : isOccupied ? 'text-red-400' : 'text-emerald-400',
        )}
      >
        {isInactive ? 'Inactive' : isOccupied ? 'Occupied' : 'Available'}
      </span>
    </button>
  )
}
