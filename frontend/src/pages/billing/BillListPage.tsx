// =============================================================================
// RestaurantFlow — Bill List Page
// Phase 8
// =============================================================================

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { listBills } from '@/services/billing'
import { BillStatusBadge } from '@/components/billing/BillStatusBadge'
import type { BillSummary, BillStatus, BillListParams, OrderType } from '@/types'

function fmt(v: string) {
  const n = parseFloat(v)
  return isNaN(n) ? '₹0.00' : `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Status' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'FINALIZED', label: 'Finalized' },
  { value: 'CANCELLED', label: 'Cancelled' },
  { value: 'VOID', label: 'Void' },
]
const ORDER_TYPE_OPTIONS = [
  { value: '', label: 'All Types' },
  { value: 'DINE_IN', label: 'Dine In' },
  { value: 'TAKEAWAY', label: 'Takeaway' },
  { value: 'COUNTER', label: 'Counter' },
]

export function BillListPage() {
  const navigate = useNavigate()
  const [bills, setBills]           = useState<BillSummary[]>([])
  const [count, setCount]           = useState(0)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState<string | null>(null)
  const [page, setPage]             = useState(1)

  const [filters, setFilters] = useState<BillListParams>({
    status: undefined,
    order_type: undefined,
    bill_number: '',
    order_number: '',
    date_from: '',
    date_to: '',
  })

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const params: BillListParams = { page }
    if (filters.status)       params.status       = filters.status as BillStatus
    if (filters.order_type)   params.order_type   = filters.order_type as OrderType
    if (filters.bill_number)  params.bill_number  = filters.bill_number
    if (filters.order_number) params.order_number = filters.order_number
    if (filters.date_from)    params.date_from    = filters.date_from
    if (filters.date_to)      params.date_to      = filters.date_to

    listBills(params)
      .then((r) => { setBills(r.results); setCount(r.count) })
      .catch(() => setError('Failed to load bills.'))
      .finally(() => setLoading(false))
  }, [page, filters])

  useEffect(() => { load() }, [load])

  const totalPages = Math.ceil(count / 20) || 1

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Bills</h1>
          <p className="text-sm text-gray-500 mt-0.5">{count} bill{count !== 1 ? 's' : ''} found</p>
        </div>
      </div>

      {/* Filters */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-3 flex flex-wrap gap-3">
        <select
          value={filters.status ?? ''}
          onChange={(e) => { setFilters(f => ({ ...f, status: e.target.value as BillStatus | undefined })); setPage(1) }}
          className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-brand-500"
        >
          {STATUS_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={filters.order_type ?? ''}
          onChange={(e) => { setFilters(f => ({ ...f, order_type: e.target.value as OrderType | undefined })); setPage(1) }}
          className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-brand-500"
        >
          {ORDER_TYPE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <input
          type="text"
          placeholder="Bill number…"
          value={filters.bill_number ?? ''}
          onChange={(e) => { setFilters(f => ({ ...f, bill_number: e.target.value })); setPage(1) }}
          className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-brand-500 w-36"
        />
        <input
          type="text"
          placeholder="Order number…"
          value={filters.order_number ?? ''}
          onChange={(e) => { setFilters(f => ({ ...f, order_number: e.target.value })); setPage(1) }}
          className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-brand-500 w-36"
        />
        <input
          type="date"
          value={filters.date_from ?? ''}
          onChange={(e) => { setFilters(f => ({ ...f, date_from: e.target.value })); setPage(1) }}
          className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-brand-500"
        />
        <input
          type="date"
          value={filters.date_to ?? ''}
          onChange={(e) => { setFilters(f => ({ ...f, date_to: e.target.value })); setPage(1) }}
          className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 focus:outline-none focus:border-brand-500"
        />
      </div>

      {error && <div className="rounded-lg bg-red-900/30 border border-red-800 text-red-400 px-4 py-3 text-sm">{error}</div>}

      {/* Table */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/60 overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-gray-500 text-sm">Loading bills…</div>
        ) : bills.length === 0 ? (
          <div className="py-12 text-center text-gray-500 text-sm">No bills match your filters.</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
                    <th className="text-left px-4 py-2.5">Bill #</th>
                    <th className="text-left px-4 py-2.5">Order #</th>
                    <th className="text-left px-4 py-2.5">Branch</th>
                    <th className="text-left px-4 py-2.5">Type</th>
                    <th className="text-left px-4 py-2.5">Status</th>
                    <th className="text-right px-4 py-2.5">Discount</th>
                    <th className="text-right px-4 py-2.5">Tax</th>
                    <th className="text-right px-4 py-2.5">Total</th>
                    <th className="text-left px-4 py-2.5">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {bills.map((bill) => (
                    <tr
                      key={bill.id}
                      onClick={() => navigate(`/billing/bills/${bill.id}`)}
                      className="border-b border-gray-800/50 hover:bg-gray-800/40 cursor-pointer text-gray-300"
                    >
                      <td className="px-4 py-3 font-mono text-white text-xs">{bill.bill_number}</td>
                      <td className="px-4 py-3 font-mono text-gray-400 text-xs">{bill.order_number ?? '—'}</td>
                      <td className="px-4 py-3 text-gray-400">{bill.branch_name}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{bill.order_type ?? '—'}</td>
                      <td className="px-4 py-3"><BillStatusBadge status={bill.status} /></td>
                      <td className="px-4 py-3 text-right font-mono text-amber-400">
                        {parseFloat(bill.discount_amount) > 0 ? `−${fmt(bill.discount_amount)}` : '—'}
                      </td>
                      <td className="px-4 py-3 text-right font-mono">{fmt(bill.tax_amount)}</td>
                      <td className="px-4 py-3 text-right font-mono font-semibold text-white">{fmt(bill.grand_total)}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{new Date(bill.created_at).toLocaleDateString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="px-4 py-3 border-t border-gray-800 flex items-center justify-between">
                <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
                <div className="flex gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                    className="px-3 py-1 text-xs rounded bg-gray-800 text-gray-400 disabled:opacity-40 hover:bg-gray-700"
                  >Previous</button>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                    className="px-3 py-1 text-xs rounded bg-gray-800 text-gray-400 disabled:opacity-40 hover:bg-gray-700"
                  >Next</button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
