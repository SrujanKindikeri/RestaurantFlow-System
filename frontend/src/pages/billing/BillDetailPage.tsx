// =============================================================================
// RestaurantFlow — Bill Detail Page
// Phase 8
// =============================================================================

import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  getBill, finalizeBill, cancelBill, voidBill,
  applyDiscount, removeDiscount, requestCorrection,
} from '@/services/billing'
import { BillStatusBadge } from '@/components/billing/BillStatusBadge'
import { BillTotalsPanel } from '@/components/billing/BillTotalsPanel'
import { BillItemsTable } from '@/components/billing/BillItemsTable'
import { PaymentModal } from '@/components/payments/PaymentModal'
import { PaymentSummaryPanel } from '@/components/payments/PaymentSummaryPanel'
import { useAuth } from '@/contexts/AuthContext'
import type { Bill, DiscountType, CorrectionType } from '@/types'

export function BillDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  const [bill, setBill]       = useState<Bill | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [busy, setBusy]       = useState(false)

  // Discount form state
  const [showDiscountForm, setShowDiscountForm] = useState(false)
  const [discountType, setDiscountType]         = useState<DiscountType>('PERCENTAGE')
  const [discountValue, setDiscountValue]       = useState('')

  // Correction form state
  const [showCorrectionForm, setShowCorrectionForm] = useState(false)
  const [correctionType, setCorrectionType]         = useState('ITEM_CORRECTION')
  const [correctionReason, setCorrectionReason]     = useState('')

  // Cancel form state
  const [showCancelForm, setShowCancelForm] = useState(false)
  const [cancelReason, setCancelReason]     = useState('')
  const [showVoidForm, setShowVoidForm]     = useState(false)
  const [voidReason, setVoidReason]         = useState('')

  const [showPaymentModal, setShowPaymentModal] = useState(false)
  const [paymentRefreshKey, setPaymentRefreshKey] = useState(0)

  const perms = user?.scope?.permissions ?? []
  const canFinalize   = perms.includes('bill.finalize')
  const canCancel     = perms.includes('bill.cancel')
  const canVoid       = perms.includes('bill.void')
  const canDiscount   = perms.includes('discount.apply')
  const canPrint      = perms.includes('bill.print')
  const canCorrect    = perms.includes('bill.correction.request')
  const canPay        = perms.includes('payment.create')

  function load() {
    if (!id) return
    setLoading(true)
    getBill(id)
      .then(setBill)
      .catch(() => setError('Bill not found.'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [id])

  async function handleFinalize() {
    if (!id || !bill) return
    setBusy(true)
    try {
      const updated = await finalizeBill(id)
      setBill(updated)
    } catch (e: unknown) {
      setError((e as { message?: string })?.message ?? 'Finalization failed.')
    } finally { setBusy(false) }
  }

  async function handleApplyDiscount() {
    if (!id || !discountValue) return
    setBusy(true)
    try {
      const updated = await applyDiscount(id, {
        discount_type: discountType,
        discount_value: discountValue,
      })
      setBill(updated)
      setShowDiscountForm(false)
      setDiscountValue('')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg ?? 'Failed to apply discount.')
    } finally { setBusy(false) }
  }

  async function handleRemoveDiscount() {
    if (!id) return
    setBusy(true)
    try {
      const updated = await removeDiscount(id)
      setBill(updated)
    } catch { setError('Failed to remove discount.') }
    finally { setBusy(false) }
  }

  async function handleCancel() {
    if (!id || !cancelReason.trim()) return
    setBusy(true)
    try {
      const updated = await cancelBill(id, { reason: cancelReason })
      setBill(updated)
      setShowCancelForm(false)
    } catch { setError('Cancellation failed.') }
    finally { setBusy(false) }
  }

  async function handleVoid() {
    if (!id || !voidReason.trim()) return
    setBusy(true)
    try {
      const updated = await voidBill(id, { reason: voidReason })
      setBill(updated)
      setShowVoidForm(false)
    } catch { setError('Void failed.') }
    finally { setBusy(false) }
  }

  async function handleRequestCorrection() {
    if (!id || !correctionReason.trim()) return
    setBusy(true)
    try {
      await requestCorrection(id, {
        correction_type: correctionType as CorrectionType,
        reason: correctionReason,
      })
      setShowCorrectionForm(false)
      setCorrectionReason('')
      load()
    } catch { setError('Failed to submit correction request.') }
    finally { setBusy(false) }
  }

  function handlePrint() {
    if (!id) return
    window.open(`/billing/bills/${id}/receipt`, '_blank')
  }

  if (loading) return <div className="py-12 text-center text-gray-500">Loading bill…</div>
  if (error && !bill) return (
    <div className="py-12 text-center">
      <p className="text-red-400">{error}</p>
      <button onClick={() => navigate(-1)} className="mt-4 text-sm text-gray-400 hover:text-white">← Back</button>
    </div>
  )
  if (!bill) return null

  const isDraft     = bill.status === 'DRAFT'
  const isFinalized = bill.status === 'FINALIZED'
  const hasDiscount = parseFloat(bill.discount_amount) > 0
  const counterSessionId = bill.counter_session ?? null

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-300">
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-white font-mono">{bill.bill_number}</h1>
              <BillStatusBadge status={bill.status} />
              {bill.has_pending_correction && (
                <span className="px-2 py-0.5 rounded text-xs bg-amber-900/40 border border-amber-700 text-amber-400">
                  Correction Pending
                </span>
              )}
            </div>
            <p className="text-sm text-gray-500">
              Order {bill.order_number} · {bill.branch_name} · {bill.order_type}
            </p>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 flex-wrap">
          {canPrint && (
            <button
              onClick={handlePrint}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 transition-colors"
            >
              Print Receipt
            </button>
          )}
          {isFinalized && canPay && (
            <button
              onClick={() => setShowPaymentModal(!showPaymentModal)}
              className="px-3 py-1.5 text-sm rounded-lg bg-green-700 text-white hover:bg-green-600 transition-colors flex items-center gap-1.5"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              {showPaymentModal ? 'Hide Payment' : 'Collect Payment'}
            </button>
          )}
          {isDraft && canDiscount && (
            <button
              onClick={() => setShowDiscountForm(!showDiscountForm)}
              className="px-3 py-1.5 text-sm rounded-lg border border-amber-700/60 text-amber-400 hover:bg-amber-900/20 transition-colors"
            >
              {hasDiscount ? 'Edit Discount' : 'Apply Discount'}
            </button>
          )}
          {isDraft && canFinalize && (
            <button
              disabled={busy}
              onClick={handleFinalize}
              className="px-3 py-1.5 text-sm rounded-lg bg-green-700 text-white hover:bg-green-600 transition-colors disabled:opacity-50"
            >
              Finalize Bill
            </button>
          )}
          {isFinalized && canCorrect && (
            <button
              onClick={() => setShowCorrectionForm(!showCorrectionForm)}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-700 text-gray-300 hover:bg-gray-800 transition-colors"
            >
              Request Correction
            </button>
          )}
          {canCancel && !['CANCELLED', 'VOID'].includes(bill.status) && (
            <button
              onClick={() => setShowCancelForm(!showCancelForm)}
              className="px-3 py-1.5 text-sm rounded-lg border border-red-800/60 text-red-400 hover:bg-red-900/20 transition-colors"
            >
              Cancel
            </button>
          )}
          {isFinalized && canVoid && (
            <button
              onClick={() => setShowVoidForm(!showVoidForm)}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-700 text-gray-500 hover:bg-gray-800 transition-colors"
            >
              Void
            </button>
          )}
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-900/30 border border-red-800 text-red-400 px-4 py-3 text-sm">{error}</div>}

      {/* Discount form */}
      {showDiscountForm && isDraft && (
        <div className="rounded-lg border border-amber-800/60 bg-amber-900/10 px-4 py-4 space-y-3">
          <h3 className="text-sm font-medium text-amber-400">Apply Discount</h3>
          <div className="flex gap-3 flex-wrap">
            <select
              value={discountType}
              onChange={(e) => setDiscountType(e.target.value as DiscountType)}
              className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5"
            >
              <option value="PERCENTAGE">Percentage (%)</option>
              <option value="FIXED_AMOUNT">Fixed Amount (₹)</option>
            </select>
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder={discountType === 'PERCENTAGE' ? 'e.g. 10' : 'e.g. 50.00'}
              value={discountValue}
              onChange={(e) => setDiscountValue(e.target.value)}
              className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 w-36"
            />
            <button
              disabled={busy || !discountValue}
              onClick={handleApplyDiscount}
              className="px-4 py-1.5 text-sm rounded-lg bg-amber-600 text-white hover:bg-amber-500 disabled:opacity-50"
            >Apply</button>
            {hasDiscount && (
              <button
                onClick={handleRemoveDiscount}
                className="px-4 py-1.5 text-sm rounded-lg border border-gray-700 text-gray-400 hover:bg-gray-800"
              >Remove Discount</button>
            )}
            <button onClick={() => setShowDiscountForm(false)} className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-300">Cancel</button>
          </div>
        </div>
      )}

      {/* Correction form */}
      {showCorrectionForm && isFinalized && (
        <div className="rounded-lg border border-gray-700 bg-gray-900/60 px-4 py-4 space-y-3">
          <h3 className="text-sm font-medium text-white">Request Correction</h3>
          <select
            value={correctionType}
            onChange={(e) => setCorrectionType(e.target.value)}
            className="text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-1.5 w-full"
          >
            <option value="ITEM_CORRECTION">Item Correction</option>
            <option value="DISCOUNT_CORRECTION">Discount Correction</option>
            <option value="TAX_CORRECTION">Tax Correction</option>
            <option value="CANCELLATION">Cancellation</option>
          </select>
          <textarea
            placeholder="Describe the correction needed (minimum 10 characters)…"
            value={correctionReason}
            onChange={(e) => setCorrectionReason(e.target.value)}
            rows={3}
            className="w-full text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-2 resize-none"
          />
          <div className="flex gap-2">
            <button
              disabled={busy || correctionReason.trim().length < 10}
              onClick={handleRequestCorrection}
              className="px-4 py-1.5 text-sm rounded-lg bg-brand-600 text-white hover:bg-brand-500 disabled:opacity-50"
            >Submit Request</button>
            <button onClick={() => setShowCorrectionForm(false)} className="px-3 py-1.5 text-sm text-gray-500">Cancel</button>
          </div>
        </div>
      )}

      {/* Cancel form */}
      {showCancelForm && (
        <div className="rounded-lg border border-red-800/60 bg-red-900/10 px-4 py-4 space-y-3">
          <h3 className="text-sm font-medium text-red-400">Cancel Bill</h3>
          <textarea
            placeholder="Cancellation reason (required)…"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            rows={2}
            className="w-full text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-2 resize-none"
          />
          <div className="flex gap-2">
            <button disabled={busy || !cancelReason.trim()} onClick={handleCancel}
              className="px-4 py-1.5 text-sm rounded-lg bg-red-700 text-white hover:bg-red-600 disabled:opacity-50">Confirm Cancel</button>
            <button onClick={() => setShowCancelForm(false)} className="px-3 py-1.5 text-sm text-gray-500">Back</button>
          </div>
        </div>
      )}

      {/* Void form */}
      {showVoidForm && (
        <div className="rounded-lg border border-gray-700 bg-gray-900/60 px-4 py-4 space-y-3">
          <h3 className="text-sm font-medium text-gray-300">Void Bill</h3>
          <textarea
            placeholder="Void reason (required)…"
            value={voidReason}
            onChange={(e) => setVoidReason(e.target.value)}
            rows={2}
            className="w-full text-sm bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-2 resize-none"
          />
          <div className="flex gap-2">
            <button disabled={busy || !voidReason.trim()} onClick={handleVoid}
              className="px-4 py-1.5 text-sm rounded-lg bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-50">Confirm Void</button>
            <button onClick={() => setShowVoidForm(false)} className="px-3 py-1.5 text-sm text-gray-500">Back</button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left — Items + info */}
        <div className="lg:col-span-2 space-y-4">
          {/* Bill info */}
          <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-4">
            <h2 className="text-sm font-medium text-white mb-3">Bill Details</h2>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
              {[
                ['Order', bill.order_number],
                ['Type', bill.order_type],
                ['Branch', bill.branch_name],
                ['Restaurant', bill.restaurant_name],
                ...(bill.table_number ? [['Table', bill.table_number]] : []),
                ...(bill.counter_code ? [['Counter', bill.counter_code]] : []),
                ['Created by', bill.created_by_name ?? bill.created_by_email ?? '—'],
                ...(bill.finalized_by_name ? [['Finalized by', `${bill.finalized_by_name} · ${bill.finalized_at ? new Date(bill.finalized_at).toLocaleString() : ''}`]] : []),
                ...(bill.cancelled_by_email ? [['Cancelled by', bill.cancelled_by_email]] : []),
                ...(bill.cancellation_reason ? [['Cancel reason', bill.cancellation_reason]] : []),
              ].map(([label, value]) => (
                <div key={label as string}>
                  <dt className="text-gray-500">{label}</dt>
                  <dd className="text-gray-200">{value}</dd>
                </div>
              ))}
            </dl>
          </div>

          {/* Items */}
          <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-4">
            <h2 className="text-sm font-medium text-white mb-3">
              Items ({bill.items?.length ?? 0})
            </h2>
            <BillItemsTable items={bill.items ?? []} />
          </div>

          {/* Corrections */}
          {bill.correction_count > 0 && (
            <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-medium text-white">
                  Corrections ({bill.correction_count})
                </h2>
                <Link to="/billing/corrections" className="text-xs text-brand-400 hover:text-brand-300">View all →</Link>
              </div>
              {bill.has_pending_correction && (
                <p className="text-sm text-amber-400">There is a pending correction request for this bill.</p>
              )}
            </div>
          )}
        </div>

        {/* Right — Totals + Payment */}
        <div className="space-y-4">
          <BillTotalsPanel totals={bill} />

          {/* Payment modal (inline, shown when canPay + finalized) */}
          {showPaymentModal && isFinalized && (
            <PaymentModal
              billId={bill.id}
              counterSessionId={counterSessionId}
              onClose={() => setShowPaymentModal(false)}
              onPaid={() => {
                setShowPaymentModal(false)
                setPaymentRefreshKey((k) => k + 1)
              }}
            />
          )}

          {/* Payment summary — always show for finalized bills */}
          {isFinalized && !showPaymentModal && (
            <PaymentSummaryPanel billId={bill.id} refreshKey={paymentRefreshKey} />
          )}

          {bill.notes && (
            <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-3">
              <p className="text-xs text-gray-500 mb-1">Notes</p>
              <p className="text-sm text-gray-300">{bill.notes}</p>
            </div>
          )}
          <div className="rounded-lg border border-gray-800 bg-gray-900/60 px-4 py-3 text-xs text-gray-500 space-y-1">
            <div>Created: {new Date(bill.created_at).toLocaleString()}</div>
            <div>Updated: {new Date(bill.updated_at).toLocaleString()}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
