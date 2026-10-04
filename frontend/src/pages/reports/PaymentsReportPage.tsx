// =============================================================================
// RestaurantFlow — Payments Report Page
// Phase 14
// =============================================================================

import { useState } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { usePaymentSummary, usePaymentMethods } from '@/hooks/useReporting'
import { getDateRange, formatCurrency } from '@/utils/reportingDates'
import type { DatePreset } from '@/utils/reportingDates'
import type { ReportFilters } from '@/services/reporting'

const DATE_PRESETS: { value: DatePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'last_7_days', label: '7 days' },
  { value: 'last_30_days', label: '30 days' },
  { value: 'this_month', label: 'This month' },
]

const COLORS = ['#6366f1', '#22d3ee', '#f59e0b', '#10b981', '#f43f5e', '#a78bfa']

export function PaymentsReportPage() {
  const [preset, setPreset] = useState<DatePreset>('last_30_days')
  const dateRange = getDateRange(preset)
  const filters: ReportFilters = {
    date_from: dateRange.date_from,
    date_to: dateRange.date_to,
  }

  const { data: summary, isLoading: sumLoading } = usePaymentSummary(filters)
  const { data: methods, isLoading: methodsLoading } = usePaymentMethods(filters)

  const s = summary?.data
  const methodRows = methods?.data ?? []

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Payments Report</h1>
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

      {/* Summary grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Collected', value: formatCurrency(s?.total_paid), color: 'text-emerald-400' },
          { label: 'Cash', value: formatCurrency(s?.cash), color: 'text-blue-400' },
          { label: 'UPI', value: formatCurrency(s?.upi), color: 'text-purple-400' },
          { label: 'Card', value: formatCurrency(s?.card), color: 'text-yellow-400' },
          { label: 'Payment Count', value: String(s?.payment_count ?? '—'), color: 'text-gray-200' },
          { label: 'Refunds', value: formatCurrency(s?.refund_amount), color: 'text-red-400' },
          { label: 'Refund Count', value: String(s?.refund_count ?? '—'), color: 'text-red-400' },
          { label: 'Other', value: formatCurrency(s?.other), color: 'text-gray-400' },
        ].map(item => (
          <div key={item.label} className="rounded-xl bg-gray-900/60 border border-gray-800 px-4 py-3">
            <p className="text-xs text-gray-500 mb-1">{item.label}</p>
            {sumLoading
              ? <div className="h-6 w-16 bg-gray-800 animate-pulse rounded" />
              : <p className={`text-xl font-semibold ${item.color}`}>{item.value}</p>
            }
          </div>
        ))}
      </div>

      {/* Method breakdown */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-5">
          Payment Method Distribution
        </h2>
        {methodsLoading ? (
          <div className="h-48 bg-gray-800 animate-pulse rounded-lg" />
        ) : methodRows.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-xs text-gray-600">No payment data</div>
        ) : (
          <div className="flex flex-col sm:flex-row items-center gap-8">
            <ResponsiveContainer width={220} height={200}>
              <PieChart>
                <Pie
                  data={methodRows} dataKey="total" nameKey="payment_method"
                  cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={2}
                >
                  {methodRows.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                  formatter={(v: number) => [`₹${v.toLocaleString()}`]}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="flex-1 space-y-2 w-full">
              {methodRows.map((r, i) => (
                <div key={r.payment_method}>
                  <div className="flex justify-between text-sm mb-1">
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                      <span className="text-gray-300">{r.payment_method}</span>
                    </div>
                    <span className="text-gray-400">{parseFloat(r.percentage).toFixed(1)}% · {r.count} txns</span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full"
                      style={{ width: `${Math.min(parseFloat(r.percentage), 100)}%`, background: COLORS[i % COLORS.length] }}
                    />
                  </div>
                  <p className="text-xs text-gray-600 mt-0.5">{formatCurrency(r.total)}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
