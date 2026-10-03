// =============================================================================
// RestaurantFlow — Table Grid Component
// Phase 6 — Groups tables by section and renders TableCard grid
// =============================================================================

import type { DiningTable } from '@/types'
import { TableCard } from './TableCard'

interface TableGridProps {
  tables: DiningTable[]
  selectedTableId?: string | null
  onSelectTable?: (table: DiningTable) => void
}

export function TableGrid({ tables, selectedTableId, onSelectTable }: TableGridProps) {
  // Group tables by section, preserving insertion order
  const sections = tables.reduce<Record<string, DiningTable[]>>((acc, table) => {
    const section = table.section || 'General'
    if (!acc[section]) acc[section] = []
    acc[section].push(table)
    return acc
  }, {})

  const sectionNames = Object.keys(sections)

  if (sectionNames.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-500">
        <svg className="h-10 w-10 mb-3 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M3 14h18M10 10V4m0 16V14M14 10V4m0 16V14" />
        </svg>
        <p className="text-sm">No tables configured for this branch.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {sectionNames.map((section) => (
        <section key={section} aria-labelledby={`section-${section}`}>
          <h3
            id={`section-${section}`}
            className="text-[10px] font-semibold text-gray-600 uppercase tracking-widest mb-3 px-0.5"
          >
            {section}
          </h3>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-8 gap-2.5">
            {sections[section].sort((a, b) => a.display_order - b.display_order).map((table) => (
              <TableCard
                key={table.id}
                table={table}
                selected={selectedTableId === table.id}
                onClick={onSelectTable}
              />
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
