// =============================================================================
// RestaurantFlow — Expenses Page
// Phase 12
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  listExpenses, submitExpense, approveExpense,
  rejectExpense, cancelExpense,
} from '@/services/financials'
import type { Expense, ExpenseStatus } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const STATUS_BADGE: Record<string, string> = {
  DRAFT:      'bg-gray-700 text-gray-400 border-gray-600',
  SUBMITTED:  'bg-blue-500/10 text-blue-400 border-blue-500/20',
  APPROVED:   'bg-green-500/10 text-green-400 border-green-500/20',
  REJECTED:   'bg-red-500/10 text-red-400 border-red-500/20',
  CANCELLED:  'bg-gray-700 text-gray-500 border-gray-600',
}

const PAYMENT_BADGE: Record<string, string> = {
  UNPAID:         'text-amber-400',
  PARTIALLY_PAID: 'text-blue-400',
  PAID:           'text-green-400',
}

export function ExpensesPage() {
  const { hasPermission } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const [expenses, setExpenses] = useState<Expense[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [rejectModal, setRejectModal] = useState<{ id: string; title: string } | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [rejectError, setRejectError] = useState('')

  const statusFilter = searchParams.get('status') ?? ''
  const paymentFilter = searchParams.get('payment_status') ?? ''
  const searchQuery = searchParams.get('search') ?? ''

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (statusFilter) params.status = statusFilter
    if (paymentFilter) params.payment_status = paymentFilter
    if (searchQuery) params.search = searchQuery
    listExpenses(params)
      .then((data) => {
        setExpenses(data.results)
        setCount(data.count)
      })
      .catch((e) => setError(e?.response?.data?.message ?? 'Failed to load expenses'))
      .finally(() => setLoading(false))
  }, [statusFilter, paymentFilter, searchQuery])

  useEffect(() => { load() }, [load])

  const doAction = async (action: string, id: string, extra?: string) => {
    setActionLoading(id)
    try {
      if (action === 'submit') await submitExpense(id)
      else if (action === 'approve') await approveExpense(id)
      else if (action === 'cancel') await cancelExpense(id)
      else if (action === 'reject' && extra) await rejectExpense(id, extra)
      load()
    } catch (e: any) {
      alert(e?.response?.data?.message ?? 'Action failed')
    } finally {
      setActionLoading(null)
    }
  }

  const handleRejectSubmit = async () => {
    if (!rejectModal) return
    if (!rejectReason.trim() || rejectReason.trim().length < 5) {
      setRejectError('Reason must be at least 5 characters.')
      return
    }
    await doAction('reject', rejectModal.id, rejectReason)
    setRejectModal(null)
    setRejectReason('')
    setRejectError('')
  }

  const canCreate  = hasPermission('expense.create')
  const canApprove = hasPermission('expense.approve')
  const canReject  = hasPermission('expense.reject')
  const canSubmit  = hasPermission('expense.submit')
  const canCancel  = hasPermission('expense.cancel')

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Expenses</h1>
          <p className="text-sm text-gray-500 mt-1">{count} total record{count !== 1 ? 's' : ''}</p>
        </div>
        {canCreate && (
          <Link
            to="/financials/expenses/new"
            className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            + New Expense
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setSearchParams((p) => { const n = new URLSearchParams(p); if (e.target.value) n.set('status', e.target.value); else n.delete('status'); return n }) }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
        >
          <option value="">All statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
          <option value="CANCELLED">Cancelled</option>
        </select>

        <select
          value={paymentFilter}
          onChange={(e) => { setSearchParams((p) => { const n = new URLSearchParams(p); if (e.target.value) n.set('payment_status', e.target.value); else n.delete('payment_status'); return n }) }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
        >
          <option value="">All payments</option>
          <option value="UNPAID">Unpaid</option>
          <option value="PARTIALLY_PAID">Partially Paid</option>
          <option value="PAID">Paid</option>
        </select>

        <input
          type="text"
          placeholder="Search expenses…"
          value={searchQuery}
          onChange={(e) => { setSearchParams((p) => { const n = new URLSearchParams(p); if (e.target.value) n.set('search', e.target.value); else n.delete('search'); return n }) }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300 placeholder-gray-600 min-w-48"
        />
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl h-16 animate-pulse" />
          ))}
        </div>
      )}

      {/* Table */}
      {!loading && expenses.length === 0 && (
        <div className="text-center py-12 text-gray-600">No expenses found.</div>
      )}

      {!loading && expenses.length > 0 && (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Number</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Title</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Category</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Amount</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Date</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Payment</th>
                <th className="px-4 py-3 text-right text-xs text-gray-500 font-medium uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {expenses.map((exp) => (
                <tr key={exp.id} className="hover:bg-gray-800/60 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{exp.expense_number}</td>
                  <td className="px-4 py-3">
                    <Link to={`/financials/expenses/${exp.id}`} className="text-white hover:text-brand-400 font-medium">
                      {exp.title}
                    </Link>
                    {exp.vendor_name && (
                      <p className="text-xs text-gray-500 mt-0.5">{exp.vendor_name}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-300">{exp.category_name}</td>
                  <td className="px-4 py-3 text-white font-medium">₹{fmt(exp.total_amount)}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{exp.expense_date}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_BADGE[exp.status] ?? ''}`}>
                      {exp.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium ${PAYMENT_BADGE[exp.payment_status] ?? 'text-gray-400'}`}>
                      {exp.payment_status.replace('_', ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Link
                        to={`/financials/expenses/${exp.id}`}
                        className="px-2 py-1 text-xs text-gray-400 hover:text-white border border-gray-700 rounded"
                      >
                        View
                      </Link>
                      {canSubmit && exp.status === 'DRAFT' && (
                        <button
                          onClick={() => doAction('submit', exp.id)}
                          disabled={actionLoading === exp.id}
                          className="px-2 py-1 text-xs text-blue-400 hover:text-white border border-blue-500/30 rounded"
                        >
                          Submit
                        </button>
                      )}
                      {canApprove && exp.status === 'SUBMITTED' && (
                        <button
                          onClick={() => doAction('approve', exp.id)}
                          disabled={actionLoading === exp.id}
                          className="px-2 py-1 text-xs text-green-400 hover:text-white border border-green-500/30 rounded"
                        >
                          Approve
                        </button>
                      )}
                      {canReject && exp.status === 'SUBMITTED' && (
                        <button
                          onClick={() => setRejectModal({ id: exp.id, title: exp.title })}
                          className="px-2 py-1 text-xs text-red-400 hover:text-white border border-red-500/30 rounded"
                        >
                          Reject
                        </button>
                      )}
                      {canCancel && exp.status === 'DRAFT' && (
                        <button
                          onClick={() => doAction('cancel', exp.id)}
                          disabled={actionLoading === exp.id}
                          className="px-2 py-1 text-xs text-gray-400 hover:text-white border border-gray-700 rounded"
                        >
                          Cancel
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject modal */}
      {rejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/80">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-1">Reject Expense</h3>
            <p className="text-sm text-gray-400 mb-4">"{rejectModal.title}"</p>
            <label className="block text-sm text-gray-400 mb-2">Rejection reason <span className="text-red-400">*</span></label>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => { setRejectReason(e.target.value); setRejectError('') }}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500"
              placeholder="Provide a clear reason for rejection…"
            />
            {rejectError && <p className="text-xs text-red-400 mt-1">{rejectError}</p>}
            <div className="flex gap-3 mt-4">
              <button
                onClick={handleRejectSubmit}
                className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg"
              >
                Confirm Reject
              </button>
              <button
                onClick={() => { setRejectModal(null); setRejectReason(''); setRejectError('') }}
                className="flex-1 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium rounded-lg border border-gray-700"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
