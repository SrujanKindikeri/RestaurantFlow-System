// =============================================================================
// RestaurantFlow — Kitchen Report Page
// Phase 14
// =============================================================================

import { useState } from 'react'
import { useKitchenPerformance } from '@/hooks/useReporting'
import { getDateRange, formatSeconds } from '@/utils/reportingDates'
import type { DatePreset } from '@/utils/reportingDates'
import type { ReportFilters } from '@/services/reporting'

const DATE_PRESETS: { value: DatePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: 'last_7_days', label: '7 days' },
  { value: 'last_30_days', label: '30 days' },
]

function MetricRow({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-gray-800/60 last:border-0">
      <div>
        <p className="text-sm text-gray-300">{label}</p>
        {sub && <p className="text-xs text-gray-600 mt-0.5">{sub}</p>}
      </div>
      <p className="text-base font-semibold text-gray-100">{value}</p>
    </div>
  )
}

export function KitchenReportPage() {
  const [preset, setPreset] = useState<DatePreset>('today')
  const dateRange = getDateRange(preset)
  const filters: ReportFilters = {
    date_from: dateRange.date_from,
    date_to: dateRange.date_to,
  }

  const { data, isLoading, isError } = useKitchenPerformance(filters)
  const k = data?.data

  const readyRate = k && k.orders_received > 0
    ? `${((k.orders_ready / k.orders_received) * 100).toFixed(1)}%`
    : '—'

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Kitchen Performance</h1>
          <p className="text-sm text-gray-500 mt-1">{dateRange.label}</p>
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
          Failed to load kitchen data.
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Received', value: String(k?.orders_received ?? '—'), color: 'text-blue-400' },
          { label: 'Ready', value: String(k?.orders_ready ?? '—'), color: 'text-emerald-400' },
          { label: 'Pending', value: String(k?.orders_pending ?? '—'), color: 'text-yellow-400' },
          { label: 'Cancelled', value: String(k?.orders_cancelled ?? '—'), color: 'text-red-400' },
        ].map(item => (
          <div key={item.label} className="rounded-xl bg-gray-900/60 border border-gray-800 px-4 py-3">
            <p className="text-xs text-gray-500 mb-1">{item.label}</p>
            {isLoading
              ? <div className="h-7 w-10 bg-gray-800 animate-pulse rounded" />
              : <p className={`text-2xl font-bold ${item.color}`}>{item.value}</p>
            }
          </div>
        ))}
      </div>

      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3">Preparation Time</h2>
        {isLoading ? (
          <div className="space-y-2">
            {Array(4).fill(0).map((_, i) => <div key={i} className="h-8 bg-gray-800 animate-pulse rounded" />)}
          </div>
        ) : (
          <>
            <MetricRow
              label="Average Preparation Time"
              value={formatSeconds(k?.average_preparation_time_seconds)}
              sub="Ready time minus started time. Null if no timestamps."
            />
            <MetricRow
              label="Median Preparation Time"
              value={formatSeconds(k?.median_preparation_time_seconds)}
            />
            <MetricRow
              label="Maximum Preparation Time"
              value={formatSeconds(k?.maximum_preparation_time_seconds)}
            />
            <MetricRow
              label="Order Ready Rate"
              value={readyRate}
              sub="Ready orders ÷ Total received"
            />
          </>
        )}
      </div>
    </div>
  )
}
