// =============================================================================
// RestaurantFlow — Balance Sheet Page
// Phase 13
// =============================================================================

import { useEffect, useState } from 'react'
import { getBalanceSheet, type BalanceSheet } from '@/services/accounting'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string | number) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function BSSection({ title, rows, total, colour }: {
  title: string
  rows: { code: string; name: string; balance: string }[]
  total: string
  colour: string
}) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-700 bg-gray-750">
        <h3 className={`text-sm font-semibold uppercase tracking-wide ${colour}`}>{title}</h3>
      </div>
      <table className="w-full text-sm">
        <tbody>
          {rows.map((row) => (
            <tr key={row.code} className="border-b border-gray-700/30">
              <td className="px-5 py-2.5 font-mono text-xs text-gray-500 w-20">{row.code}</td>
              <td className="px-5 py-2.5 text-gray-300">{row.name}</td>
              <td className="px-5 py-2.5 text-right font-mono text-gray-300">₹{fmt(row.balance)}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={3} className="px-5 py-4 text-center text-gray-500 text-xs">No entries</td></tr>
          )}
        </tbody>
        <tfoot>
          <tr className="border-t border-gray-600">
            <td colSpan={2} className="px-5 py-3 font-semibold text-gray-300">Total {title}</td>
            <td className={`px-5 py-3 text-right font-mono font-bold ${colour}`}>₹{fmt(total)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

export function BalanceSheetPage() {
  const { user } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [data, setData] = useState<BalanceSheet | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [asOfDate, setAsOfDate] = useState('')

  useEffect(() => {
    if (!restaurantId) { setLoading(false); return }
    setLoading(true)
    const params: Record<string, string> = {}
    if (asOfDate) params.as_of_date = asOfDate
    getBalanceSheet(restaurantId, params)
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load balance sheet'))
      .finally(() => setLoading(false))
  }, [restaurantId, asOfDate])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Balance Sheet</h1>
          <p className="text-sm text-gray-500 mt-1">Assets = Liabilities + Equity</p>
        </div>
        <input type="date" value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500"
          placeholder="As of date" />
      </div>

      {/* Balance check */}
      {data && (
        <div className={`rounded-xl p-4 border flex items-center justify-between flex-wrap gap-4 ${
          data.is_balanced
            ? 'bg-green-500/10 border-green-500/30'
            : 'bg-red-500/10 border-red-500/30'
        }`}>
          <p className={`font-semibold ${data.is_balanced ? 'text-green-400' : 'text-red-400'}`}>
            {data.is_balanced
              ? '✓ Assets = Liabilities + Equity'
              : `✗ Balance Sheet is IMBALANCED — Variance: ₹${fmt(data.variance)}`
            }
          </p>
          <div className="flex gap-8">
            <div>
              <p className="text-xs text-gray-500">Total Assets</p>
              <p className="text-xl font-bold text-blue-400">₹{fmt(data.total_assets)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Liabilities + Equity</p>
              <p className="text-xl font-bold text-white">₹{fmt(data.total_liabilities_and_equity)}</p>
            </div>
          </div>
        </div>
      )}

      {loading && <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-40 bg-gray-800 rounded-xl animate-pulse" />
      ))}</div>}
      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {data && (
        <div className="grid lg:grid-cols-2 gap-6">
          {/* Left: Assets */}
          <BSSection title="Assets" rows={data.assets} total={data.total_assets} colour="text-blue-400" />

          {/* Right: Liabilities + Equity */}
          <div className="space-y-4">
            <BSSection title="Liabilities" rows={data.liabilities} total={data.total_liabilities} colour="text-red-400" />
            <BSSection title="Equity" rows={data.equity} total={data.total_equity} colour="text-purple-400" />

            <div className="flex justify-between items-center px-5 py-4 rounded-xl bg-gray-800 border border-gray-700">
              <span className="font-semibold text-gray-300">Total Liabilities & Equity</span>
              <span className="font-mono font-bold text-xl text-white">
                ₹{fmt(data.total_liabilities_and_equity)}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
