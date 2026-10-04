// =============================================================================
// RestaurantFlow — Menu / Product Report Page
// Phase 14
// =============================================================================

import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useTopSellingItems, useCategoryPerformance } from '@/hooks/useReporting'
import { getDateRange, formatCurrency } from '@/utils/reportingDates'
import type { DatePreset } from '@/utils/reportingDates'
import type { ReportFilters } from '@/services/reporting'
import { getExportUrl } from '@/services/reporting'

const DATE_PRESETS: { value: DatePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'last_7_days', label: '7 days' },
  { value: 'last_30_days', label: '30 days' },
  { value: 'this_month', label: 'This month' },
]

export function MenuReportPage() {
  const [preset, setPreset] = useState<DatePreset>('last_30_days')
  const [sortBy, setSortBy] = useState<'revenue' | 'quantity' | 'orders'>('revenue')
  const [limit, setLimit] = useState(10)
  const dateRange = getDateRange(preset)
  const filters: ReportFilters = {
    date_from: dateRange.date_from,
    date_to: dateRange.date_to,
    limit,
    sort_by: sortBy,
  }

  const { data: topItems, isLoading: topLoading, isError } = useTopSellingItems(filters)
  const { data: catData, isLoading: catLoading } = useCategoryPerformance(filters)

  const topRows = topItems?.data ?? []
  const catRows = catData?.data ?? []

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Menu Performance</h1>
          <p className="text-sm text-gray-500 mt-1">{dateRange.date_from} → {dateRange.date_to}</p>
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {DATE_PRESETS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setPreset(opt.value)}
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

      {/* Top selling items */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest">
            Top Selling Items
          </h2>
          <div className="flex gap-2 flex-wrap">
            <div className="flex gap-1">
              {(['revenue', 'quantity', 'orders'] as const).map(s => (
                <button
                  key={s}
                  onClick={() => setSortBy(s)}
                  className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
                    sortBy === s
                      ? 'bg-brand-500/20 border-brand-500/40 text-brand-400'
                      : 'border-gray-800 text-gray-600 hover:text-gray-400'
                  }`}
                >
                  by {s}
                </button>
              ))}
            </div>
            <select
              value={limit}
              onChange={e => setLimit(Number(e.target.value))}
              className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-300"
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
            </select>
            <a
              href={getExportUrl('menu_top_selling', filters)}
              className="text-xs text-brand-400 hover:text-brand-300 transition-colors flex items-center gap-1"
            >
              CSV ↓
            </a>
          </div>
        </div>

        {isError ? (
          <p className="text-sm text-red-400">Failed to load menu data.</p>
        ) : topLoading ? (
          <div className="h-56 bg-gray-800 animate-pulse rounded-lg" />
        ) : topRows.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-xs text-gray-600">
            No sales data for this period
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(180, topRows.length * 32)}>
            <BarChart data={topRows} layout="vertical" margin={{ top: 0, right: 50, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
              <XAxis
                type="number" tick={{ fill: '#6b7280', fontSize: 11 }}
                tickFormatter={(v: number) =>
                  sortBy === 'revenue' ? `₹${(v/1000).toFixed(0)}K` : String(Math.round(v))
                }
              />
              <YAxis
                type="category" dataKey="menu_item_name"
                tick={{ fill: '#d1d5db', fontSize: 11 }} width={130}
              />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                formatter={(v: number, name: string) =>
                  [sortBy === 'revenue' ? `₹${v.toLocaleString()}` : v, name]
                }
              />
              <Bar
                dataKey={sortBy === 'revenue' ? 'net_revenue' : sortBy === 'quantity' ? 'quantity_sold' : 'number_of_orders'}
                fill="#6366f1" radius={[0, 4, 4, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Category performance table */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-4">
          Category Performance
        </h2>
        {catLoading ? (
          <div className="space-y-2">
            {Array(5).fill(0).map((_, i) => <div key={i} className="h-8 bg-gray-800 animate-pulse rounded" />)}
          </div>
        ) : catRows.length === 0 ? (
          <p className="text-sm text-gray-600 py-4 text-center">No data</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left">
                  {['Category', 'Qty Sold', 'Gross Revenue', 'Net Revenue', '% of Sales', 'Avg Price'].map(h => (
                    <th key={h} className="pb-3 pr-4 text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {catRows.map(r => (
                  <tr key={r.category} className="hover:bg-gray-800/30 transition-colors">
                    <td className="py-2.5 pr-4 text-gray-300 font-medium">{r.category}</td>
                    <td className="py-2.5 pr-4 text-gray-400">{parseFloat(r.quantity_sold).toFixed(1)}</td>
                    <td className="py-2.5 pr-4 text-gray-400">{formatCurrency(r.gross_revenue)}</td>
                    <td className="py-2.5 pr-4 text-gray-200">{formatCurrency(r.net_revenue)}</td>
                    <td className="py-2.5 pr-4 text-gray-400">{parseFloat(r.sales_percentage).toFixed(1)}%</td>
                    <td className="py-2.5 pr-4 text-gray-400">
                      {r.average_item_value ? formatCurrency(r.average_item_value) : '—'}
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
