// =============================================================================
// RestaurantFlow — Expense Detail Page
// Phase 12
// =============================================================================

import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  getExpense, submitExpense, approveExpense,
  rejectExpense, cancelExpense, listAttachments, uploadAttachment,
} from '@/services/financials'
import type { ExpenseDetail, ExpenseAttachment } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string) =>
  Number(v).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const STATUS_BADGE: Record<string, string> = {
  DRAFT:      'bg-gray-700 text-gray-400 border-gray-600',
  SUBMITTED:  'bg-blue-500/10 text-blue-400 border-blue-500/20',
  APPROVED:   'bg-green-500/10 text-green-400 border-green-500/20',
  REJECTED:   'bg-red-500/10 text-red-400 border-red-500/20',
  CANCELLED:  'bg-gray-700 text-gray-500 border-gray-600',
}

export function ExpenseDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()

  const [expense, setExpense] = useState<ExpenseDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)
  const [rejectModal, setRejectModal] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [rejectError, setRejectError] = useState('')
  const [uploadError, setUploadError] = useState<string | null>(null)

  const load = () => {
    if (!id) return
    setLoading(true)
    getExpense(id)
      .then(setExpense)
      .catch((e) => setError(e?.response?.data?.message ?? 'Failed to load expense'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [id])

  const doAction = async (action: string, extra?: string) => {
    if (!id) return
    setActionLoading(true)
    try {
      if (action === 'submit') await submitExpense(id)
      else if (action === 'approve') await approveExpense(id)
      else if (action === 'reject' && extra) await rejectExpense(id, extra)
      else if (action === 'cancel') await cancelExpense(id)
      load()
    } catch (e: any) {
      alert(e?.response?.data?.message ?? 'Action failed')
    } finally {
      setActionLoading(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!id || !e.target.files?.[0]) return
    setUploadError(null)
    const file = e.target.files[0]
    try {
      await uploadAttachment(id, file)
      load()
    } catch (err: any) {
      setUploadError(err?.response?.data?.message ?? 'Upload failed')
    }
    e.target.value = ''
  }

  if (loading) {
    return <div className="p-6 text-gray-400">Loading…</div>
  }

  if (error || !expense) {
    return (
      <div className="p-6">
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error ?? 'Expense not found.'}</div>
      </div>
    )
  }

  const canSubmit  = hasPermission('expense.submit')
  const canApprove = hasPermission('expense.approve')
  const canReject  = hasPermission('expense.reject')
  const canCancel  = hasPermission('expense.cancel')
  const canUpload  = hasPermission('expense.attachment.create')

  return (
    <div className="p-6 max-w-4xl space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <button onClick={() => navigate(-1)} className="text-sm text-gray-400 hover:text-white mb-3 flex items-center gap-1">← Back</button>
          <h1 className="text-2xl font-semibold text-white">{expense.title}</h1>
          <p className="text-sm text-gray-500 mt-1 font-mono">{expense.expense_number}</p>
        </div>
        <span className={`text-sm px-3 py-1 rounded-full border ${STATUS_BADGE[expense.status] ?? ''}`}>
          {expense.status}
        </span>
      </div>

      {/* Financial summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Base Amount</p>
          <p className="text-xl font-bold text-white">₹{fmt(expense.amount)}</p>
        </div>
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Tax</p>
          <p className="text-xl font-bold text-white">₹{fmt(expense.tax_amount)}</p>
        </div>
        <div className="bg-brand-500/10 border border-brand-500/20 rounded-xl p-4">
          <p className="text-xs text-gray-500 mb-1">Total</p>
          <p className="text-xl font-bold text-brand-400">₹{fmt(expense.total_amount)}</p>
        </div>
      </div>

      {/* Details */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl divide-y divide-gray-700">
        <div className="grid grid-cols-2 gap-px">
          {[
            { label: 'Category', value: `${expense.category_name} (${expense.category_code})` },
            { label: 'Payment Status', value: expense.payment_status.replace('_', ' ') },
            { label: 'Expense Date', value: expense.expense_date },
            { label: 'Due Date', value: expense.due_date ?? '—' },
            { label: 'Vendor', value: expense.vendor_name || '—' },
            { label: 'Vendor Ref', value: expense.vendor_reference || '—' },
            { label: 'Branch', value: expense.branch_name ?? 'Restaurant-level' },
            { label: 'Created By', value: expense.created_by_detail?.email ?? '—' },
          ].map(({ label, value }) => (
            <div key={label} className="px-5 py-3">
              <p className="text-xs text-gray-500 mb-0.5">{label}</p>
              <p className="text-sm text-gray-200">{value}</p>
            </div>
          ))}
        </div>
        {expense.description && (
          <div className="px-5 py-3">
            <p className="text-xs text-gray-500 mb-0.5">Description</p>
            <p className="text-sm text-gray-200">{expense.description}</p>
          </div>
        )}
        {expense.rejection_reason && (
          <div className="px-5 py-3 bg-red-500/5">
            <p className="text-xs text-red-400 mb-0.5">Rejection Reason</p>
            <p className="text-sm text-red-300">{expense.rejection_reason}</p>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex gap-3">
        {canSubmit && expense.status === 'DRAFT' && (
          <button onClick={() => doAction('submit')} disabled={actionLoading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg disabled:opacity-50">
            Submit for Approval
          </button>
        )}
        {canApprove && expense.status === 'SUBMITTED' && (
          <button onClick={() => doAction('approve')} disabled={actionLoading}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg disabled:opacity-50">
            Approve
          </button>
        )}
        {canReject && expense.status === 'SUBMITTED' && (
          <button onClick={() => setRejectModal(true)}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg">
            Reject
          </button>
        )}
        {canCancel && expense.status === 'DRAFT' && (
          <button onClick={() => doAction('cancel')} disabled={actionLoading}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm font-medium rounded-lg border border-gray-600 disabled:opacity-50">
            Cancel
          </button>
        )}
      </div>

      {/* Attachments */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-gray-400">Attachments</h2>
          {canUpload && (
            <label className="cursor-pointer px-3 py-1.5 text-xs text-brand-400 border border-brand-500/30 rounded-lg hover:bg-brand-500/10 transition-colors">
              + Upload
              <input type="file" className="hidden" onChange={handleFileUpload}
                accept=".pdf,.jpg,.jpeg,.png,.webp,.docx,.xlsx" />
            </label>
          )}
        </div>
        {uploadError && <p className="text-xs text-red-400 mb-2">{uploadError}</p>}
        {expense.attachments.length === 0 ? (
          <p className="text-sm text-gray-600">No attachments yet.</p>
        ) : (
          <div className="space-y-2">
            {expense.attachments.map((att) => (
              <div key={att.id} className="flex items-center justify-between bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
                <div>
                  <p className="text-sm text-white">{att.file_name}</p>
                  <p className="text-xs text-gray-500">{att.file_type} · {(att.file_size / 1024).toFixed(1)} KB</p>
                </div>
                {att.file_url && (
                  <a href={att.file_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-brand-400 hover:text-brand-300">
                    Download
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Approval history */}
      {expense.approvals.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-gray-400 mb-3">Approval History</h2>
          <div className="space-y-2">
            {expense.approvals.map((appr) => (
              <div key={appr.id} className="bg-gray-800 border border-gray-700 rounded-lg px-4 py-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-200">
                    Requested by {appr.requested_by_detail?.email}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded border ${
                    appr.status === 'APPROVED' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                    appr.status === 'REJECTED' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                    'bg-blue-500/10 text-blue-400 border-blue-500/20'
                  }`}>
                    {appr.status}
                  </span>
                </div>
                {appr.reviewed_by_detail && (
                  <p className="text-xs text-gray-500 mt-1">
                    Reviewed by {appr.reviewed_by_detail.email}
                    {appr.reviewed_at && ` on ${new Date(appr.reviewed_at).toLocaleDateString()}`}
                  </p>
                )}
                {appr.rejection_reason && (
                  <p className="text-xs text-red-400 mt-1">Reason: {appr.rejection_reason}</p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Reject modal */}
      {rejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/80">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">Reject Expense</h3>
            <label className="block text-sm text-gray-400 mb-2">Reason <span className="text-red-400">*</span></label>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => { setRejectReason(e.target.value); setRejectError('') }}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
              placeholder="Provide a clear reason…"
            />
            {rejectError && <p className="text-xs text-red-400 mt-1">{rejectError}</p>}
            <div className="flex gap-3 mt-4">
              <button onClick={async () => {
                if (!rejectReason.trim() || rejectReason.trim().length < 5) {
                  setRejectError('Reason must be at least 5 characters.')
                  return
                }
                await doAction('reject', rejectReason)
                setRejectModal(false)
                setRejectReason('')
              }} className="flex-1 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg">
                Confirm Reject
              </button>
              <button onClick={() => { setRejectModal(false); setRejectReason(''); setRejectError('') }}
                className="flex-1 py-2 bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
