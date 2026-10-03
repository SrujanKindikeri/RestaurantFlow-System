// =============================================================================
// RestaurantFlow — Bill Receipt / Print Page
// Phase 9 — Updated with payment information
// =============================================================================

import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getBillReceiptWithPayments } from '@/services/payments'
import type { BillReceiptDataV9 } from '@/types'

function fmt(v: string, currency = '₹') {
  const n = parseFloat(v)
  if (isNaN(n)) return `${currency}0.00`
  return `${currency}${Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function BillReceiptPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const printRef = useRef<HTMLDivElement>(null)

  const [receipt, setReceipt] = useState<BillReceiptDataV9 | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    getBillReceiptWithPayments(id)
      .then(setReceipt)
      .catch(() => setError('Receipt not found.'))
      .finally(() => setLoading(false))
  }, [id])

  function handlePrint() {
    window.print()
  }

  if (loading) return <div className="py-12 text-center text-gray-500">Loading receipt…</div>
  if (error || !receipt) return (
    <div className="py-12 text-center">
      <p className="text-red-400">{error ?? 'Receipt not found.'}</p>
      <button onClick={() => navigate(-1)} className="mt-4 text-sm text-gray-400 hover:text-white">← Back</button>
    </div>
  )

  const currency = receipt.currency === 'INR' ? '₹' : receipt.currency
  const hasDiscount = parseFloat(receipt.discount_amount) > 0
  const hasRounding = parseFloat(receipt.rounding_amount) !== 0
  const hasPayments = (receipt.payments ?? []).length > 0
  const paymentStatus = receipt.payment_status ?? 'UNPAID'

  const METHOD_LABELS: Record<string, string> = {
    CASH: 'Cash', UPI: 'UPI', CARD: 'Card', WALLET: 'Wallet',
    NET_BANKING: 'Net Banking', BANK_TRANSFER: 'Bank Transfer',
    CHEQUE: 'Cheque', CREDIT: 'Credit', OTHER: 'Other',
  }

  const PAYMENT_STATUS_LABELS: Record<string, string> = {
    UNPAID: 'UNPAID', PARTIALLY_PAID: 'PARTIAL', PAID: 'PAID', OVERPAID: 'OVERPAID',
  }

  return (
    <div className="min-h-screen bg-gray-950 py-8">
      {/* Print controls — hidden when printing */}
      <div className="print:hidden max-w-md mx-auto mb-4 flex gap-3 justify-between items-center">
        <button onClick={() => navigate(-1)} className="text-sm text-gray-400 hover:text-white flex items-center gap-1">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back
        </button>
        <button
          onClick={handlePrint}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm hover:bg-brand-500"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
          </svg>
          Print Receipt
        </button>
      </div>

      {/* Receipt paper — this is what gets printed */}
      <div
        ref={printRef}
        className="max-w-md mx-auto bg-white text-gray-900 rounded-lg shadow-2xl print:shadow-none print:rounded-none"
        style={{ fontFamily: "'Courier New', Courier, monospace", fontSize: '13px' }}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 text-center border-b border-dashed border-gray-300">
          {receipt.receipt_header && (
            <p className="text-xs text-gray-500 mb-2">{receipt.receipt_header}</p>
          )}
          <h1 className="text-lg font-bold">{receipt.restaurant.name}</h1>
          <p className="text-sm">{receipt.branch.name}</p>
          {receipt.branch.address && <p className="text-xs text-gray-600">{receipt.branch.address}</p>}
          {(receipt.branch.city || receipt.branch.state) && (
            <p className="text-xs text-gray-600">
              {[receipt.branch.city, receipt.branch.state, receipt.branch.postal_code].filter(Boolean).join(', ')}
            </p>
          )}
          {receipt.branch.phone && <p className="text-xs text-gray-600">Ph: {receipt.branch.phone}</p>}
          {receipt.restaurant.tax_id && (
            <p className="text-xs text-gray-500 mt-1">GSTIN: {receipt.restaurant.tax_id}</p>
          )}
        </div>

        {/* Bill info */}
        <div className="px-6 py-3 border-b border-dashed border-gray-300 text-xs">
          <div className="flex justify-between">
            <span>Bill No.</span>
            <span className="font-bold">{receipt.bill_number}</span>
          </div>
          <div className="flex justify-between">
            <span>Order No.</span>
            <span>{receipt.order_number}</span>
          </div>
          <div className="flex justify-between">
            <span>Type</span>
            <span>{receipt.order_type.replace('_', ' ')}</span>
          </div>
          {receipt.table_number && (
            <div className="flex justify-between">
              <span>Table</span>
              <span>{receipt.table_number}</span>
            </div>
          )}
          {receipt.counter_code && (
            <div className="flex justify-between">
              <span>Counter</span>
              <span>{receipt.counter_code}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span>Date</span>
            <span>{receipt.finalized_at
              ? new Date(receipt.finalized_at).toLocaleString()
              : new Date(receipt.date).toLocaleString()}
            </span>
          </div>
          {receipt.cashier && (
            <div className="flex justify-between">
              <span>Cashier</span>
              <span>{receipt.cashier}</span>
            </div>
          )}
        </div>

        {/* Items */}
        <div className="px-6 py-3 border-b border-dashed border-gray-300">
          {receipt.items.map((item, i) => {
            const qty = parseFloat(item.quantity)
            return (
              <div key={i} className="mb-1">
                <div className="flex justify-between">
                  <span className="font-medium">{item.name}</span>
                  <span>{fmt(item.total_amount, currency)}</span>
                </div>
                <div className="text-xs text-gray-500 flex justify-between">
                  <span>{qty % 1 === 0 ? qty.toFixed(0) : qty.toFixed(3)} × {fmt(item.unit_price, currency)}</span>
                  {parseFloat(item.tax_rate) > 0 && (
                    <span>{item.tax_code} {parseFloat(item.tax_rate).toFixed(1)}%</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {/* Totals */}
        <div className="px-6 py-3 border-b border-dashed border-gray-300 text-xs space-y-1">
          <div className="flex justify-between">
            <span>Subtotal</span>
            <span>{fmt(receipt.subtotal, currency)}</span>
          </div>
          {hasDiscount && (
            <div className="flex justify-between">
              <span>
                Discount ({receipt.discount_type === 'PERCENTAGE'
                  ? `${receipt.discount_value}%`
                  : `Fixed`})
              </span>
              <span>−{fmt(receipt.discount_amount, currency)}</span>
            </div>
          )}
          {/* Tax breakdown */}
          {Object.entries(receipt.tax_breakdown)
            .filter(([, v]) => parseFloat(v) > 0)
            .map(([code, amount]) => (
              <div key={code} className="flex justify-between">
                <span>Tax ({code})</span>
                <span>{fmt(amount, currency)}</span>
              </div>
            ))}
          {parseFloat(receipt.tax_amount) === 0 && (
            <div className="flex justify-between text-gray-400">
              <span>Tax</span>
              <span>Nil</span>
            </div>
          )}
          {hasRounding && (
            <div className="flex justify-between text-gray-500">
              <span>Rounding</span>
              <span>{parseFloat(receipt.rounding_amount) > 0 ? '+' : ''}{fmt(receipt.rounding_amount, currency)}</span>
            </div>
          )}
          {/* Grand total line */}
          <div className="flex justify-between font-bold text-sm border-t border-gray-400 pt-1 mt-1">
            <span>TOTAL</span>
            <span>{fmt(receipt.grand_total, currency)}</span>
          </div>
        </div>

        {/* Payment details — Phase 9 */}
        <div className="px-6 py-3 border-b border-dashed border-gray-300 text-xs space-y-1">
          {hasPayments ? (
            <>
              {(receipt.payments ?? []).map((p, i) => (
                <div key={i}>
                  <div className="flex justify-between font-medium">
                    <span>{METHOD_LABELS[p.payment_method] ?? p.payment_method}</span>
                    <span>{fmt(p.amount, currency)}</span>
                  </div>
                  {p.payment_method === 'CASH' && p.cash_received && (
                    <div className="flex justify-between text-gray-500">
                      <span className="pl-3">Cash received</span>
                      <span>{fmt(p.cash_received, currency)}</span>
                    </div>
                  )}
                  {p.payment_method === 'CASH' && p.change_amount && parseFloat(p.change_amount) > 0 && (
                    <div className="flex justify-between text-gray-500">
                      <span className="pl-3">Change</span>
                      <span>{fmt(p.change_amount, currency)}</span>
                    </div>
                  )}
                  {p.transaction_reference && (
                    <div className="flex justify-between text-gray-400">
                      <span className="pl-3">Ref</span>
                      <span className="font-mono">{p.transaction_reference}</span>
                    </div>
                  )}
                </div>
              ))}
              {(receipt.payments ?? []).length > 1 && (
                <div className="flex justify-between font-medium border-t border-dashed border-gray-300 pt-1 mt-1">
                  <span>Total Paid</span>
                  <span>{fmt(receipt.total_paid ?? '0', currency)}</span>
                </div>
              )}
              <div className="flex justify-between font-bold">
                <span>Payment Status</span>
                <span>{PAYMENT_STATUS_LABELS[paymentStatus] ?? paymentStatus}</span>
              </div>
              {parseFloat(receipt.remaining ?? '0') > 0 && (
                <div className="flex justify-between text-red-600 font-medium">
                  <span>Balance Due</span>
                  <span>{fmt(receipt.remaining ?? '0', currency)}</span>
                </div>
              )}
            </>
          ) : (
            <div className="text-gray-400 italic text-center">Payment pending</div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 text-center text-xs text-gray-500">
          {receipt.receipt_footer && (
            <p className="mb-2">{receipt.receipt_footer}</p>
          )}
          <p>Thank you for your visit!</p>
          <p className="text-gray-400 mt-1">Powered by RestaurantFlow</p>
        </div>
      </div>

      {/* Print styles injected */}
      <style>{`
        @media print {
          body * { visibility: hidden; }
          #root { visibility: hidden; }
          .print\\:shadow-none, .print\\:shadow-none * { visibility: visible; }
          [class*="print:shadow-none"] { position: fixed; left: 0; top: 0; width: 100%; }
          .print\\:hidden { display: none !important; }
        }
      `}</style>
    </div>
  )
}
