// =============================================================================
// RestaurantFlow — Accounting Periods Page
// Phase 13
// =============================================================================

import { useEffect, useState } from 'react'
import { listPeriods, closePeriod, reopenPeriod, type AccountingPeriod } from '@/services/accounting'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_BADGE: Record<string, string> = {
  OPEN:             'bg-green-500/10 text-green-400 border-green-500/20',
  CLOSE_REQUESTED:  'bg-amber-500/10 text-amber-400 border-amber-500/20',
  CLOSED:           'bg-gray-700 text-gray-400 border-gray-600',
}

export function AccountingPeriodsPage() {
  const { user } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [periods, setPeriods] = useState<AccountingPeriod[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const load = () => {
    if (!restaurantId) { setLoading(false); return }
    listPeriods({ restaurant: restaurantId })
      .then(setPeriods)
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load periods'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [restaurantId])

  const handleClose = async (period: AccountingPeriod) => {
    setActionError(null)
    setActionLoading(period.id)
    try {
      await closePeriod(period.id, '')
      load()
    } catch (e: any) {
      setActionError(e?.response?.data?.detail ?? 'Failed to close period')
    } finally {
      setActionLoading(null)
    }
  }

  const handleReopen = async (period: AccountingPeriod) => {
    setActionError(null)
    setActionLoading(period.id)
    try {
      await reopenPeriod(period.id, '')
      load()
    } catch (e: any) {
      setActionError(e?.response?.data?.detail ?? 'Failed to reopen period')
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Accounting Periods</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage open and closed periods. Posted entries cannot be added to closed periods.
        </p>
      </div>

      {actionError && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{actionError}</div>
      )}

      {loading && (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-16 bg-gray-800 rounded-xl animate-pulse" />
        ))}</div>
      )}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {!loading && !error && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="px-5 py-3 text-xs text-gray-500 font-medium text-left">Period</th>
                <th className="px-5 py-3 text-xs text-gray-500 font-medium text-left hidden sm:table-cell">Start Date</th>
                <th className="px-5 py-3 text-xs text-gray-500 font-medium text-left hidden sm:table-cell">End Date</th>
                <th className="px-5 py-3 text-xs text-gray-500 font-medium text-left">Status</th>
                <th className="px-5 py-3 text-xs text-gray-500 font-medium text-left hidden md:table-cell">Closed By</th>
                <th className="px-5 py-3 text-xs text-gray-500 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {periods.length === 0 && (
                <tr><td colSpan={6} className="px-5 py-8 text-center text-gray-500">No periods found.</td></tr>
              )}
              {periods.map((period) => (
                <tr key={period.id} className="border-b border-gray-700/50 hover:bg-gray-750">
                  <td className="px-5 py-3 text-gray-300 font-medium">{period.name}</td>
                  <td className="px-5 py-3 text-gray-400 text-xs hidden sm:table-cell">{period.start_date}</td>
                  <td className="px-5 py-3 text-gray-400 text-xs hidden sm:table-cell">{period.end_date}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs border ${STATUS_BADGE[period.status] ?? ''}`}>
                      {period.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-500 text-xs hidden md:table-cell">
                    {period.closed_by_email ?? '—'}
                  </td>
                  <td className="px-5 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      {period.status !== 'CLOSED' && (
                        <button
                          onClick={() => handleClose(period)}
                          disabled={actionLoading === period.id}
                          className="px-3 py-1 text-xs bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded hover:bg-amber-500/20 transition-colors disabled:opacity-50"
                        >
                          {actionLoading === period.id ? '...' : 'Close'}
                        </button>
                      )}
                      {period.status === 'CLOSED' && (
                        <button
                          onClick={() => handleReopen(period)}
                          disabled={actionLoading === period.id}
                          className="px-3 py-1 text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded hover:bg-blue-500/20 transition-colors disabled:opacity-50"
                        >
                          {actionLoading === period.id ? '...' : 'Reopen'}
                        </button>
                      )}
                    </div>
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
