// =============================================================================
// RestaurantFlow — Financial Dashboard
// Phase 12
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getFinancialDashboard } from '@/services/financials'
import type { FinancialDashboard } from '@/types'

const fmt = (v: string | number) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const STATUS_BADGE: Record<string, string> = {
  DRAFT:      'bg-gray-700 text-gray-400 border-gray-600',
  SUBMITTED:  'bg-blue-500/10 text-blue-400 border-blue-500/20',
  APPROVED:   'bg-green-500/10 text-green-400 border-green-500/20',
  REJECTED:   'bg-red-500/10 text-red-400 border-red-500/20',
  CANCELLED:  'bg-gray-700 text-gray-500 border-gray-600',
}

interface StatCardProps {
  label: string
  value: number | string
  to: string
  variant?: 'default' | 'warning' | 'danger' | 'info' | 'success'
}

function StatCard({ label, value, to, variant = 'default' }: StatCardProps) {
  const colours = {
    default: 'text-white',
    warning: 'text-amber-400',
    danger:  'text-red-400',
    info:    'text-blue-400',
    success: 'text-green-400',
  }
  return (
    <Link
      to={to}
      className="bg-gray-800 border border-gray-700 rounded-xl p-5 hover:border-gray-600 transition-colors"
    >
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-3xl font-bold ${colours[variant]}`}>{value}</p>
    </Link>
  )
}

export function FinancialDashboard() {
  const [data, setData] = useState<FinancialDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getFinancialDashboard()
      .then(setData)
      .catch((e) => setError(e?.response?.data?.message ?? 'Failed to load financial dashboard'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-white">Financial Operations</h1>
        <p className="text-sm text-gray-500 mt-1">Expenses, payables, and financial overview</p>
      </div>

      {loading && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-5 animate-pulse h-24" />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {data && (
        <>
          {/* Expense KPIs */}
          <section>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">Expenses</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              <StatCard label="Total Expenses"    value={data.total_expenses}    to="/financials/expenses" />
              <StatCard label="Pending Approval"  value={data.pending_approval}  to="/financials/expenses?status=SUBMITTED" variant="warning" />
              <StatCard label="Approved"          value={data.approved_expenses} to="/financials/expenses?status=APPROVED" variant="success" />
              <StatCard label="Rejected"          value={data.rejected_expenses} to="/financials/expenses?status=REJECTED" variant="danger" />
              <StatCard label="Unpaid"            value={data.unpaid_expenses}   to="/financials/expenses?payment_status=UNPAID" variant="warning" />
              <StatCard label="Partially Paid"    value={data.partially_paid}    to="/financials/payables?status=PARTIALLY_PAID" variant="info" />
              <StatCard label="Overdue Payables"  value={data.overdue_payables}  to="/financials/payables?status=OVERDUE" variant="danger" />
            </div>
          </section>

          {/* Payable amounts */}
          <section>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">Payables Summary</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Total Payable</p>
                <p className="text-2xl font-bold text-white">₹{fmt(data.total_payable_amount)}</p>
              </div>
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Total Paid</p>
                <p className="text-2xl font-bold text-green-400">₹{fmt(data.total_paid_amount)}</p>
              </div>
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-5">
                <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">Outstanding</p>
                <p className="text-2xl font-bold text-amber-400">₹{fmt(data.total_remaining_amount)}</p>
              </div>
            </div>
          </section>

          {/* Category breakdown */}
          {data.category_summary.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">By Category</h2>
              <div className="bg-gray-800 border border-gray-700 rounded-xl divide-y divide-gray-700">
                {data.category_summary.map((cat) => (
                  <div key={cat.category__code} className="flex items-center justify-between px-5 py-3">
                    <div>
                      <span className="text-sm text-white">{cat.category__name}</span>
                      <span className="ml-2 text-xs text-gray-600 font-mono">{cat.category__code}</span>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold text-white">₹{fmt(cat.total)}</p>
                      <p className="text-xs text-gray-500">{cat.count} expense{cat.count !== 1 ? 's' : ''}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Recent expenses */}
          {data.recent_expenses.length > 0 && (
            <section>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest">Recent Expenses</h2>
                <Link to="/financials/expenses" className="text-xs text-brand-400 hover:text-brand-300">View all →</Link>
              </div>
              <div className="bg-gray-800 border border-gray-700 rounded-xl divide-y divide-gray-700">
                {data.recent_expenses.map((exp) => (
                  <Link
                    key={exp.id}
                    to={`/financials/expenses/${exp.id}`}
                    className="flex items-center justify-between px-5 py-3 hover:bg-gray-800/60 transition-colors"
                  >
                    <div>
                      <p className="text-sm text-white">{exp.title}</p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {exp.expense_number} · {exp.category_name} · {exp.expense_date}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_BADGE[exp.status] ?? 'text-gray-400'}`}>
                        {exp.status}
                      </span>
                      <span className="text-sm font-semibold text-white">₹{fmt(exp.total_amount)}</span>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Quick links */}
          <section>
            <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">Quick Access</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {[
                { label: 'Expenses',          to: '/financials/expenses' },
                { label: 'Create Expense',    to: '/financials/expenses/new' },
                { label: 'Approval Queue',    to: '/financials/expenses?status=SUBMITTED' },
                { label: 'Categories',        to: '/financials/categories' },
                { label: 'Recurring',         to: '/financials/recurring' },
                { label: 'Supplier Invoices', to: '/financials/supplier-invoices' },
                { label: 'Payables',          to: '/financials/payables' },
                { label: 'Overdue',           to: '/financials/payables?status=OVERDUE' },
              ].map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="bg-gray-800/60 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-300 hover:text-white hover:border-gray-600 transition-colors"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
