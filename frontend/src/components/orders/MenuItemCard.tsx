// =============================================================================
// RestaurantFlow — Menu Item Card (POS quick-add)
// Phase 6
// =============================================================================

import { cn } from '@/utils/cn'
import type { CatalogItem, FoodType } from '@/types'

const FOOD_TYPE_DOT: Record<FoodType, string> = {
  VEG:     'bg-emerald-500',
  NON_VEG: 'bg-red-500',
  EGG:     'bg-yellow-400',
  VEGAN:   'bg-teal-400',
  OTHER:   'bg-gray-500',
}

interface MenuItemCardProps {
  item: CatalogItem
  onAdd: (item: CatalogItem) => void
}

export function MenuItemCard({ item, onAdd }: MenuItemCardProps) {
  const hasPrice = item.price != null

  return (
    <div
      className={cn(
        'flex items-center justify-between gap-2 rounded-lg border border-gray-700/60 bg-gray-800/40',
        'px-3 py-2.5 hover:border-gray-600 hover:bg-gray-800/70 transition-colors',
        !hasPrice && 'opacity-50',
      )}
    >
      {/* Left: name + price */}
      <div className="flex items-start gap-2 min-w-0 flex-1">
        {/* Food type indicator */}
        <span
          className={cn(
            'mt-1 w-2 h-2 rounded-sm flex-shrink-0',
            FOOD_TYPE_DOT[item.food_type] ?? 'bg-gray-500',
          )}
          aria-label={item.food_type}
        />
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-100 truncate leading-snug">
            {item.name}
          </p>
          {item.short_description && (
            <p className="text-[10px] text-gray-500 truncate">{item.short_description}</p>
          )}
          <p className="text-sm font-semibold text-brand-400 mt-0.5">
            {hasPrice ? `₹${parseFloat(item.price!).toFixed(2)}` : 'No price'}
          </p>
        </div>
      </div>

      {/* Add button */}
      <button
        type="button"
        onClick={() => onAdd(item)}
        disabled={!hasPrice}
        aria-label={`Add ${item.name} to order`}
        className={cn(
          'flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
          hasPrice
            ? 'bg-brand-500 hover:bg-brand-400 text-white active:scale-95'
            : 'bg-gray-700 text-gray-500 cursor-not-allowed',
        )}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
        </svg>
      </button>
    </div>
  )
}
