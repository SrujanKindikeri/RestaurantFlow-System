// =============================================================================
// RestaurantFlow — Billing Dashboard
// Phase 8
//
// Landing page for the billing section.
// Shows quick stats + recent bills + navigation to key billing flows.
// =============================================================================

import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { listBills } from '@/services/billing'
import { BillStatusBadge } from '@/components/billing/BillStatusBadge'
import { useAuth } from '@/contexts/AuthContext'
import type { BillSummary } from '@/types'

function fmt(v: string) {
  const n = parseFloat(v)
  return isNaN(n) ? '₹0.00' : `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

interface Stats {
  total: number
  draft: number
  finalized: number
  cancelled: number
}

export function BillingDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [recentBills, setRecentBills] = useState<BillSummary[]>([])
  const [stats, setStats]             = useState<Stats>({ total: 0, draft: 0, finalized: 0, cancelled: 0 })
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState<string | null>(null)

  const canCreate = user?.scope?.permissions?.includes('bill.create')

  useEffect(() => {
    setLoading(true)
    listBills({ page: 1 })
      .then((res) => {
        setRecentBills(res.results.slice(0, 8))
        const bills = res.results
        setStats({
          total:     res.count,
          draft:     bills.filter((b) => b.status === 'DRAFT').length,
          finalized: bills.filter((b) => b.status === 'FINALIZED').length,
          cancelled: bills.filter((b) => b.status === 'CANCELLED').length,
        })
      })
      .catch(() => setError('Failed to load billing data.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Billing</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage bills, invoices, and corrections</p>
        </div>
        <div className="flex gap-2">
          {canCreate && (
            <Link
              to="/orders"
              className="px-3 py-1.5 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-500 transition-colors"
            >
              + New Bill from Order
            </Link>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-900/30 border border-red-800 text-red-400 px-4 py-3 text-sm">{error}</div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: 'Total Bills', value: stats.total, color: 'text-white' },
          { label: 'Draft',       value: stats.draft,     color: 'text-gray-400' },
          { label: 'Finalized',   value: stats.finalized, color: 'text-green-400' },
          { label: 'Cancelled',   value: stats.cancelled, color: 'text-red-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-3">
            <p className="text-xs text-gray-500">{label}</p>
            <p className={`text-2xl font-bold mt-1 ${color}`}>{loading ? '…' : value}</p>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Link to="/billing/bills" className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-4 hover:border-gray-700 transition-colors">
          <div className="text-brand-400 mb-2">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-white">Bill History</p>
          <p className="text-xs text-gray-500 mt-0.5">Search and filter all bills</p>
        </Link>
        <Link to="/billing/corrections" className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-4 hover:border-gray-700 transition-colors">
          <div className="text-amber-400 mb-2">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </div>
          <p className="text-sm font-medium text-white">Corrections</p>
          <p className="text-xs text-gray-500 mt-0.5">Review and approve corrections</p>
        </Link>
        <Link to="/orders" className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-4 hover:border-gray-700 transition-colors">
          <div className="text-blue-400 mb-2">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
            </svg>
          </div>
          <p className="text-sm font-medium text-white">New Bill</p>
          <p className="text-xs text-gray-500 mt-0.5">Create bill from confirmed order</p>
        </Link>
      </div>

      {/* Recent bills */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/60 overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
          <h2 className="text-sm font-medium text-white">Recent Bills</h2>
          <Link to="/billing/bills" className="text-xs text-brand-400 hover:text-brand-300">View all →</Link>
        </div>
        {loading ? (
          <div className="px-4 py-8 text-center text-gray-500 text-sm">Loading…</div>
        ) : recentBills.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-500 text-sm">No bills yet.</div>
        ) : (
          <div className="divide-y divide-gray-800">
            {recentBills.map((bill) => (
              <div
                key={bill.id}
                onClick={() => navigate(`/billing/bills/${bill.id}`)}
                className="px-4 py-3 flex items-center justify-between hover:bg-gray-800/40 cursor-pointer"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <BillStatusBadge status={bill.status} />
                  <div className="min-w-0">
                    <p className="text-sm font-mono text-white truncate">{bill.bill_number}</p>
                    <p className="text-xs text-gray-500">
                      {bill.order_number} · {bill.branch_name}
                    </p>
                  </div>
                </div>
                <div className="text-right flex-shrink-0">
                  <p className="text-sm font-semibold text-white">{fmt(bill.grand_total)}</p>
                  <p className="text-xs text-gray-600">{new Date(bill.created_at).toLocaleDateString()}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
