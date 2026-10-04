// =============================================================================
// RestaurantFlow — Inventory Report Page
// Phase 14
// =============================================================================

import { useInventorySummary } from '@/hooks/useReporting'
import { formatCurrency } from '@/utils/reportingDates'
import type { ReportFilters } from '@/services/reporting'

export function InventoryReportPage() {
  const filters: ReportFilters = {}
  const { data, isLoading, isError } = useInventorySummary(filters)
  const inv = data?.data

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-white">Inventory Report</h1>
        <p className="text-sm text-gray-500 mt-1">Current stock levels across all locations</p>
      </div>

      {isError && (
        <div className="rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-3 text-sm text-red-400">
          Failed to load inventory data.
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Items', value: String(inv?.total_inventory_items ?? '—'), color: 'text-blue-400' },
          { label: 'Low Stock', value: String(inv?.low_stock_items ?? '—'), color: 'text-yellow-400' },
          { label: 'Out of Stock', value: String(inv?.out_of_stock_items ?? '—'), color: 'text-red-400' },
          { label: 'Stock Value', value: formatCurrency(inv?.stock_value_estimate), color: 'text-emerald-400' },
        ].map(item => (
          <div key={item.label} className="rounded-xl bg-gray-900/60 border border-gray-800 px-4 py-4">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">{item.label}</p>
            {isLoading
              ? <div className="h-8 w-16 bg-gray-800 animate-pulse rounded" />
              : <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
            }
          </div>
        ))}
      </div>

      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3">Notes</h2>
        <ul className="text-sm text-gray-500 space-y-2 list-disc list-inside">
          <li>Stock value is estimated as <span className="text-gray-300">quantity × weighted-average cost</span></li>
          <li>Low stock items have quantity ≤ reorder level</li>
          <li>Out of stock items have zero or negative available quantity</li>
          <li>This is a current snapshot — not a historical accounting valuation</li>
        </ul>
      </div>
    </div>
  )
}
