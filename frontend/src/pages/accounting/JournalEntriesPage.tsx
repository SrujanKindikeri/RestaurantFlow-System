// =============================================================================
// RestaurantFlow — Journal Entries Page
// Phase 13
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listJournalEntries, type JournalEntry } from '@/services/accounting'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_BADGE: Record<string, string> = {
  DRAFT:    'bg-gray-700 text-gray-400 border-gray-600',
  POSTED:   'bg-green-500/10 text-green-400 border-green-500/20',
  REVERSED: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  VOID:     'bg-gray-700 text-gray-500 border-gray-600',
}

const SOURCE_LABELS: Record<string, string> = {
  BILL: 'Sales',
  PAYMENT: 'Payment',
  PAYMENT_REFUND: 'Refund',
  SUPPLIER_INVOICE: 'Purchase',
  EXPENSE: 'Expense',
  INVENTORY_CONSUMPTION: 'COGS',
  CONSUMPTION_REVERSAL: 'COGS Rev.',
  PAYABLE_PAYMENT: 'Payable',
  MANUAL: 'Manual',
  PERIOD_CLOSE: 'Period Close',
}

const fmt = (v: string | number) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export function JournalEntriesPage() {
  const { user } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [entries, setEntries] = useState<JournalEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [sourceFilter, setSourceFilter] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  useEffect(() => {
    if (!restaurantId) { setLoading(false); return }
    setLoading(true)
    const params: Record<string, string> = { restaurant: restaurantId }
    if (statusFilter) params.status = statusFilter
    if (sourceFilter) params.source_type = sourceFilter
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo

    listJournalEntries(params)
      .then((res) => setEntries(res.results ?? []))
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load journal entries'))
      .finally(() => setLoading(false))
  }, [restaurantId, statusFilter, sourceFilter, dateFrom, dateTo])

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Journal Entries</h1>
          <p className="text-sm text-gray-500 mt-1">Double-entry accounting transactions</p>
        </div>
        <Link
          to="/accounting/journals/new"
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + Manual Entry
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="POSTED">Posted</option>
          <option value="REVERSED">Reversed</option>
          <option value="VOID">Void</option>
        </select>
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
        >
          <option value="">All Sources</option>
          {Object.entries(SOURCE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
          placeholder="From"
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
          placeholder="To"
        />
      </div>

      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-14 bg-gray-800 rounded animate-pulse" />
          ))}
        </div>
      )}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {!loading && !error && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-left">
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">Entry #</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">Date</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">Description</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium hidden md:table-cell">Source</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium text-right">Debit</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium text-right">Credit</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium">Status</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium hidden lg:table-cell">Balanced</th>
              </tr>
            </thead>
            <tbody>
              {entries.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                    No journal entries found.
                  </td>
                </tr>
              )}
              {entries.map((entry) => (
                <tr key={entry.id} className="border-b border-gray-700/50 hover:bg-gray-750">
                  <td className="px-4 py-3">
                    <Link
                      to={`/accounting/journals/${entry.id}`}
                      className="font-mono text-blue-400 hover:text-blue-300 text-xs"
                    >
                      {entry.entry_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{entry.entry_date}</td>
                  <td className="px-4 py-3 text-gray-300 max-w-xs truncate">{entry.description}</td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    <span className="text-xs text-gray-500">
                      {SOURCE_LABELS[entry.source_type] ?? entry.source_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300 font-mono text-xs">
                    ₹{fmt(entry.total_debits)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-300 font-mono text-xs">
                    ₹{fmt(entry.total_credits)}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs border ${STATUS_BADGE[entry.status] ?? ''}`}>
                      {entry.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    {entry.is_balanced
                      ? <span className="text-green-400 text-xs">✓</span>
                      : <span className="text-red-400 text-xs">✗ Imbalanced</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
