// =============================================================================
// RestaurantFlow — Payables Page
// Phase 12
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listPayables, getPayableDashboard, recordPayment } from '@/services/financials'
import type { Payable, PayableDashboard } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const STATUS_BADGE: Record<string, string> = {
  OPEN:           'bg-blue-500/10 text-blue-400 border-blue-500/20',
  PARTIALLY_PAID: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  PAID:           'bg-green-500/10 text-green-400 border-green-500/20',
  OVERDUE:        'bg-red-500/10 text-red-400 border-red-500/20',
  CANCELLED:      'bg-gray-700 text-gray-500 border-gray-600',
}

export function PayablesPage() {
  const { hasPermission } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [payables, setPayables] = useState<Payable[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dashboard, setDashboard] = useState<PayableDashboard | null>(null)
  const [paymentModal, setPaymentModal] = useState<Payable | null>(null)
  const [paymentAmount, setPaymentAmount] = useState('')
  const [paymentError, setPaymentError] = useState('')
  const [paymentLoading, setPaymentLoading] = useState(false)

  const statusFilter = searchParams.get('status') ?? ''
  const typeFilter   = searchParams.get('payable_type') ?? ''

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (statusFilter) params.status = statusFilter
    if (typeFilter) params.payable_type = typeFilter
    listPayables(params)
      .then((data) => { setPayables(data.results); setCount(data.count) })
      .catch((e) => setError(e?.response?.data?.message ?? 'Failed to load payables'))
      .finally(() => setLoading(false))
  }, [statusFilter, typeFilter])

  useEffect(() => {
    load()
    getPayableDashboard().then(setDashboard).catch(() => {})
  }, [load])

  const handleRecordPayment = async () => {
    if (!paymentModal) return
    if (!paymentAmount || Number(paymentAmount) <= 0) {
      setPaymentError('Enter a valid amount greater than 0.')
      return
    }
    setPaymentLoading(true)
    try {
      await recordPayment(paymentModal.id, paymentAmount)
      setPaymentModal(null)
      setPaymentAmount('')
      setPaymentError('')
      load()
      getPayableDashboard().then(setDashboard).catch(() => {})
    } catch (e: any) {
      setPaymentError(e?.response?.data?.message ?? 'Payment failed')
    } finally {
      setPaymentLoading(false)
    }
  }

  const canManage = hasPermission('payable.manage')

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Payables</h1>
        <p className="text-sm text-gray-500 mt-1">Financial obligations and payment tracking</p>
      </div>

      {/* Dashboard summary */}
      {dashboard && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Open',          value: dashboard.open_payables,    colour: 'text-blue-400' },
            { label: 'Partially Paid',value: dashboard.partially_paid,   colour: 'text-amber-400' },
            { label: 'Overdue',       value: dashboard.overdue_payables, colour: 'text-red-400' },
            { label: 'Paid',          value: dashboard.paid_payables,    colour: 'text-green-400' },
          ].map(({ label, value, colour }) => (
            <div key={label} className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <p className="text-xs text-gray-500 mb-1">{label}</p>
              <p className={`text-2xl font-bold ${colour}`}>{value}</p>
            </div>
          ))}
        </div>
      )}

      {dashboard && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">Total Payable</p>
            <p className="text-xl font-bold text-white">₹{fmt(dashboard.total_amount)}</p>
          </div>
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">Paid</p>
            <p className="text-xl font-bold text-green-400">₹{fmt(dashboard.paid_amount)}</p>
          </div>
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
            <p className="text-xs text-gray-500 mb-1">Outstanding</p>
            <p className="text-xl font-bold text-amber-400">₹{fmt(dashboard.remaining_amount)}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setSearchParams((p) => { const n = new URLSearchParams(p); if (e.target.value) n.set('status', e.target.value); else n.delete('status'); return n }) }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
        >
          <option value="">All statuses</option>
          <option value="OPEN">Open</option>
          <option value="PARTIALLY_PAID">Partially Paid</option>
          <option value="PAID">Paid</option>
          <option value="OVERDUE">Overdue</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => { setSearchParams((p) => { const n = new URLSearchParams(p); if (e.target.value) n.set('payable_type', e.target.value); else n.delete('payable_type'); return n }) }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
        >
          <option value="">All types</option>
          <option value="EXPENSE">Expense</option>
          <option value="SUPPLIER_INVOICE">Supplier Invoice</option>
        </select>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl h-16 animate-pulse" />)}</div>
      ) : payables.length === 0 ? (
        <div className="text-center py-12 text-gray-600">No payables found.</div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Reference</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Type</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Supplier</th>
                <th className="px-4 py-3 text-right text-xs text-gray-500 font-medium uppercase tracking-wider">Amount</th>
                <th className="px-4 py-3 text-right text-xs text-gray-500 font-medium uppercase tracking-wider">Paid</th>
                <th className="px-4 py-3 text-right text-xs text-gray-500 font-medium uppercase tracking-wider">Remaining</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Due</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Status</th>
                {canManage && <th className="px-4 py-3 text-right text-xs text-gray-500 font-medium uppercase tracking-wider">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {payables.map((p) => (
                <tr key={p.id} className={`hover:bg-gray-800/60 transition-colors ${p.is_overdue ? 'border-l-2 border-red-500/40' : ''}`}>
                  <td className="px-4 py-3 font-mono text-xs text-gray-300">{p.reference_number}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs text-gray-400">{p.payable_type.replace('_', ' ')}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-300 text-sm">{p.supplier_name ?? '—'}</td>
                  <td className="px-4 py-3 text-right text-white font-medium">₹{fmt(p.amount)}</td>
                  <td className="px-4 py-3 text-right text-green-400">₹{fmt(p.paid_amount)}</td>
                  <td className="px-4 py-3 text-right font-semibold text-amber-400">₹{fmt(p.remaining_amount)}</td>
                  <td className={`px-4 py-3 text-xs ${p.is_overdue ? 'text-red-400 font-semibold' : 'text-gray-400'}`}>
                    {p.due_date ?? '—'}
                    {p.is_overdue && <span className="ml-1 text-red-500">⚠</span>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_BADGE[p.status] ?? ''}`}>
                      {p.status.replace('_', ' ')}
                    </span>
                  </td>
                  {canManage && (
                    <td className="px-4 py-3 text-right">
                      {!['PAID', 'CANCELLED'].includes(p.status) && (
                        <button
                          onClick={() => { setPaymentModal(p); setPaymentAmount(''); setPaymentError('') }}
                          className="px-2 py-1 text-xs text-brand-400 border border-brand-500/30 rounded hover:text-white"
                        >
                          Pay
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Record payment modal */}
      {paymentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/80">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-sm">
            <h3 className="text-lg font-semibold text-white mb-1">Record Payment</h3>
            <p className="text-sm text-gray-400 mb-1">{paymentModal.reference_number}</p>
            <p className="text-xs text-gray-500 mb-4">
              Remaining: <span className="text-amber-400 font-semibold">₹{fmt(paymentModal.remaining_amount)}</span>
            </p>
            <label className="block text-sm text-gray-400 mb-2">Payment Amount (₹) <span className="text-red-400">*</span></label>
            <input
              type="number"
              min="0.01"
              step="0.01"
              max={paymentModal.remaining_amount}
              value={paymentAmount}
              onChange={(e) => { setPaymentAmount(e.target.value); setPaymentError('') }}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
            />
            {paymentError && <p className="text-xs text-red-400 mt-1">{paymentError}</p>}
            <div className="flex gap-3 mt-4">
              <button
                onClick={handleRecordPayment}
                disabled={paymentLoading}
                className="flex-1 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium rounded-lg disabled:opacity-50"
              >
                {paymentLoading ? 'Recording…' : 'Record Payment'}
              </button>
              <button
                onClick={() => { setPaymentModal(null); setPaymentAmount(''); setPaymentError('') }}
                className="flex-1 py-2 bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg"
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
