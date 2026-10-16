// =============================================================================
// RestaurantFlow — Enterprise Branch Detail Page
// Phase 20
// =============================================================================

import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  CheckCircle2, XCircle, Clock, Users, ShoppingCart,
  CalendarDays, ListChecks, AlertTriangle, RefreshCw,
} from 'lucide-react'
import { enterpriseApi, BranchDetail, ChecklistItem } from '@/services/enterprise'

const STATUS_COLOR: Record<string, string> = {
  ACTIVE:             'bg-green-100 text-green-700',
  TEMPORARILY_CLOSED: 'bg-orange-100 text-orange-700',
  SCHEDULED_CLOSURE:  'bg-yellow-100 text-yellow-800',
  MAINTENANCE:        'bg-blue-100 text-blue-700',
  INACTIVE:           'bg-gray-100 text-gray-600',
}

const CHECKLIST_COLOR: Record<string, string> = {
  READY:   'bg-green-100 text-green-700',
  WARNING: 'bg-yellow-100 text-yellow-800',
  BLOCKED: 'bg-red-100 text-red-700',
}

function ConfirmDialog({
  title, message, confirmLabel, onConfirm, onCancel, loading,
}: {
  title: string; message: string; confirmLabel: string
  onConfirm: () => void; onCancel: () => void; loading?: boolean
}) {
  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
      <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6">
        <h3 id="confirm-title" className="text-base font-semibold text-gray-900 mb-2">{title}</h3>
        <p className="text-sm text-gray-600 mb-5">{message}</p>
        <div className="flex justify-end gap-3">
          <button onClick={onCancel} className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Processing…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

export function EnterpriseBranchDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [detail, setDetail] = useState<BranchDetail | null>(null)
  const [checklist, setChecklist] = useState<ChecklistItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<{ action: 'open' | 'close' | 'reopen'; reason: string } | null>(null)
  const [showChecklist, setShowChecklist] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  function showToast(msg: string, type: 'success' | 'error') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  async function load() {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const d = await enterpriseApi.getBranchDetail(id)
      setDetail(d)
    } catch {
      setError('Failed to load branch details.')
    } finally {
      setLoading(false)
    }
  }

  async function loadChecklist() {
    if (!id) return
    try {
      const res = await enterpriseApi.getOpeningChecklist(id)
      setChecklist(res.checklist)
      setShowChecklist(true)
    } catch {
      showToast('Failed to load checklist.', 'error')
    }
  }

  async function executeAction() {
    if (!confirm || !id) return
    setActionLoading(true)
    try {
      if (confirm.action === 'open') await enterpriseApi.openBranch(id, confirm.reason)
      else if (confirm.action === 'close') await enterpriseApi.closeBranch(id, confirm.reason)
      else await enterpriseApi.reopenBranch(id, confirm.reason)
      showToast(`Branch ${confirm.action}ed successfully.`, 'success')
      setConfirm(null)
      load()
    } catch (e: any) {
      showToast(e?.response?.data?.message ?? 'Action failed.', 'error')
      setConfirm(null)
    } finally {
      setActionLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const isActive = detail?.operational_status === 'ACTIVE'
  const isClosed = detail?.operational_status !== 'ACTIVE'

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm text-white ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`} role="alert">
          {toast.msg}
        </div>
      )}

      {/* Confirm dialog */}
      {confirm && (
        <ConfirmDialog
          title={`${confirm.action.charAt(0).toUpperCase() + confirm.action.slice(1)} Branch`}
          message={`Are you sure you want to ${confirm.action} this branch? ${confirm.reason ? `Reason: ${confirm.reason}` : ''}`}
          confirmLabel={confirm.action.charAt(0).toUpperCase() + confirm.action.slice(1)}
          onConfirm={executeAction}
          onCancel={() => setConfirm(null)}
          loading={actionLoading}
        />
      )}

      {loading && (
        <div className="h-64 bg-gray-100 rounded-xl animate-pulse" aria-label="Loading branch detail" />
      )}

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700" role="alert">{error}</div>
      )}

      {detail && (
        <>
          {/* Header */}
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{detail.branch_name}</h1>
              <p className="text-sm text-gray-500 mt-1">{detail.branch_code}</p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLOR[detail.operational_status] ?? 'bg-gray-100 text-gray-600'}`}>
                {detail.operational_status.replace(/_/g, ' ')}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-3 flex-wrap mb-6">
            {isClosed && (
              <button
                onClick={() => setConfirm({ action: 'open', reason: '' })}
                className="px-4 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2"
              >
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Open Branch
              </button>
            )}
            {isActive && (
              <button
                onClick={() => setConfirm({ action: 'close', reason: 'Manual closure' })}
                className="px-4 py-2 text-sm bg-orange-600 text-white rounded-lg hover:bg-orange-700 flex items-center gap-2"
              >
                <XCircle className="h-4 w-4" aria-hidden="true" /> Close Branch
              </button>
            )}
            {isClosed && detail.operational_status !== 'ACTIVE' && (
              <button
                onClick={() => setConfirm({ action: 'reopen', reason: '' })}
                className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" /> Reopen
              </button>
            )}
            <button
              onClick={loadChecklist}
              className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <ListChecks className="h-4 w-4" aria-hidden="true" /> Opening Checklist
            </button>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {[
              { label: 'Active Staff',    value: detail.active_staff_count,   icon: <Users className="h-4 w-4" /> },
              { label: 'Active Counters', value: detail.active_counter_count ?? '—', icon: <ShoppingCart className="h-4 w-4" /> },
              { label: 'Active Closures', value: detail.active_closures.length, icon: <CalendarDays className="h-4 w-4" /> },
              { label: 'Schedule Days',   value: detail.operating_hours.length, icon: <Clock className="h-4 w-4" /> },
            ].map(({ label, value, icon }) => (
              <div key={label} className="bg-white rounded-lg border border-gray-200 p-4">
                <div className="flex items-center gap-2 text-gray-500 mb-1 text-sm">{icon}<span>{label}</span></div>
                <p className="text-2xl font-bold text-gray-900">{value}</p>
              </div>
            ))}
          </div>

          {/* Opening Checklist */}
          {showChecklist && checklist && (
            <div className="bg-white rounded-xl border border-gray-200 mb-6">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <ListChecks className="h-5 w-5 text-blue-600" aria-hidden="true" />
                  Opening Checklist
                </h2>
                <button onClick={() => setShowChecklist(false)} className="text-xs text-gray-500 hover:text-gray-700">Dismiss</button>
              </div>
              <ul className="divide-y divide-gray-100">
                {checklist.map((item) => (
                  <li key={item.type} className="px-4 py-3 flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{item.label}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{item.detail}</p>
                    </div>
                    <span className={`flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium ${CHECKLIST_COLOR[item.status] ?? 'bg-gray-100 text-gray-600'}`}>
                      {item.status}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Operating Hours */}
          <div className="bg-white rounded-xl border border-gray-200 mb-6">
            <div className="px-4 py-3 border-b border-gray-100">
              <h2 className="font-semibold text-gray-900">Operating Hours</h2>
            </div>
            {detail.operating_hours.length === 0 ? (
              <p className="px-4 py-6 text-sm text-gray-400 text-center">No schedule configured.</p>
            ) : (
              <table className="min-w-full divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>
                    <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Day</th>
                    <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Opens</th>
                    <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Closes</th>
                    <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {detail.operating_hours.map((h) => (
                    <tr key={h.day_of_week}>
                      <td className="px-4 py-2 text-sm font-medium text-gray-900">{h.day_of_week}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">{h.is_closed ? '—' : h.opening_time ?? '—'}</td>
                      <td className="px-4 py-2 text-sm text-gray-600">{h.is_closed ? '—' : h.closing_time ?? '—'}</td>
                      <td className="px-4 py-2">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${h.is_closed ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                          {h.is_closed ? 'Closed' : 'Open'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Active Closures */}
          {detail.active_closures.length > 0 && (
            <div className="bg-white rounded-xl border border-orange-200 mb-6">
              <div className="px-4 py-3 border-b border-orange-100 bg-orange-50 rounded-t-xl">
                <h2 className="font-semibold text-orange-900 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4" aria-hidden="true" />
                  Active Closures
                </h2>
              </div>
              <ul className="divide-y divide-gray-100">
                {detail.active_closures.map((c) => (
                  <li key={c.id} className="px-4 py-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium text-gray-900">{c.closure_type.replace(/_/g, ' ')}</p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {new Date(c.start_datetime).toLocaleString()} → {new Date(c.end_datetime).toLocaleString()}
                        </p>
                        {c.reason && <p className="text-xs text-gray-500 mt-0.5">{c.reason}</p>}
                      </div>
                      <span className="text-xs px-2 py-0.5 bg-orange-100 text-orange-700 rounded-full">{c.status}</span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  )
}
