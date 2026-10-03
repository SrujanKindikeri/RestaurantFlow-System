// =============================================================================
// RestaurantFlow — Payment History Page
// Phase 9
//
// Filterable list of all payments accessible to the current user.
// Filters: date, branch, counter, payment method, status, cashier.
// =============================================================================

import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { listPayments } from '@/services/payments'
import { PaymentStatusBadge } from '@/components/payments/PaymentStatusBadge'
import { useAuth } from '@/contexts/AuthContext'
import type { PaymentSummary, PaymentMethod, PaymentStatus, PaymentListParams } from '@/types'

const METHOD_LABELS: Record<PaymentMethod, string> = {
  CASH: 'Cash', UPI: 'UPI', CARD: 'Card', WALLET: 'Wallet',
  NET_BANKING: 'Net Banking', BANK_TRANSFER: 'Bank Transfer',
  CHEQUE: 'Cheque', CREDIT: 'Credit', OTHER: 'Other',
}

function fmt(v: string | number) {
  const n = parseFloat(String(v))
  return isNaN(n) ? '₹0.00' : `₹${Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const ALL_METHODS: PaymentMethod[] = ['CASH', 'UPI', 'CARD', 'WALLET', 'NET_BANKING', 'BANK_TRANSFER', 'CHEQUE', 'CREDIT', 'OTHER']
const ALL_STATUSES: PaymentStatus[] = ['PENDING', 'COMPLETED', 'FAILED', 'CANCELLED', 'REFUNDED', 'PARTIALLY_REFUNDED']

export function PaymentHistoryPage() {
  const { user } = useAuth()
  const perms = user?.scope?.permissions ?? []
  const canView = perms.includes('payment.view') || perms.includes('payment.history.view')

  const [payments, setPayments]   = useState<PaymentSummary[]>([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState<string | null>(null)
  const [count, setCount]         = useState(0)
  const [page, setPage]           = useState(1)

  // Filters
  const [status, setStatus]       = useState<string>('')
  const [method, setMethod]       = useState<string>('')
  const [dateFrom, setDateFrom]   = useState('')
  const [dateTo, setDateTo]       = useState('')
  const [branchId, setBranchId]   = useState('')

  const load = useCallback(() => {
    if (!canView) return
    setLoading(true)
    const params: PaymentListParams = { page }
    if (status)   params.status   = status as PaymentStatus
    if (method)   params.payment_method = method as PaymentMethod
    if (dateFrom) params.date_from = dateFrom
    if (dateTo)   params.date_to   = dateTo
    if (branchId) params.branch   = branchId

    listPayments(params)
      .then((res) => {
        setPayments(res.results)
        setCount(res.count)
      })
      .catch(() => setError('Failed to load payment history.'))
      .finally(() => setLoading(false))
  }, [canView, page, status, method, dateFrom, dateTo, branchId])

  useEffect(() => { load() }, [load])

  function handleFilterSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    load()
  }

  function clearFilters() {
    setStatus(''); setMethod(''); setDateFrom(''); setDateTo(''); setBranchId('')
    setPage(1)
  }

  const totalPages = Math.ceil(count / 20)

  if (!canView) {
    return (
      <div className="py-12 text-center text-gray-500">
        You do not have permission to view payment history.
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-white">Payment History</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {count > 0 ? `${count} payment${count !== 1 ? 's' : ''}` : 'All payments'}
          </p>
        </div>
      </div>

      {/* Filters */}
      <form onSubmit={handleFilterSubmit} className="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5"
          >
            <option value="">All Statuses</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>{s.replace('_', ' ')}</option>
            ))}
          </select>

          <select
            value={method}
            onChange={(e) => setMethod(e.target.value)}
            className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5"
          >
            <option value="">All Methods</option>
            {ALL_METHODS.map((m) => (
              <option key={m} value={m}>{METHOD_LABELS[m]}</option>
            ))}
          </select>

          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5"
            placeholder="From"
          />

          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5"
            placeholder="To"
          />

          <div className="flex gap-2">
            <button
              type="submit"
              className="flex-1 px-3 py-1.5 text-sm rounded-lg bg-brand-700 text-white hover:bg-brand-600"
            >
              Filter
            </button>
            <button
              type="button"
              onClick={clearFilters}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-800"
            >
              Clear
            </button>
          </div>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-900/30 border border-red-800 text-red-400 px-4 py-3 text-sm">{error}</div>
      )}

      {/* Table */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-900/80">
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Payment #</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Bill / Order</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Method</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wide">Amount</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Cashier</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wide">Date</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-600">Loading…</td>
              </tr>
            ) : payments.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-600">
                  No payments found for the selected filters.
                </td>
              </tr>
            ) : (
              payments.map((p) => (
                <tr key={p.id} className="border-b border-gray-800/60 hover:bg-gray-800/20 transition-colors">
                  <td className="px-4 py-3">
                    <Link
                      to={`/payments/${p.id}`}
                      className="font-mono text-brand-400 hover:text-brand-300 text-xs"
                    >
                      {p.payment_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs">
                      {p.bill_number && (
                        <Link to={`/billing/bills/${p.bill}`} className="text-gray-300 hover:text-white font-mono">
                          {p.bill_number}
                        </Link>
                      )}
                      {p.order_number && (
                        <div className="text-gray-500">{p.order_number}</div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-300">
                      {METHOD_LABELS[p.payment_method] ?? p.payment_method}
                    </span>
                    {p.counter_code && (
                      <div className="text-xs text-gray-600">{p.counter_code}</div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-semibold text-white">{fmt(p.amount)}</span>
                    {p.payment_method === 'CASH' && p.change_amount && parseFloat(p.change_amount) > 0 && (
                      <div className="text-xs text-gray-500">Change: {fmt(p.change_amount)}</div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <PaymentStatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-400">
                    {p.initiated_by_name ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">
                    {p.completed_at
                      ? new Date(p.completed_at).toLocaleString()
                      : new Date(p.created_at).toLocaleString()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-400">
          <span>Page {page} of {totalPages} · {count} total</span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="px-3 py-1.5 rounded-lg border border-gray-700 hover:bg-gray-800 disabled:opacity-40"
            >
              ← Prev
            </button>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 rounded-lg border border-gray-700 hover:bg-gray-800 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
