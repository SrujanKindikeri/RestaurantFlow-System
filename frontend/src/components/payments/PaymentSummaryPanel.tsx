// =============================================================================
// RestaurantFlow — Payment Summary Panel
// Phase 9
//
// Read-only summary of all payments against a bill.
// Used inside BillDetailPage when the bill is finalized.
// =============================================================================

import { useState, useEffect } from 'react'
import { getBillPaymentSummary } from '@/services/payments'
import { BillPaymentStatusBadge, PaymentStatusBadge } from './PaymentStatusBadge'
import type { BillPaymentSummary } from '@/types'

const METHOD_LABELS: Record<string, string> = {
  CASH: 'Cash', UPI: 'UPI', CARD: 'Card',
  WALLET: 'Wallet', NET_BANKING: 'Net Banking',
  BANK_TRANSFER: 'Bank Transfer', CHEQUE: 'Cheque',
  CREDIT: 'Credit', OTHER: 'Other',
}

function fmt(v: string | number) {
  const n = parseFloat(String(v))
  return isNaN(n) ? '₹0.00' : `₹${Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

interface Props {
  billId: string
  /** If provided, re-fetches when this value increments */
  refreshKey?: number
}

export function PaymentSummaryPanel({ billId, refreshKey }: Props) {
  const [summary, setSummary] = useState<BillPaymentSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getBillPaymentSummary(billId)
      .then(setSummary)
      .catch(() => setError('Failed to load payment summary.'))
      .finally(() => setLoading(false))
  }, [billId, refreshKey])

  if (loading) return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-6 text-center text-xs text-gray-600">
      Loading payment summary…
    </div>
  )
  if (error || !summary) return null

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/60 overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <h3 className="text-sm font-medium text-white">Payment Summary</h3>
        <BillPaymentStatusBadge status={summary.payment_status} />
      </div>

      <div className="px-4 py-3 space-y-3">
        {/* Totals */}
        <div className="grid grid-cols-3 gap-2 text-xs">
          <div>
            <p className="text-gray-500">Bill Total</p>
            <p className="font-semibold text-white">{fmt(summary.bill_total)}</p>
          </div>
          <div>
            <p className="text-gray-500">Total Paid</p>
            <p className="font-semibold text-green-400">{fmt(summary.total_paid)}</p>
          </div>
          <div>
            <p className="text-gray-500">Remaining</p>
            <p className={`font-semibold ${parseFloat(summary.remaining) > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {fmt(summary.remaining)}
            </p>
          </div>
        </div>

        {/* Payment list */}
        {summary.payments.length > 0 ? (
          <div className="space-y-1 pt-1 border-t border-gray-800">
            {summary.payments.map((p) => (
              <div key={p.id} className="flex items-center justify-between py-1 text-xs">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-gray-500">{p.payment_number}</span>
                  <span className="text-gray-400">{METHOD_LABELS[p.payment_method] ?? p.payment_method}</span>
                  <PaymentStatusBadge status={p.status} />
                </div>
                <div className="text-right">
                  <span className="font-semibold text-white">{fmt(p.amount)}</span>
                  {p.payment_method === 'CASH' && p.change_amount && parseFloat(p.change_amount) > 0 && (
                    <div className="text-gray-500">Change: {fmt(p.change_amount)}</div>
                  )}
                  {p.transaction_reference && (
                    <div className="text-gray-600 font-mono">{p.transaction_reference}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-600 text-center py-2">No payments recorded yet.</p>
        )}

        {summary.total_refunded && parseFloat(summary.total_refunded) > 0 && (
          <div className="pt-2 border-t border-gray-800 text-xs flex justify-between text-gray-400">
            <span>Total Refunded</span>
            <span className="text-blue-400">{fmt(summary.total_refunded)}</span>
          </div>
        )}
      </div>
    </div>
  )
}
