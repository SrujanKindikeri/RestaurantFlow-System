// =============================================================================
// RestaurantFlow — Profit & Loss Page
// Phase 13
// =============================================================================

import { useEffect, useState } from 'react'
import { getProfitLoss, type ProfitLoss } from '@/services/accounting'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string | number) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function Section({ title, rows, total, colour }: {
  title: string
  rows: { code: string; name: string; balance: string }[]
  total: string
  colour: string
}) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
      <div className="px-5 py-3 border-b border-gray-700 bg-gray-750">
        <h3 className={`text-sm font-semibold ${colour}`}>{title}</h3>
      </div>
      <table className="w-full text-sm">
        <tbody>
          {rows.map((row) => (
            <tr key={row.code} className="border-b border-gray-700/30">
              <td className="px-5 py-2.5 font-mono text-xs text-gray-500 w-20">{row.code}</td>
              <td className="px-5 py-2.5 text-gray-300 flex-1">{row.name}</td>
              <td className="px-5 py-2.5 text-right font-mono text-gray-300">₹{fmt(row.balance)}</td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={3} className="px-5 py-4 text-center text-gray-500 text-xs">No entries</td>
            </tr>
          )}
        </tbody>
        <tfoot>
          <tr className="border-t border-gray-600">
            <td colSpan={2} className="px-5 py-3 text-sm font-semibold text-gray-300">Total {title}</td>
            <td className={`px-5 py-3 text-right font-mono font-bold ${colour}`}>₹{fmt(total)}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

function SubtotalRow({ label, value, highlight = false }: { label: string; value: string; highlight?: boolean }) {
  const isNegative = Number(value) < 0
  return (
    <div className={`flex justify-between items-center px-5 py-4 rounded-xl border ${
      highlight
        ? isNegative
          ? 'bg-red-500/10 border-red-500/30'
          : 'bg-green-500/10 border-green-500/30'
        : 'bg-gray-800 border-gray-700'
    }`}>
      <span className={`font-semibold ${highlight ? 'text-white' : 'text-gray-300'}`}>{label}</span>
      <span className={`font-mono font-bold text-xl ${
        highlight
          ? isNegative ? 'text-red-400' : 'text-green-400'
          : 'text-white'
      }`}>
        ₹{fmt(value)}
      </span>
    </div>
  )
}

export function ProfitLossPage() {
  const { user } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [data, setData] = useState<ProfitLoss | null>(null)
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
    getProfitLoss(restaurantId, params)
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load P&L'))
      .finally(() => setLoading(false))
  }, [restaurantId, dateFrom, dateTo])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white">Profit & Loss</h1>
          <p className="text-sm text-gray-500 mt-1">Based on posted journal entries only</p>
        </div>
        <div className="flex gap-3">
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-blue-500" />
        </div>
      </div>

      {loading && <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-40 bg-gray-800 rounded-xl animate-pulse" />
      ))}</div>}
      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {data && (
        <div className="space-y-4">
          <Section title="Revenue" rows={data.revenue} total={data.total_revenue} colour="text-green-400" />
          <Section title="Cost of Goods Sold" rows={data.cogs} total={data.total_cogs} colour="text-amber-400" />
          <SubtotalRow label="Gross Profit" value={data.gross_profit} highlight />
          <Section title="Operating Expenses" rows={data.operating_expenses} total={data.total_operating_expenses} colour="text-red-400" />
          <SubtotalRow label="Operating Profit" value={data.operating_profit} highlight />
        </div>
      )}
    </div>
  )
}
