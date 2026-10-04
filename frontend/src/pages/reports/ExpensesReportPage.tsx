// =============================================================================
// RestaurantFlow — Expenses Report Page
// Phase 14
// =============================================================================

import { useState } from 'react'
import { useExpenses, usePayables } from '@/hooks/useReporting'
import { getDateRange, formatCurrency } from '@/utils/reportingDates'
import type { DatePreset } from '@/utils/reportingDates'
import type { ReportFilters } from '@/services/reporting'

const DATE_PRESETS: { value: DatePreset; label: string }[] = [
  { value: 'this_month', label: 'This month' },
  { value: 'prev_month', label: 'Prev month' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'last_7_days', label: 'Last 7 days' },
]

export function ExpensesReportPage() {
  const [preset, setPreset] = useState<DatePreset>('this_month')
  const dateRange = getDateRange(preset)
  const filters: ReportFilters = {
    date_from: dateRange.date_from,
    date_to: dateRange.date_to,
  }

  const { data: expData, isLoading: expLoading } = useExpenses(filters)
  const { data: payData, isLoading: payLoading } = usePayables(filters)

  const exp = expData?.data as Record<string, unknown> | undefined
  const pay = payData?.data as Record<string, unknown> | undefined

  const catBreakdown = (exp?.category_breakdown ?? []) as Array<Record<string, string>>
  const branchBreakdown = (exp?.branch_breakdown ?? []) as Array<Record<string, string>>

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Expenses & Payables</h1>
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

      {/* Expense summary */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { label: 'Total Expenses', key: 'total_expenses', color: 'text-gray-200' },
          { label: 'Approved', key: 'approved_expenses', color: 'text-emerald-400' },
          { label: 'Pending Approval', key: 'pending_expenses', color: 'text-yellow-400' },
          { label: 'Unpaid', key: 'unpaid_expenses', color: 'text-red-400' },
          { label: 'Paid', key: 'paid_expenses', color: 'text-blue-400' },
        ].map(item => (
          <div key={item.label} className="rounded-xl bg-gray-900/60 border border-gray-800 px-4 py-3">
            <p className="text-xs text-gray-500 mb-1">{item.label}</p>
            {expLoading
              ? <div className="h-6 w-16 bg-gray-800 animate-pulse rounded" />
              : <p className={`text-xl font-semibold ${item.color}`}>
                  {formatCurrency(exp?.[item.key] as string)}
                </p>
            }
          </div>
        ))}
      </div>

      {/* Payables summary */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-4">Payables Overview</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Total Payables', key: 'total_payables', color: 'text-gray-200' },
            { label: 'Outstanding', key: 'outstanding_payables', color: 'text-yellow-400' },
            { label: 'Overdue', key: 'overdue_payables', color: 'text-red-400' },
            { label: 'Paid', key: 'paid', color: 'text-emerald-400' },
          ].map(item => (
            <div key={item.label}>
              <p className="text-xs text-gray-500">{item.label}</p>
              {payLoading
                ? <div className="h-6 w-14 bg-gray-800 animate-pulse rounded mt-1" />
                : <p className={`text-lg font-semibold mt-1 ${item.color}`}>
                    {formatCurrency(pay?.[item.key] as string)}
                  </p>
              }
            </div>
          ))}
        </div>
      </div>

      {/* Category breakdown */}
      {catBreakdown.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
          <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-4">
            Approved Expenses by Category
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr>
                {['Category', 'Amount', '% of Total'].map(h => (
                  <th key={h} className="pb-3 pr-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/60">
              {catBreakdown.map(r => (
                <tr key={r.category}>
                  <td className="py-2.5 pr-4 text-gray-300">{r.category}</td>
                  <td className="py-2.5 pr-4 text-gray-200">{formatCurrency(r.amount)}</td>
                  <td className="py-2.5 pr-4 text-gray-400">
                    {r.percentage ? `${parseFloat(r.percentage).toFixed(1)}%` : '—'}
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
