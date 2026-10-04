// =============================================================================
// RestaurantFlow — Supplier Invoices Page
// Phase 12
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  listSupplierInvoices, getSupplierInvoice,
  submitSupplierInvoice, approveSupplierInvoice, cancelSupplierInvoice,
} from '@/services/financials'
import type { SupplierInvoice, SupplierInvoiceDetail } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const STATUS_BADGE: Record<string, string> = {
  DRAFT:          'bg-gray-700 text-gray-400 border-gray-600',
  SUBMITTED:      'bg-blue-500/10 text-blue-400 border-blue-500/20',
  APPROVED:       'bg-green-500/10 text-green-400 border-green-500/20',
  PARTIALLY_PAID: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  PAID:           'bg-green-500/20 text-green-300 border-green-500/30',
  CANCELLED:      'bg-gray-700 text-gray-500 border-gray-600',
}

export function SupplierInvoicesPage() {
  const { hasPermission } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [invoices, setInvoices] = useState<SupplierInvoice[]>([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<SupplierInvoiceDetail | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const statusFilter = searchParams.get('status') ?? ''

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (statusFilter) params.status = statusFilter
    listSupplierInvoices(params)
      .then((data) => { setInvoices(data.results); setCount(data.count) })
      .catch((e) => setError(e?.response?.data?.message ?? 'Failed to load invoices'))
      .finally(() => setLoading(false))
  }, [statusFilter])

  useEffect(() => { load() }, [load])

  const openDetail = async (id: string) => {
    try {
      const inv = await getSupplierInvoice(id)
      setSelected(inv)
    } catch { /* ignore */ }
  }

  const doAction = async (action: string, id: string) => {
    setActionLoading(id)
    try {
      if (action === 'submit') await submitSupplierInvoice(id)
      else if (action === 'approve') await approveSupplierInvoice(id)
      else if (action === 'cancel') await cancelSupplierInvoice(id, 'Cancelled via UI')
      load()
      if (selected?.id === id) openDetail(id)
    } catch (e: any) {
      alert(e?.response?.data?.message ?? 'Action failed')
    } finally {
      setActionLoading(null)
    }
  }

  const canSubmit  = hasPermission('supplier_invoice.submit')
  const canApprove = hasPermission('supplier_invoice.approve')
  const canCancel  = hasPermission('supplier_invoice.cancel')

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Supplier Invoices</h1>
          <p className="text-sm text-gray-500 mt-1">{count} total</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <select
          value={statusFilter}
          onChange={(e) => { setSearchParams((p) => { const n = new URLSearchParams(p); if (e.target.value) n.set('status', e.target.value); else n.delete('status'); return n }) }}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-300"
        >
          <option value="">All statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="APPROVED">Approved</option>
          <option value="PARTIALLY_PAID">Partially Paid</option>
          <option value="PAID">Paid</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl h-16 animate-pulse" />)}</div>
      ) : invoices.length === 0 ? (
        <div className="text-center py-12 text-gray-600">No supplier invoices found.</div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Invoice #</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Supplier</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Date</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Due Date</th>
                <th className="px-4 py-3 text-right text-xs text-gray-500 font-medium uppercase tracking-wider">Total</th>
                <th className="px-4 py-3 text-left text-xs text-gray-500 font-medium uppercase tracking-wider">Status</th>
                <th className="px-4 py-3 text-right text-xs text-gray-500 font-medium uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {invoices.map((inv) => (
                <tr key={inv.id} className="hover:bg-gray-800/60 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">
                    <button onClick={() => openDetail(inv.id)} className="text-brand-400 hover:text-brand-300">
                      {inv.invoice_number}
                    </button>
                    {inv.external_invoice_number && (
                      <p className="text-gray-600 text-xs">{inv.external_invoice_number}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-200">{inv.supplier_name}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{inv.invoice_date}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{inv.due_date ?? '—'}</td>
                  <td className="px-4 py-3 text-right font-semibold text-white">₹{fmt(inv.total_amount)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded border ${STATUS_BADGE[inv.status] ?? ''}`}>
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {canSubmit && inv.status === 'DRAFT' && (
                        <button onClick={() => doAction('submit', inv.id)} disabled={actionLoading === inv.id}
                          className="px-2 py-1 text-xs text-blue-400 border border-blue-500/30 rounded hover:text-white">
                          Submit
                        </button>
                      )}
                      {canApprove && inv.status === 'SUBMITTED' && (
                        <button onClick={() => doAction('approve', inv.id)} disabled={actionLoading === inv.id}
                          className="px-2 py-1 text-xs text-green-400 border border-green-500/30 rounded hover:text-white">
                          Approve
                        </button>
                      )}
                      {canCancel && ['DRAFT', 'SUBMITTED'].includes(inv.status) && (
                        <button onClick={() => doAction('cancel', inv.id)} disabled={actionLoading === inv.id}
                          className="px-2 py-1 text-xs text-gray-400 border border-gray-700 rounded hover:text-white">
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

      {/* Detail slide-over */}
      {selected && (
        <div className="fixed inset-0 z-50 flex justify-end bg-gray-950/60" onClick={() => setSelected(null)}>
          <div className="bg-gray-900 border-l border-gray-700 w-full max-w-lg h-full overflow-y-auto p-6"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-lg font-semibold text-white">{selected.invoice_number}</h2>
                <p className="text-sm text-gray-500">{selected.supplier_name}</p>
              </div>
              <button onClick={() => setSelected(null)} className="text-gray-500 hover:text-white text-xl">×</button>
            </div>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-800 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Subtotal</p>
                  <p className="text-sm font-semibold text-white">₹{fmt(selected.subtotal)}</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Tax</p>
                  <p className="text-sm font-semibold text-white">₹{fmt(selected.tax_amount)}</p>
                </div>
                <div className="bg-gray-800 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Discount</p>
                  <p className="text-sm font-semibold text-white">₹{fmt(selected.discount_amount)}</p>
                </div>
                <div className="bg-brand-500/10 border border-brand-500/20 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">Total</p>
                  <p className="text-sm font-bold text-brand-400">₹{fmt(selected.total_amount)}</p>
                </div>
              </div>

              <div className="bg-gray-800 rounded-lg divide-y divide-gray-700">
                {[
                  { label: 'Invoice Date', value: selected.invoice_date },
                  { label: 'Due Date', value: selected.due_date ?? '—' },
                  { label: 'External Invoice #', value: selected.external_invoice_number || '—' },
                  { label: 'Purchase Order', value: selected.purchase_number ?? '—' },
                  { label: 'Status', value: selected.status },
                  { label: 'Payable ID', value: selected.payable_id ? selected.payable_id.slice(0, 8) + '…' : '—' },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-center justify-between px-4 py-2.5">
                    <span className="text-xs text-gray-500">{label}</span>
                    <span className="text-sm text-gray-200">{value}</span>
                  </div>
                ))}
              </div>

              {selected.notes && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Notes</p>
                  <p className="text-sm text-gray-300">{selected.notes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
