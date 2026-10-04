// =============================================================================
// RestaurantFlow — Sales Report Page
// Phase 14
// =============================================================================

import { useState } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar,
} from 'recharts'
import { useSalesSummary, useSalesTrend, useHourlySales } from '@/hooks/useReporting'
import { getDateRange, formatCurrency } from '@/utils/reportingDates'
import type { DatePreset } from '@/utils/reportingDates'
import type { ReportFilters } from '@/services/reporting'
import { getExportUrl } from '@/services/reporting'

const DATE_PRESETS: { value: DatePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'last_7_days', label: 'Last 7 days' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'this_month', label: 'This month' },
  { value: 'prev_month', label: 'Prev month' },
]

function SummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-800/60 last:border-0">
      <span className="text-sm text-gray-400">{label}</span>
      <span className="text-sm font-medium text-gray-100">{value}</span>
    </div>
  )
}

export function SalesReportPage() {
  const [preset, setPreset] = useState<DatePreset>('last_7_days')
  const [granularity, setGranularity] = useState<'daily' | 'weekly' | 'monthly'>('daily')
  const dateRange = getDateRange(preset)
  const filters: ReportFilters = { date_from: dateRange.date_from, date_to: dateRange.date_to }

  const { data: summary, isLoading: sumLoading, isError: sumError } = useSalesSummary(filters)
  const { data: trend, isLoading: trendLoading } = useSalesTrend({ ...filters, granularity })
  const { data: hourly, isLoading: hourlyLoading } = useHourlySales(filters)

  const s = summary?.data
  const trendRows = trend?.data ?? []
  const hourlyRows = hourly?.data ?? []

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Sales Report</h1>
          <p className="text-sm text-gray-500 mt-1">{dateRange.label} · {dateRange.date_from} → {dateRange.date_to}</p>
        </div>
        <div className="flex gap-2 flex-wrap">
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

      {/* Summary card */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest">Sales Summary</h2>
          <a
            href={getExportUrl('sales_summary', filters)}
            className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
          >
            Export CSV ↓
          </a>
        </div>
        {sumError ? (
          <p className="text-sm text-red-400">Failed to load summary.</p>
        ) : sumLoading ? (
          <div className="space-y-2">
            {Array(6).fill(0).map((_, i) => (
              <div key={i} className="h-6 bg-gray-800 animate-pulse rounded" />
            ))}
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-x-8">
            <div>
              <SummaryRow label="Gross Sales" value={formatCurrency(s?.gross_sales, '₹')} />
              <SummaryRow label="Discount" value={formatCurrency(s?.discount_amount, '₹')} />
              <SummaryRow label="Taxable Amount" value={formatCurrency(s?.taxable_amount, '₹')} />
              <SummaryRow label="Tax Amount" value={formatCurrency(s?.tax_amount, '₹')} />
            </div>
            <div>
              <SummaryRow label="Net Sales" value={formatCurrency(s?.net_sales, '₹')} />
              <SummaryRow label="Bills" value={String(s?.number_of_bills ?? '—')} />
              <SummaryRow label="Avg Bill" value={formatCurrency(s?.average_bill_value, '₹')} />
              <SummaryRow label="Rounding" value={formatCurrency(s?.rounding_amount, '₹')} />
            </div>
          </div>
        )}
      </div>

      {/* Trend Chart */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest">Sales Trend</h2>
          <div className="flex gap-1.5">
            {(['daily', 'weekly', 'monthly'] as const).map(g => (
              <button
                key={g}
                onClick={() => setGranularity(g)}
                className={`px-2.5 py-1 rounded text-xs font-medium border transition-colors ${
                  granularity === g
                    ? 'bg-brand-500/20 border-brand-500/40 text-brand-400'
                    : 'border-gray-800 text-gray-600 hover:text-gray-400'
                }`}
              >
                {g.charAt(0).toUpperCase() + g.slice(1)}
              </button>
            ))}
          </div>
        </div>
        {trendLoading ? (
          <div className="h-52 bg-gray-800 animate-pulse rounded-lg" />
        ) : trendRows.length === 0 ? (
          <div className="h-52 flex items-center justify-center text-xs text-gray-600">No data for this period</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendRows} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="date" tick={{ fill: '#6b7280', fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickFormatter={(v: number) => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                formatter={(v: number) => [`₹${v.toLocaleString()}`]}
              />
              <Line type="monotone" dataKey="net_sales" stroke="#6366f1" strokeWidth={2} dot={false} name="Net Sales" />
              <Line type="monotone" dataKey="gross_sales" stroke="#9ca3af" strokeWidth={1} dot={false} strokeDasharray="4 2" name="Gross Sales" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Hourly Chart */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-4">Peak Hours</h2>
        {hourlyLoading ? (
          <div className="h-48 bg-gray-800 animate-pulse rounded-lg" />
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={hourlyRows} margin={{ top: 4, right: 4, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis dataKey="hour" tick={{ fill: '#6b7280', fontSize: 10 }}
                tickFormatter={(h: number) => `${h}:00`} />
              <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} tickFormatter={(v: number) => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                formatter={(v: number) => [`₹${v.toLocaleString()}`, 'Sales']}
                labelFormatter={(h: number) => `${h}:00 – ${h+1}:00`}
              />
              <Bar dataKey="sales" fill="#6366f1" radius={[3, 3, 0, 0]} name="Sales" />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
