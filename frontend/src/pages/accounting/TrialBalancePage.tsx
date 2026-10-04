// =============================================================================
// RestaurantFlow — Trial Balance Page
// Phase 13
// =============================================================================

import { useEffect, useState } from 'react'
import { getTrialBalance, type TrialBalance, type TrialBalanceRow } from '@/services/accounting'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string | number) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const TYPE_COLOUR: Record<string, string> = {
  ASSET: 'text-blue-400', LIABILITY: 'text-red-400',
  EQUITY: 'text-purple-400', REVENUE: 'text-green-400', EXPENSE: 'text-amber-400',
}

export function TrialBalancePage() {
  const { user } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [data, setData] = useState<TrialBalance | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')

  useEffect(() => {
    if (!restaurantId) { setLoading(false); return }
    setLoading(true)
    const params: Record<string, string> = {}
    if (dateFrom) params.date_from = dateFrom
    if (dateTo) params.date_to = dateTo
    getTrialBalance(restaurantId, params)
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load trial balance'))
      .finally(() => setLoading(false))
  }, [restaurantId, dateFrom, dateTo])

  // Group rows by type
  const byType: Record<string, TrialBalanceRow[]> = {}
  data?.accounts.forEach((row) => {
    if (!byType[row.account_type]) byType[row.account_type] = []
    byType[row.account_type].push(row)
  })

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Trial Balance</h1>
          <p className="text-sm text-gray-500 mt-1">
            Total debits must equal total credits. Any variance indicates an accounting error.
          </p>
        </div>
        <div className="flex gap-3">
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
        </div>
      </div>

      {/* Balance status banner */}
      {data && (
        <div className={`rounded-xl p-4 border flex items-center justify-between ${
          data.is_balanced
            ? 'bg-green-500/10 border-green-500/30'
            : 'bg-red-500/10 border-red-500/30'
        }`}>
          <div>
            <p className={`font-semibold ${data.is_balanced ? 'text-green-400' : 'text-red-400'}`}>
              {data.is_balanced ? '✓ Trial Balance is BALANCED' : '✗ Trial Balance is IMBALANCED'}
            </p>
            {!data.is_balanced && (
              <p className="text-sm text-red-400 mt-1">
                Variance: ₹{fmt(data.variance)} — investigate your journal entries.
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">Total Debits</p>
            <p className="text-xl font-bold text-white">₹{fmt(data.grand_debit)}</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">Total Credits</p>
            <p className="text-xl font-bold text-white">₹{fmt(data.grand_credit)}</p>
          </div>
        </div>
      )}

      {loading && (
        <div className="space-y-2">{Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-10 bg-gray-800 rounded animate-pulse" />
        ))}</div>
      )}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {data && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="px-4 py-3 text-xs text-gray-500 font-medium text-left">Code</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium text-left">Account Name</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium text-left hidden md:table-cell">Type</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium text-right">Debit</th>
                <th className="px-4 py-3 text-xs text-gray-500 font-medium text-right">Credit</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(byType).map(([type, rows]) => (
                <>
                  <tr key={`header-${type}`} className="bg-gray-750/50">
                    <td colSpan={5} className={`px-4 py-2 text-xs font-semibold uppercase tracking-wider ${TYPE_COLOUR[type] ?? 'text-gray-400'}`}>
                      {type}
                    </td>
                  </tr>
                  {rows.map((row) => (
                    <tr key={row.account_code} className="border-b border-gray-700/30 hover:bg-gray-750">
                      <td className="px-4 py-2.5 font-mono text-xs text-gray-400">{row.account_code}</td>
                      <td className="px-4 py-2.5 text-gray-300">{row.account_name}</td>
                      <td className="px-4 py-2.5 hidden md:table-cell">
                        <span className="text-xs text-gray-500">{row.normal_balance}</span>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-gray-300">
                        {Number(row.debit_total) > 0 ? `₹${fmt(row.debit_total)}` : '—'}
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono text-gray-300">
                        {Number(row.credit_total) > 0 ? `₹${fmt(row.credit_total)}` : '—'}
                      </td>
                    </tr>
                  ))}
                </>
              ))}
              {/* Totals row */}
              <tr className="border-t-2 border-gray-600 font-semibold">
                <td colSpan={3} className="px-4 py-3 text-gray-300 text-sm">TOTALS</td>
                <td className="px-4 py-3 text-right font-mono text-white">₹{fmt(data.grand_debit)}</td>
                <td className="px-4 py-3 text-right font-mono text-white">₹{fmt(data.grand_credit)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
