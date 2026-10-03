// =============================================================================
// RestaurantFlow — Stock Movement History Page
// Phase 10
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { listStockMovements } from '@/services/inventory'
import type { StockMovement, MovementType } from '@/types'

const TYPE_BADGE: Record<string, string> = {
  PURCHASE:        'bg-green-500/10 text-green-400 border-green-500/20',
  PURCHASE_RETURN: 'bg-red-500/10 text-red-400 border-red-500/20',
  TRANSFER_IN:     'bg-brand-500/10 text-brand-400 border-brand-500/20',
  TRANSFER_OUT:    'bg-blue-500/10 text-blue-400 border-blue-500/20',
  WASTAGE:         'bg-amber-500/10 text-amber-400 border-amber-500/20',
  ADJUSTMENT_IN:   'bg-teal-500/10 text-teal-400 border-teal-500/20',
  ADJUSTMENT_OUT:  'bg-orange-500/10 text-orange-400 border-orange-500/20',
  CONSUMPTION:     'bg-purple-500/10 text-purple-400 border-purple-500/20',
  OPENING_STOCK:   'bg-gray-600/20 text-gray-400 border-gray-600',
  CORRECTION:      'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
}

export function StockHistoryPage() {
  const [movements, setMovements] = useState<StockMovement[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterType, setFilterType] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filterType) params.movement_type = filterType
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    listStockMovements(params)
      .then(r => setMovements(r.data))
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load movements'))
      .finally(() => setLoading(false))
  }, [filterType, dateFrom, dateTo])

  useEffect(() => { load() }, [load])

  const movementTypes: MovementType[] = [
    'PURCHASE', 'PURCHASE_RETURN', 'TRANSFER_IN', 'TRANSFER_OUT',
    'WASTAGE', 'ADJUSTMENT_IN', 'ADJUSTMENT_OUT',
    'CONSUMPTION', 'OPENING_STOCK', 'CORRECTION',
  ]

  return (
    <div className="p-6 space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-white">Stock Movement History</h1>
        <p className="text-sm text-gray-500 mt-0.5">{movements.length} movements (most recent first)</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select value={filterType} onChange={e => setFilterType(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
          <option value="">All Types</option>
          {movementTypes.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} title="From date"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} title="To date"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
        {(filterType || dateFrom || dateTo) && (
          <button onClick={() => { setFilterType(''); setDateFrom(''); setDateTo('') }}
            className="px-3 py-2 text-xs text-gray-500 hover:text-gray-300 border border-gray-700 rounded-lg">
            Clear
          </button>
        )}
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-10 bg-gray-800 rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {['Date', 'Type', 'Item', 'Location', 'Quantity', 'Unit', 'Unit Cost', 'Total Cost', 'Reference', 'Performed By'].map(h => (
                  <th key={h} className="text-left text-xs text-gray-500 font-medium px-3 py-2 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {movements.map(m => (
                <tr key={m.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 py-2.5 text-gray-500 text-xs whitespace-nowrap">
                    {new Date(m.created_at).toLocaleDateString()}{' '}
                    <span className="text-gray-700">{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </td>
                  <td className="px-3 py-2.5">
                    <span className={`text-xs px-2 py-0.5 rounded-full border whitespace-nowrap ${TYPE_BADGE[m.movement_type] ?? 'bg-gray-700 text-gray-400 border-gray-600'}`}>
                      {m.movement_type.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-3 py-2.5">
                    <p className="text-gray-200 whitespace-nowrap">{m.item_name}</p>
                    <p className="text-gray-600 font-mono text-xs">{m.item_sku}</p>
                  </td>
                  <td className="px-3 py-2.5 text-gray-400 text-xs whitespace-nowrap">{m.location_name}</td>
                  <td className="px-3 py-2.5 text-gray-300 font-medium">{m.quantity}</td>
                  <td className="px-3 py-2.5 text-gray-400">{m.item_unit}</td>
                  <td className="px-3 py-2.5 text-gray-400">₹{m.unit_cost}</td>
                  <td className="px-3 py-2.5 text-gray-300 font-medium">₹{m.total_cost}</td>
                  <td className="px-3 py-2.5 text-gray-500 text-xs font-mono">
                    {m.reference_type ? `${m.reference_type.replace(/_/g, ' ')}` : '—'}
                  </td>
                  <td className="px-3 py-2.5 text-gray-400 text-xs whitespace-nowrap">{m.performed_by_email}</td>
                </tr>
              ))}
              {movements.length === 0 && (
                <tr><td colSpan={10} className="px-3 py-8 text-center text-gray-600 text-sm">No movements found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
