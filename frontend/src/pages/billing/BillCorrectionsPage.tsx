// =============================================================================
// RestaurantFlow — Bill Corrections Page
// Phase 8
// =============================================================================

import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { listCorrections, approveCorrection, rejectCorrection } from '@/services/billing'
import { useAuth } from '@/contexts/AuthContext'
import type { BillCorrectionRequest, CorrectionStatus } from '@/types'
import { cn } from '@/utils/cn'

const STATUS_COLORS: Record<CorrectionStatus, string> = {
  PENDING:   'bg-amber-900/40 border-amber-700 text-amber-400',
  APPROVED:  'bg-green-900/40 border-green-700 text-green-400',
  REJECTED:  'bg-red-900/40 border-red-700 text-red-400',
  CANCELLED: 'bg-gray-800 border-gray-700 text-gray-500',
}

export function BillCorrectionsPage() {
  const { user } = useAuth()

  const [corrections, setCorrections] = useState<BillCorrectionRequest[]>([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [busy, setBusy]               = useState<string | null>(null)

  // Approve/reject inline
  const [rejectId, setRejectId]   = useState<string | null>(null)
  const [rejectNote, setRejectNote] = useState('')

  const canApprove = user?.scope?.permissions?.includes('bill.correction.approve')

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (statusFilter) params.status = statusFilter
    listCorrections(params)
      .then((r) => setCorrections(r.results))
      .catch(() => setError('Failed to load corrections.'))
      .finally(() => setLoading(false))
  }, [statusFilter])

  useEffect(() => { load() }, [load])

  async function handleApprove(id: string) {
    setBusy(id)
    try {
      await approveCorrection(id, { review_note: 'Approved.' })
      load()
    } catch { setError('Approval failed.') }
    finally { setBusy(null) }
  }

  async function handleReject(id: string) {
    if (!rejectNote.trim()) return
    setBusy(id)
    try {
      await rejectCorrection(id, { review_note: rejectNote })
      setRejectId(null)
      setRejectNote('')
      load()
    } catch { setError('Rejection failed.') }
    finally { setBusy(null) }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Bill Corrections</h1>
          <p className="text-sm text-gray-500 mt-0.5">Review and approve correction requests</p>
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-900/30 border border-red-800 text-red-400 px-4 py-3 text-sm">{error}</div>}

      {/* Status filter */}
      <div className="flex gap-3">
        {['', 'PENDING', 'APPROVED', 'REJECTED', 'CANCELLED'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cn(
              'px-3 py-1.5 text-xs rounded-lg border transition-colors',
              statusFilter === s
                ? 'bg-brand-600 border-brand-500 text-white'
                : 'border-gray-700 text-gray-500 hover:text-gray-300 hover:border-gray-600'
            )}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900/60 overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-gray-500 text-sm">Loading…</div>
        ) : corrections.length === 0 ? (
          <div className="py-12 text-center text-gray-500 text-sm">No correction requests found.</div>
        ) : (
          <div className="divide-y divide-gray-800">
            {corrections.map((cr) => (
              <div key={cr.id} className="px-4 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium border',
                        STATUS_COLORS[cr.status],
                      )}>
                        {cr.status}
                      </span>
                      <span className="text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded border border-gray-700">
                        {cr.correction_type.replace('_', ' ')}
                      </span>
                      <Link
                        to={`/billing/bills/${cr.bill}`}
                        className="text-xs font-mono text-brand-400 hover:text-brand-300"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {cr.bill_number}
                      </Link>
                    </div>
                    <p className="text-sm text-gray-300 mt-2">{cr.reason}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      Requested by {cr.requested_by_name ?? cr.requested_by_email} ·{' '}
                      {new Date(cr.created_at).toLocaleString()}
                    </p>
                    {cr.review_note && (
                      <p className="text-xs text-gray-400 mt-1 italic">Note: {cr.review_note}</p>
                    )}
                    {cr.reviewed_by_name && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        Reviewed by {cr.reviewed_by_name} · {cr.reviewed_at ? new Date(cr.reviewed_at).toLocaleString() : ''}
                      </p>
                    )}
                  </div>

                  {/* Actions */}
                  {canApprove && cr.status === 'PENDING' && (
                    <div className="flex-shrink-0 flex flex-col gap-2">
                      {rejectId === cr.id ? (
                        <div className="space-y-2">
                          <textarea
                            placeholder="Rejection note (required)…"
                            value={rejectNote}
                            onChange={(e) => setRejectNote(e.target.value)}
                            rows={2}
                            className="text-xs bg-gray-800 border border-gray-700 text-gray-300 rounded px-2 py-1 w-48 resize-none"
                          />
                          <div className="flex gap-1">
                            <button
                              disabled={!rejectNote.trim() || busy === cr.id}
                              onClick={() => handleReject(cr.id)}
                              className="px-3 py-1 text-xs rounded bg-red-800 text-white hover:bg-red-700 disabled:opacity-50"
                            >Reject</button>
                            <button onClick={() => { setRejectId(null); setRejectNote('') }} className="px-2 py-1 text-xs text-gray-500">✕</button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <button
                            disabled={busy === cr.id}
                            onClick={() => handleApprove(cr.id)}
                            className="px-3 py-1 text-xs rounded bg-green-800 text-white hover:bg-green-700 disabled:opacity-50"
                          >Approve</button>
                          <button
                            onClick={() => { setRejectId(cr.id); setRejectNote('') }}
                            className="px-3 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:bg-gray-800"
                          >Reject</button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
