// =============================================================================
// RestaurantFlow — POS Billing Panel
// Phase 9 — Payment integration added
// =============================================================================

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createBillFromOrder,
  finalizeBill,
  applyDiscount,
  removeDiscount,
  calculateBill,
} from '@/services/billing'
import { BillStatusBadge } from './BillStatusBadge'
import { BillTotalsPanel } from './BillTotalsPanel'
import { BillItemsTable } from './BillItemsTable'
import { PaymentModal } from '@/components/payments/PaymentModal'
import { PaymentSummaryPanel } from '@/components/payments/PaymentSummaryPanel'
import { useAuth } from '@/contexts/AuthContext'
import type { Bill, BillCalculation, DiscountType, OrderDetail } from '@/types'

interface Props {
  order: OrderDetail
  onClose: () => void
}

export function POSBillingPanel({ order, onClose }: Props) {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [bill, setBill]       = useState<Bill | null>(null)
  const [preview, setPreview] = useState<BillCalculation | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy]       = useState(false)
  const [error, setError]     = useState<string | null>(null)
  const [step, setStep] = useState<'review' | 'discount' | 'finalized' | 'payment' | 'paid'>('review')
  const [paymentRefreshKey, setPaymentRefreshKey] = useState(0)

  // Discount form
  const [discountType, setDiscountType]   = useState<DiscountType>('PERCENTAGE')
  const [discountValue, setDiscountValue] = useState('')

  const perms = user?.scope?.permissions ?? []
  const canFinalize  = perms.includes('bill.finalize')
  const canDiscount  = perms.includes('discount.apply')
  const canPrint     = perms.includes('bill.print')
  const canPay       = perms.includes('payment.create')

  // Step 1 — create (or retrieve) the bill on mount
  useEffect(() => {
    setLoading(true)
    createBillFromOrder(order.id)
      .then(async (b) => {
        setBill(b)
        // Fetch calculation preview
        const calc = await calculateBill(b.id)
        setPreview(calc)
        if (b.status === 'FINALIZED') setStep('finalized')
      })
      .catch(() => setError('Failed to create bill. Check the order is confirmed.'))
      .finally(() => setLoading(false))
  }, [order.id])

  async function handleApplyDiscount() {
    if (!bill || !discountValue) return
    setBusy(true)
    setError(null)
    try {
      const updated = await applyDiscount(bill.id, { discount_type: discountType, discount_value: discountValue })
      setBill(updated)
      const calc = await calculateBill(updated.id)
      setPreview(calc)
      setDiscountValue('')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg ?? 'Failed to apply discount.')
    } finally { setBusy(false) }
  }

  async function handleRemoveDiscount() {
    if (!bill) return
    setBusy(true)
    try {
      const updated = await removeDiscount(bill.id)
      setBill(updated)
      const calc = await calculateBill(updated.id)
      setPreview(calc)
    } catch { setError('Failed to remove discount.') }
    finally { setBusy(false) }
  }

  async function handleFinalize() {
    if (!bill) return
    setBusy(true)
    setError(null)
    try {
      const finalized = await finalizeBill(bill.id)
      setBill(finalized)
      setStep('finalized')
    } catch (e: unknown) {      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg ?? 'Finalization failed.')
    } finally { setBusy(false) }
  }

  function handlePrint() {
    if (bill) navigate(`/billing/bills/${bill.id}/receipt`)
  }

  function handleViewBill() {
    if (bill) navigate(`/billing/bills/${bill.id}`)
  }

  // Counter session from order (if COUNTER type)
  const counterSessionId = order.counter_session ?? null

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-800 bg-gray-900/80 p-6 text-center text-gray-500">
        Preparing bill…
      </div>
    )
  }

  if (error && !bill) {
    return (
      <div className="rounded-xl border border-red-800/60 bg-red-900/10 p-6 text-center">
        <p className="text-red-400 text-sm">{error}</p>
        <button onClick={onClose} className="mt-3 text-xs text-gray-500 hover:text-gray-300">Close</button>
      </div>
    )
  }

  const totals = preview ?? bill

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
      {/* Panel header */}
      <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-white">
            {step === 'finalized' ? 'Bill Finalized' : 'Create Bill'}
          </h2>
          {bill && <BillStatusBadge status={bill.status} />}
          {bill && (
            <span className="text-xs font-mono text-gray-500">{bill.bill_number}</span>
          )}
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-400">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {error && (
        <div className="px-5 py-2 bg-red-900/20 border-b border-red-800/40">
          <p className="text-xs text-red-400">{error}</p>
        </div>
      )}

      <div className="px-5 py-4 space-y-5">
        {/* Order summary */}
        <div className="text-xs text-gray-500 flex gap-4">
          <span>Order: <span className="text-gray-300 font-mono">{order.order_number}</span></span>
          <span>Type: <span className="text-gray-300">{order.order_type}</span></span>
          {order.table_number && <span>Table: <span className="text-gray-300">{order.table_number}</span></span>}
          {order.counter_code && <span>Counter: <span className="text-gray-300">{order.counter_code}</span></span>}
        </div>

        {/* Items */}
        {bill && bill.items && bill.items.length > 0 && (
          <div>
            <p className="text-xs text-gray-500 mb-2">Items ({bill.items.length})</p>
            <BillItemsTable items={bill.items} />
          </div>
        )}

        {/* Discount section — only for draft bills */}
        {bill?.status === 'DRAFT' && canDiscount && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <p className="text-xs text-gray-500">Discount</p>
              {parseFloat(bill.discount_amount) > 0 && (
                <button
                  onClick={handleRemoveDiscount}
                  className="text-xs text-red-400 hover:text-red-300"
                >Remove</button>
              )}
            </div>
            <div className="flex gap-2 flex-wrap">
              <select
                value={discountType}
                onChange={(e) => setDiscountType(e.target.value as DiscountType)}
                className="text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-2 py-1.5"
              >
                <option value="PERCENTAGE">% Percentage</option>
                <option value="FIXED_AMOUNT">₹ Fixed Amount</option>
              </select>
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder={discountType === 'PERCENTAGE' ? 'e.g. 5' : 'e.g. 50.00'}
                value={discountValue}
                onChange={(e) => setDiscountValue(e.target.value)}
                className="text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-2 py-1.5 w-28"
              />
              <button
                disabled={busy || !discountValue}
                onClick={handleApplyDiscount}
                className="px-3 py-1.5 text-xs rounded-lg bg-amber-700 text-white hover:bg-amber-600 disabled:opacity-50"
              >Apply Discount</button>
            </div>
          </div>
        )}

        {/* Totals */}
        {totals && (
          <BillTotalsPanel
            totals={{
              ...totals,
              discount_type: bill?.discount_type ?? null,
              discount_value: bill?.discount_value ?? '0.00',
            }}
          />
        )}

        {/* Action buttons */}
        <div className="flex gap-3 pt-1">
          {step !== 'finalized' && canFinalize && bill?.status === 'DRAFT' && (
            <button
              disabled={busy}
              onClick={handleFinalize}
              className="flex-1 py-2.5 rounded-xl bg-green-700 text-white font-semibold text-sm hover:bg-green-600 transition-colors disabled:opacity-50"
            >
              {busy ? 'Finalizing…' : 'Finalize Bill'}
            </button>
          )}

          {step === 'finalized' && (
            <>
              {canPay && (
                <button
                  onClick={() => setStep('payment')}
                  className="flex-1 py-2.5 rounded-xl bg-green-700 text-white font-semibold text-sm hover:bg-green-600 transition-colors flex items-center justify-center gap-2"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  Collect Payment
                </button>
              )}
              {canPrint && (
                <button
                  onClick={handlePrint}
                  className="flex-1 py-2.5 rounded-xl border border-brand-700/60 text-brand-400 font-semibold text-sm hover:bg-brand-900/20 transition-colors flex items-center justify-center gap-2"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                  </svg>
                  Print Receipt
                </button>
              )}
              <button
                onClick={handleViewBill}
                className="px-4 py-2.5 rounded-xl border border-gray-700 text-gray-300 text-sm hover:bg-gray-800 transition-colors"
              >
                View Bill
              </button>
            </>
          )}

          {step === 'payment' && bill && (
            <button
              onClick={() => setStep('finalized')}
              className="px-4 py-2.5 rounded-xl border border-gray-700 text-gray-400 text-sm hover:bg-gray-800"
            >
              ← Back to Bill
            </button>
          )}

          {step !== 'finalized' && (
            <button
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-gray-700 text-gray-500 text-sm hover:bg-gray-800 hover:text-gray-300 transition-colors"
            >
              Close
            </button>
          )}
        </div>

        {/* Payment modal (inline panel — replaces "Phase 9 notice") */}
        {step === 'payment' && bill && (
          <PaymentModal
            billId={bill.id}
            counterSessionId={counterSessionId}
            onClose={() => setStep('finalized')}
            onPaid={() => {
              setStep('paid')
              setPaymentRefreshKey((k) => k + 1)
            }}
          />
        )}

        {/* Payment summary after completion */}
        {(step === 'finalized' || step === 'paid') && bill && (
          <PaymentSummaryPanel billId={bill.id} refreshKey={paymentRefreshKey} />
        )}
      </div>
    </div>
  )
}
