// =============================================================================
// RestaurantFlow — Branch Performance Report Page
// Phase 14
// =============================================================================

import { useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useBranchPerformance } from '@/hooks/useReporting'
import { getDateRange, formatCurrency } from '@/utils/reportingDates'
import type { DatePreset } from '@/utils/reportingDates'
import type { ReportFilters } from '@/services/reporting'

const DATE_PRESETS: { value: DatePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'last_7_days', label: '7 days' },
  { value: 'last_30_days', label: '30 days' },
  { value: 'this_month', label: 'This month' },
]

export function BranchesReportPage() {
  const [preset, setPreset] = useState<DatePreset>('last_30_days')
  const dateRange = getDateRange(preset)
  const filters: ReportFilters = {
    date_from: dateRange.date_from,
    date_to: dateRange.date_to,
  }

  const { data, isLoading, isError } = useBranchPerformance(filters)
  const rows = data?.data ?? []

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Branch Performance</h1>
          <p className="text-sm text-gray-500 mt-1">{dateRange.date_from} → {dateRange.date_to}</p>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {DATE_PRESETS.map(opt => (
            <button key={opt.value} onClick={() => setPreset(opt.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                preset === opt.value
                  ? 'bg-brand-500/20 border-brand-500/40 text-brand-400'
                  : 'bg-gray-900/60 border-gray-800 text-gray-500 hover:text-gray-300'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {isError && (
        <div className="rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-3 text-sm text-red-400">
          Failed to load branch data.
        </div>
      )}

      {/* Revenue comparison chart */}
      {!isLoading && rows.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
          <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-4">Revenue by Branch</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={rows} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="branch_name" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }}
                tickFormatter={(v: number) => `₹${(v / 1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                formatter={(v: number) => [`₹${v.toLocaleString()}`, 'Revenue']}
              />
              <Bar dataKey="revenue" fill="#6366f1" radius={[4, 4, 0, 0]} name="Revenue" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Detailed table */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-4">
          Branch Detail
        </h2>
        {isLoading ? (
          <div className="space-y-2">
            {Array(4).fill(0).map((_, i) => <div key={i} className="h-10 bg-gray-800 animate-pulse rounded" />)}
          </div>
        ) : rows.length === 0 ? (
          <p className="text-sm text-gray-600 py-6 text-center">No branch data for this period</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr>
                  {['Branch', 'Orders', 'Bills', 'Revenue', 'Payments', 'Discounts', 'Avg Bill', 'Gross Margin'].map(h => (
                    <th key={h} className="pb-3 pr-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {rows.map(r => (
                  <tr key={r.branch_id} className="hover:bg-gray-800/30 transition-colors">
                    <td className="py-3 pr-4 font-medium text-gray-200">{r.branch_name}</td>
                    <td className="py-3 pr-4 text-gray-400">{r.orders}</td>
                    <td className="py-3 pr-4 text-gray-400">{r.bills}</td>
                    <td className="py-3 pr-4 text-emerald-400 font-medium">{formatCurrency(r.revenue)}</td>
                    <td className="py-3 pr-4 text-gray-400">{formatCurrency(r.payments)}</td>
                    <td className="py-3 pr-4 text-gray-400">{formatCurrency(r.discounts)}</td>
                    <td className="py-3 pr-4 text-gray-400">
                      {r.average_bill_value ? formatCurrency(r.average_bill_value) : '—'}
                    </td>
                    <td className="py-3 pr-4 text-gray-400">
                      {r.gross_margin ? `${parseFloat(r.gross_margin).toFixed(1)}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
