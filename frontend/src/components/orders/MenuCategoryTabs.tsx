// =============================================================================
// RestaurantFlow — Menu Category Tabs (POS fast-select)
// Phase 6
// =============================================================================

import { cn } from '@/utils/cn'
import type { CatalogCategory } from '@/types'

interface MenuCategoryTabsProps {
  categories: CatalogCategory[]
  activeCategoryId: string | null
  onSelect: (id: string) => void
}

export function MenuCategoryTabs({ categories, activeCategoryId, onSelect }: MenuCategoryTabsProps) {
  return (
    <div
      className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none"
      role="tablist"
      aria-label="Menu categories"
    >
      {categories.map((cat) => (
        <button
          key={cat.id}
          type="button"
          role="tab"
          aria-selected={activeCategoryId === cat.id}
          onClick={() => onSelect(cat.id)}
          className={cn(
            'flex-shrink-0 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
            activeCategoryId === cat.id
              ? 'bg-brand-500 text-white shadow-sm'
              : 'bg-gray-800 text-gray-400 hover:text-gray-200 hover:bg-gray-700',
          )}
        >
          {cat.name}
          <span className="ml-1.5 text-[10px] opacity-60">
            {cat.items.length}
          </span>
        </button>
      ))}
    </div>
  )
}
