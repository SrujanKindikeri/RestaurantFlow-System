// =============================================================================
// RestaurantFlow — Stock Overview Page
// Phase 10
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { listStockBalances, listInventoryItems, listStorageLocations } from '@/services/inventory'
import type { StockBalance, StockStatus } from '@/types'

const STATUS_BADGE: Record<StockStatus, string> = {
  IN_STOCK:     'bg-green-500/10 text-green-400 border-green-500/20',
  LOW_STOCK:    'bg-amber-500/10 text-amber-400 border-amber-500/20',
  OUT_OF_STOCK: 'bg-red-500/10 text-red-400 border-red-500/20',
}

export function StockOverviewPage() {
  const [balances, setBalances] = useState<StockBalance[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState('')
  const [filterLocation, setFilterLocation] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filterStatus) params.status = filterStatus
    if (filterLocation) params.location = filterLocation
    listStockBalances(params)
      .then(r => setBalances(r.data))
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load stock'))
      .finally(() => setLoading(false))
  }, [filterStatus, filterLocation])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-white">Stock Overview</h1>
        <p className="text-sm text-gray-500 mt-0.5">{balances.length} balance records</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
        >
          <option value="">All Statuses</option>
          <option value="IN_STOCK">In Stock</option>
          <option value="LOW_STOCK">Low Stock</option>
          <option value="OUT_OF_STOCK">Out of Stock</option>
        </select>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {['Item', 'SKU', 'Category', 'Location', 'Quantity', 'Reserved', 'Available', 'Unit', 'Avg Cost', 'Reorder Level', 'Status'].map(h => (
                  <th key={h} className="text-left text-xs text-gray-500 font-medium px-3 py-2 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {balances.map(b => (
                <tr key={b.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 py-3 text-gray-200 font-medium whitespace-nowrap">{b.item_name}</td>
                  <td className="px-3 py-3 text-gray-400 font-mono text-xs">{b.item_sku}</td>
                  <td className="px-3 py-3 text-gray-400">{b.category_name ?? '—'}</td>
                  <td className="px-3 py-3 text-gray-400 whitespace-nowrap">{b.location_name}</td>
                  <td className="px-3 py-3 text-gray-300">{b.quantity}</td>
                  <td className="px-3 py-3 text-gray-400">{b.reserved_quantity}</td>
                  <td className="px-3 py-3 text-gray-300 font-medium">{b.available_quantity}</td>
                  <td className="px-3 py-3 text-gray-400">{b.item_unit}</td>
                  <td className="px-3 py-3 text-gray-300">₹{b.average_cost}</td>
                  <td className="px-3 py-3 text-gray-400">{b.reorder_level}</td>
                  <td className="px-3 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_BADGE[b.stock_status]}`}>
                      {b.stock_status.replace('_', ' ')}
                    </span>
                  </td>
                </tr>
              ))}
              {balances.length === 0 && (
                <tr><td colSpan={11} className="px-3 py-8 text-center text-gray-600 text-sm">No stock data found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
