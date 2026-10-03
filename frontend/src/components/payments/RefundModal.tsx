// =============================================================================
// RestaurantFlow — Refund Modal
// Phase 9
// =============================================================================

import { useState } from 'react'
import { requestRefund, approveRefund, rejectRefund, processRefund } from '@/services/payments'
import { RefundStatusBadge } from './PaymentStatusBadge'
import type { Payment, PaymentRefundItem } from '@/types'

function fmt(v: string | number) {
  const n = parseFloat(String(v))
  return isNaN(n) ? '₹0.00' : `₹${Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

interface Props {
  payment: Payment
  canRequest:  boolean
  canApprove:  boolean
  canProcess:  boolean
  onClose:     () => void
  onRefunded?: () => void
}

export function RefundModal({ payment, canRequest, canApprove, canProcess, onClose, onRefunded }: Props) {
  const [refunds, setRefunds] = useState<PaymentRefundItem[]>(payment.refunds ?? [])
  const [busy, setBusy]       = useState(false)
  const [error, setError]     = useState<string | null>(null)

  // Request form
  const [refundAmount, setRefundAmount] = useState('')
  const [refundReason, setRefundReason] = useState('')
  const [refundNotes, setRefundNotes]   = useState('')
  const [showReqForm, setShowReqForm]   = useState(false)

  // Reject reason
  const [rejectingId, setRejectingId]     = useState<string | null>(null)
  const [rejectReason, setRejectReason]   = useState('')

  // Calculate refundable
  const totalProcessed = refunds
    .filter((r) => r.status === 'PROCESSED')
    .reduce((s, r) => s + parseFloat(r.amount), 0)
  const refundable = parseFloat(payment.amount) - totalProcessed

  async function handleRequestRefund() {
    if (!refundAmount || !refundReason.trim()) return
    setBusy(true)
    setError(null)
    try {
      const r = await requestRefund(payment.id, {
        amount: refundAmount,
        reason: refundReason.trim(),
        notes:  refundNotes.trim(),
      })
      setRefunds((prev) => [...prev, r])
      setRefundAmount('')
      setRefundReason('')
      setRefundNotes('')
      setShowReqForm(false)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg ?? 'Failed to request refund.')
    } finally {
      setBusy(false)
    }
  }

  async function handleApprove(refundId: string) {
    setBusy(true)
    setError(null)
    try {
      const updated = await approveRefund(refundId)
      setRefunds((prev) => prev.map((r) => r.id === refundId ? updated : r))
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg ?? 'Failed to approve refund.')
    } finally {
      setBusy(false)
    }
  }

  async function handleReject(refundId: string) {
    if (!rejectReason.trim()) return
    setBusy(true)
    setError(null)
    try {
      const updated = await rejectRefund(refundId, { reason: rejectReason.trim() })
      setRefunds((prev) => prev.map((r) => r.id === refundId ? updated : r))
      setRejectingId(null)
      setRejectReason('')
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg ?? 'Failed to reject refund.')
    } finally {
      setBusy(false)
    }
  }

  async function handleProcess(refundId: string) {
    setBusy(true)
    setError(null)
    try {
      const updated = await processRefund(refundId)
      setRefunds((prev) => prev.map((r) => r.id === refundId ? updated : r))
      onRefunded?.()
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { message?: string } } })?.response?.data?.message
      setError(msg ?? 'Failed to process refund.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-800 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">Refunds</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Payment {payment.payment_number} · {fmt(payment.amount)}
            · Refundable: <span className="text-white">{fmt(refundable)}</span>
          </p>
        </div>
        <button onClick={onClose} className="text-gray-600 hover:text-gray-400">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="px-5 py-4 space-y-4">
        {error && (
          <div className="rounded-lg bg-red-900/30 border border-red-800 text-red-400 px-3 py-2 text-xs">{error}</div>
        )}

        {/* Existing refunds */}
        {refunds.length > 0 && (
          <div className="space-y-2">
            {refunds.map((r) => (
              <div key={r.id} className="rounded-lg border border-gray-800 bg-gray-800/40 px-4 py-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-gray-500">{r.refund_number}</span>
                    <RefundStatusBadge status={r.status} />
                  </div>
                  <span className="text-sm font-semibold text-white">{fmt(r.amount)}</span>
                </div>
                <p className="text-xs text-gray-400">{r.reason}</p>
                {r.rejection_reason && (
                  <p className="text-xs text-red-400 mt-1">Rejected: {r.rejection_reason}</p>
                )}
                {r.requested_by_name && (
                  <p className="text-xs text-gray-600 mt-1">Requested by {r.requested_by_name}</p>
                )}

                {/* Actions */}
                {r.status === 'REQUESTED' && canApprove && (
                  <div className="flex gap-2 mt-2">
                    <button
                      disabled={busy}
                      onClick={() => handleApprove(r.id)}
                      className="px-3 py-1 text-xs rounded-lg bg-green-800 text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      Approve
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => setRejectingId(r.id)}
                      className="px-3 py-1 text-xs rounded-lg border border-red-800/60 text-red-400 hover:bg-red-900/20 disabled:opacity-50"
                    >
                      Reject
                    </button>
                  </div>
                )}
                {rejectingId === r.id && (
                  <div className="mt-2 space-y-2">
                    <input
                      type="text"
                      placeholder="Rejection reason"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-1.5 text-xs"
                    />
                    <div className="flex gap-2">
                      <button
                        disabled={busy || !rejectReason.trim()}
                        onClick={() => handleReject(r.id)}
                        className="px-3 py-1 text-xs rounded-lg bg-red-800 text-white hover:bg-red-700 disabled:opacity-50"
                      >
                        Confirm Rejection
                      </button>
                      <button
                        onClick={() => { setRejectingId(null); setRejectReason('') }}
                        className="px-3 py-1 text-xs rounded-lg border border-gray-700 text-gray-400"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {r.status === 'APPROVED' && canProcess && (
                  <button
                    disabled={busy}
                    onClick={() => handleProcess(r.id)}
                    className="mt-2 px-3 py-1 text-xs rounded-lg bg-blue-800 text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    Mark Processed
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {refunds.length === 0 && (
          <p className="text-center text-sm text-gray-600 py-4">No refunds yet.</p>
        )}

        {/* Request new refund */}
        {canRequest && refundable > 0 && payment.status === 'COMPLETED' && (
          <>
            {!showReqForm ? (
              <button
                onClick={() => setShowReqForm(true)}
                className="w-full py-2 rounded-lg border border-gray-700 text-gray-300 text-sm hover:bg-gray-800"
              >
                + Request Refund
              </button>
            ) : (
              <div className="rounded-lg border border-gray-700 bg-gray-800/40 px-4 py-3 space-y-3">
                <p className="text-xs font-medium text-gray-300">New Refund Request</p>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Amount (max {fmt(refundable)})</label>
                  <input
                    type="number"
                    min="0.01"
                    max={refundable}
                    step="0.01"
                    placeholder="0.00"
                    value={refundAmount}
                    onChange={(e) => setRefundAmount(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Reason <span className="text-red-400">*</span></label>
                  <input
                    type="text"
                    placeholder="Reason for refund…"
                    value={refundReason}
                    onChange={(e) => setRefundReason(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Notes (optional)</label>
                  <input
                    type="text"
                    placeholder="Additional notes…"
                    value={refundNotes}
                    onChange={(e) => setRefundNotes(e.target.value)}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    disabled={busy || !refundAmount || !refundReason.trim()}
                    onClick={handleRequestRefund}
                    className="flex-1 py-2 text-sm rounded-lg bg-brand-700 text-white hover:bg-brand-600 disabled:opacity-50"
                  >
                    {busy ? 'Requesting…' : 'Submit Request'}
                  </button>
                  <button
                    onClick={() => { setShowReqForm(false); setRefundAmount(''); setRefundReason('') }}
                    className="px-4 py-2 text-sm rounded-lg border border-gray-700 text-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
