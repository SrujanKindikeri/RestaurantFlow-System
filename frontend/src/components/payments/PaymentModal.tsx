// =============================================================================
// RestaurantFlow — Payment Modal
// Phase 9
//
// Full POS payment screen shown as a modal/panel over the Bill Detail page.
//
// Flow:
//   1. Displays Grand Total, Paid, Remaining.
//   2. Cashier selects payment method.
//   3. For CASH: enters cash_received; backend calculates change.
//   4. For UPI/CARD: enters transaction_reference.
//   5. Clicks PAY — button disabled during request.
//   6. On success: shows payment result + remaining amount.
//   7. If remaining > 0: allows another payment (split flow).
//   8. When remaining = 0: shows "Bill Paid" + Print Receipt button.
//
// Security:
//   - Amount is taken from the backend summary, never from user input.
//   - idempotency_key is generated per-attempt; same key is reused on retry.
//   - change_amount is NOT sent — backend calculates it.
//   - PAY button is disabled while processing to prevent double-click.
// =============================================================================

import { useState, useEffect, useRef } from 'react'
import { createPayment, getBillPaymentSummary } from '@/services/payments'
import { BillPaymentStatusBadge, PaymentStatusBadge } from './PaymentStatusBadge'
import type {
  BillPaymentSummary,
  PaymentMethod,
  Payment,
} from '@/types'

/** Generate a random UUID-like idempotency key using the Web Crypto API. */
function newIdempotencyKey(): string {
  return crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now().toString(36)
}

const METHOD_LABELS: Record<PaymentMethod, string> = {
  CASH:         'Cash',
  UPI:          'UPI',
  CARD:         'Card',
  WALLET:       'Wallet',
  NET_BANKING:  'Net Banking',
  BANK_TRANSFER:'Bank Transfer',
  CHEQUE:       'Cheque',
  CREDIT:       'Credit',
  OTHER:        'Other',
}

const PRIMARY_METHODS: PaymentMethod[] = ['CASH', 'UPI', 'CARD', 'OTHER']

function fmt(v: string | number, currency = '₹') {
  const n = parseFloat(String(v))
  if (isNaN(n)) return `${currency}0.00`
  const abs = Math.abs(n)
  return `${n < 0 ? '−' : ''}${currency}${abs.toLocaleString('en-IN', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })}`
}

interface Props {
  billId: string
  counterSessionId?: string | null
  onClose: () => void
  onPaid: () => void
}

export function PaymentModal({ billId, counterSessionId, onClose, onPaid }: Props) {
  const [summary, setSummary] = useState<BillPaymentSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [busy, setBusy]       = useState(false)

  const [method, setMethod]   = useState<PaymentMethod>('CASH')
  const [cashReceived, setCashReceived] = useState('')
  const [txnRef, setTxnRef]   = useState('')
  const [notes, setNotes]     = useState('')
  const [lastPayment, setLastPayment] = useState<Payment | null>(null)

  // Idempotency key — generated once per payment attempt, reused on retry
  const idempotencyKeyRef = useRef<string>(newIdempotencyKey())

  function refreshSummary() {
    return getBillPaymentSummary(billId)
      .then(setSummary)
      .catch(() => setError('Failed to load payment summary.'))
  }

  useEffect(() => {
    setLoading(true)
    refreshSummary().finally(() => setLoading(false))
  }, [billId])

  const remaining = parseFloat(summary?.remaining ?? '0')
  const isPaid = remaining <= 0

  async function handlePay() {
    if (!summary || isPaid || busy) return
    setBusy(true)
    setError(null)

    // Validate amount on frontend (display only — backend revalidates)
    const amount = summary.remaining

    try {
      const payload: Parameters<typeof createPayment>[0] = {
        bill_id:       billId,
        amount,
        payment_method: method,
        idempotency_key: idempotencyKeyRef.current,
        notes,
      }

      if (method === 'CASH') {
        if (!cashReceived || parseFloat(cashReceived) <= 0) {
          setError('Please enter the cash received amount.')
          setBusy(false)
          return
        }
        payload.cash_received = cashReceived
        payload.counter_session = counterSessionId ?? undefined
      } else if (['UPI', 'CARD'].includes(method)) {
        if (!txnRef.trim()) {
          setError('A transaction reference is required for ' + METHOD_LABELS[method] + ' payments.')
          setBusy(false)
          return
        }
        payload.transaction_reference = txnRef.trim()
      } else {
        if (txnRef.trim()) payload.transaction_reference = txnRef.trim()
      }

      const payment = await createPayment(payload)
      setLastPayment(payment)

      // Refresh summary to reflect new payment
      await refreshSummary()

      // Reset form for possible next partial payment
      setCashReceived('')
      setTxnRef('')
      setNotes('')
      // Generate a NEW idempotency key for the next attempt
      idempotencyKeyRef.current = newIdempotencyKey()

      // If fully paid, notify parent
      const freshRemaining = parseFloat(summary.remaining) - parseFloat(payment.amount)
      if (freshRemaining <= 0) onPaid()
    } catch (e: unknown) {
      const errData = (e as { response?: { data?: { message?: string; code?: string } } })?.response?.data
      setError(errData?.message ?? 'Payment failed. Please try again.')
      // Keep the same idempotency key so the user can safely retry
    } finally {
      setBusy(false)
    }
  }

  if (loading) return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-8 text-center text-gray-500">
      Loading payment details…
    </div>
  )

  if (!summary) return null

  const billTotal  = parseFloat(summary.bill_total)
  const totalPaid  = parseFloat(summary.total_paid)

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-semibold text-white">Payment</h2>
          <BillPaymentStatusBadge status={summary.payment_status} />
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-400">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Totals bar */}
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-gray-800/60 px-3 py-2 text-center">
            <p className="text-xs text-gray-500 mb-1">Bill Total</p>
            <p className="text-sm font-semibold text-white">{fmt(billTotal)}</p>
          </div>
          <div className="rounded-lg bg-gray-800/60 px-3 py-2 text-center">
            <p className="text-xs text-gray-500 mb-1">Paid</p>
            <p className="text-sm font-semibold text-green-400">{fmt(totalPaid)}</p>
          </div>
          <div className={`rounded-lg px-3 py-2 text-center ${remaining > 0 ? 'bg-red-900/20 border border-red-800/40' : 'bg-green-900/20 border border-green-800/40'}`}>
            <p className="text-xs text-gray-500 mb-1">Remaining</p>
            <p className={`text-sm font-semibold ${remaining > 0 ? 'text-red-400' : 'text-green-400'}`}>
              {fmt(remaining)}
            </p>
          </div>
        </div>

        {/* Previous payments */}
        {summary.payments.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs text-gray-500">Payments recorded</p>
            {summary.payments.map((p) => (
              <div key={p.id} className="flex items-center justify-between text-xs text-gray-400 py-1 border-b border-gray-800">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-gray-500">{p.payment_number}</span>
                  <span>{METHOD_LABELS[p.payment_method]}</span>
                  <PaymentStatusBadge status={p.status} />
                </div>
                <span className="font-semibold text-white">{fmt(p.amount)}</span>
              </div>
            ))}
          </div>
        )}

        {/* Last payment success banner */}
        {lastPayment && (
          <div className="rounded-lg bg-green-900/20 border border-green-800/40 px-4 py-3">
            <p className="text-sm font-semibold text-green-400">
              ✓ {fmt(lastPayment.amount)} via {METHOD_LABELS[lastPayment.payment_method]}
            </p>
            {lastPayment.payment_method === 'CASH' && lastPayment.change_amount && (
              <p className="text-xs text-gray-400 mt-0.5">
                Change: <span className="text-white font-semibold">{fmt(lastPayment.change_amount)}</span>
              </p>
            )}
          </div>
        )}

        {/* Bill fully paid */}
        {isPaid && (
          <div className="rounded-lg bg-green-900/20 border border-green-800/40 px-4 py-4 text-center">
            <p className="text-base font-bold text-green-400 mb-1">Bill Fully Paid</p>
            <p className="text-xs text-gray-500">All payments have been collected.</p>
            <div className="flex gap-3 mt-3 justify-center">
              <button
                onClick={() => window.open(`/billing/bills/${billId}/receipt`, '_blank')}
                className="px-4 py-2 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-500 flex items-center gap-2"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
                </svg>
                Print Receipt
              </button>
              <button onClick={onClose}
                className="px-4 py-2 text-sm rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800">
                Close
              </button>
            </div>
          </div>
        )}

        {/* Payment form — only when remaining > 0 */}
        {!isPaid && (
          <>
            {/* Method selector */}
            <div>
              <p className="text-xs text-gray-500 mb-2">Payment Method</p>
              <div className="grid grid-cols-4 gap-2">
                {PRIMARY_METHODS.map((m) => (
                  <button
                    key={m}
                    onClick={() => { setMethod(m); setCashReceived(''); setTxnRef('') }}
                    className={`py-2 rounded-lg text-xs font-medium border transition-colors ${
                      method === m
                        ? 'bg-brand-700 border-brand-600 text-white'
                        : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
                    }`}
                  >
                    {METHOD_LABELS[m]}
                  </button>
                ))}
              </div>
            </div>

            {/* Amount display (from backend — not editable for last payment) */}
            <div className="rounded-lg bg-gray-800/60 px-4 py-3 flex items-center justify-between">
              <span className="text-xs text-gray-400">Amount to collect</span>
              <span className="text-lg font-bold text-white">{fmt(remaining)}</span>
            </div>

            {/* CASH fields */}
            {method === 'CASH' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Cash Received (₹)</label>
                  <input
                    type="number"
                    min={remaining}
                    step="0.01"
                    placeholder={`e.g. ${Math.ceil(remaining)}`}
                    value={cashReceived}
                    onChange={(e) => setCashReceived(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-600"
                  />
                </div>
                {cashReceived && parseFloat(cashReceived) >= remaining && (
                  <div className="rounded-lg bg-gray-800/60 px-3 py-2 flex justify-between text-sm">
                    <span className="text-gray-400">Change</span>
                    <span className="font-semibold text-green-400">
                      {fmt(parseFloat(cashReceived) - remaining)}
                    </span>
                  </div>
                )}
                {cashReceived && parseFloat(cashReceived) < remaining && (
                  <p className="text-xs text-red-400">Cash received is less than the amount due.</p>
                )}
              </div>
            )}

            {/* UPI / CARD fields */}
            {(method === 'UPI' || method === 'CARD') && (
              <div>
                <label className="block text-xs text-gray-400 mb-1">
                  Transaction Reference <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  placeholder={method === 'UPI' ? 'UPI transaction ID / UTR' : 'POS terminal reference'}
                  value={txnRef}
                  onChange={(e) => setTxnRef(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-600"
                />
              </div>
            )}

            {/* OTHER field */}
            {(method === 'OTHER' || method === 'WALLET') && (
              <div>
                <label className="block text-xs text-gray-400 mb-1">Reference (optional)</label>
                <input
                  type="text"
                  placeholder="Reference number"
                  value={txnRef}
                  onChange={(e) => setTxnRef(e.target.value)}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-600"
                />
              </div>
            )}

            {/* Notes */}
            <div>
              <label className="block text-xs text-gray-400 mb-1">Notes (optional)</label>
              <input
                type="text"
                placeholder="Any notes…"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-600"
              />
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-lg bg-red-900/30 border border-red-800 text-red-400 px-3 py-2 text-xs">
                {error}
              </div>
            )}

            {/* PAY button */}
            <button
              disabled={busy}
              onClick={handlePay}
              className="w-full py-3 rounded-xl bg-green-700 text-white font-semibold text-sm hover:bg-green-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {busy ? (
                <>
                  <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                  </svg>
                  Processing…
                </>
              ) : (
                `Pay ${fmt(remaining)}`
              )}
            </button>
          </>
        )}
      </div>
    </div>
  )
}
