// =============================================================================
// RestaurantFlow — Enterprise Staff Management Page
// Phase 20
// =============================================================================

import { useEffect, useState } from 'react'
import { Users, RefreshCw, ArrowRight, CheckCircle2, XCircle } from 'lucide-react'
import { enterpriseApi, StaffAssignment, StaffTransfer } from '@/services/enterprise'

const TRANSFER_STATUS_COLOR: Record<string, string> = {
  REQUESTED: 'bg-yellow-100 text-yellow-800',
  APPROVED:  'bg-blue-100 text-blue-700',
  REJECTED:  'bg-red-100 text-red-700',
  COMPLETED: 'bg-green-100 text-green-700',
  CANCELLED: 'bg-gray-100 text-gray-600',
}

type Tab = 'assignments' | 'transfers'

export function EnterpriseStaffPage() {
  const [tab, setTab] = useState<Tab>('assignments')
  const [assignments, setAssignments] = useState<StaffAssignment[]>([])
  const [transfers, setTransfers] = useState<StaffTransfer[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [restaurantId, setRestaurantId] = useState('')
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  function showToast(msg: string, type: 'success' | 'error') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  async function loadAssignments() {
    if (!restaurantId) return
    setLoading(true)
    setError(null)
    try {
      const res = await enterpriseApi.getStaff(restaurantId)
      setAssignments(Array.isArray(res) ? res : [])
    } catch {
      setError('Failed to load staff assignments.')
    } finally {
      setLoading(false)
    }
  }

  async function loadTransfers() {
    if (!restaurantId) return
    setLoading(true)
    setError(null)
    try {
      const res = await enterpriseApi.getTransfers(restaurantId)
      setTransfers(Array.isArray(res) ? res : [])
    } catch {
      setError('Failed to load transfers.')
    } finally {
      setLoading(false)
    }
  }

  async function handleApprove(transferId: string) {
    try {
      await enterpriseApi.approveTransfer(transferId)
      showToast('Transfer approved.', 'success')
      loadTransfers()
    } catch {
      showToast('Approval failed.', 'error')
    }
  }

  async function handleReject(transferId: string) {
    try {
      await enterpriseApi.rejectTransfer(transferId, 'Rejected by manager')
      showToast('Transfer rejected.', 'success')
      loadTransfers()
    } catch {
      showToast('Rejection failed.', 'error')
    }
  }

  async function handleComplete(transferId: string) {
    try {
      await enterpriseApi.completeTransfer(transferId)
      showToast('Transfer completed.', 'success')
      loadTransfers()
    } catch (e: any) {
      showToast(e?.response?.data?.message ?? 'Completion failed.', 'error')
    }
  }

  useEffect(() => {
    if (!restaurantId) return
    if (tab === 'assignments') loadAssignments()
    else loadTransfers()
  }, [tab, restaurantId])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm text-white ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`} role="alert">
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Users className="h-6 w-6 text-blue-600" aria-hidden="true" />
            Staff Management
          </h1>
          <p className="text-sm text-gray-500 mt-1">Branch assignments and transfers</p>
        </div>
        <button
          onClick={() => tab === 'assignments' ? loadAssignments() : loadTransfers()}
          disabled={loading || !restaurantId}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          aria-label="Refresh staff data"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Restaurant input */}
      <div className="mb-5">
        <label htmlFor="rest-id" className="block text-xs font-medium text-gray-600 mb-1">Restaurant ID</label>
        <input
          id="rest-id"
          type="text"
          value={restaurantId}
          onChange={(e) => setRestaurantId(e.target.value)}
          placeholder="Restaurant UUID…"
          className="w-full max-w-sm text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-gray-200">
        {(['assignments', 'transfers'] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition ${tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-4" role="alert">{error}</div>
      )}

      {!restaurantId && (
        <p className="text-center py-12 text-gray-400 text-sm">Enter a Restaurant ID to view staff data.</p>
      )}

      {loading && restaurantId && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {/* Assignments tab */}
      {!loading && tab === 'assignments' && assignments.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-100" role="table">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Staff</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Branch</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell">Role</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden lg:table-cell">Primary</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {assignments.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900">{a.user.full_name}</p>
                    <p className="text-xs text-gray-500">{a.user.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-sm text-gray-900">{a.branch.name}</p>
                    <p className="text-xs text-gray-500">{a.branch.code}</p>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600 hidden md:table-cell">{a.role_name}</td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    {a.is_primary
                      ? <CheckCircle2 className="h-4 w-4 text-green-500" aria-label="Primary assignment" />
                      : <XCircle className="h-4 w-4 text-gray-400" aria-label="Secondary assignment" />}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${a.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                      {a.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Transfers tab */}
      {!loading && tab === 'transfers' && transfers.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-100" role="table">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Staff</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Route</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell">Requested</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {transfers.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900">{t.user.full_name}</p>
                    <p className="text-xs text-gray-500">{t.user.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5 text-sm text-gray-700">
                      <span>{t.source_branch.name}</span>
                      <ArrowRight className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" aria-hidden="true" />
                      <span>{t.destination_branch.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${TRANSFER_STATUS_COLOR[t.status] ?? 'bg-gray-100 text-gray-600'}`}>
                      {t.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 hidden md:table-cell">
                    {new Date(t.requested_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {t.status === 'REQUESTED' && (
                        <>
                          <button onClick={() => handleApprove(t.id)} className="text-xs text-green-600 hover:underline">Approve</button>
                          <button onClick={() => handleReject(t.id)} className="text-xs text-red-500 hover:underline">Reject</button>
                        </>
                      )}
                      {t.status === 'APPROVED' && (
                        <button onClick={() => handleComplete(t.id)} className="text-xs text-blue-600 hover:underline">Complete</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && restaurantId && (
        (tab === 'assignments' && assignments.length === 0) ||
        (tab === 'transfers' && transfers.length === 0)
      ) && (
        <div className="text-center py-12 text-gray-400">
          <Users className="h-10 w-10 mx-auto mb-2 opacity-40" aria-hidden="true" />
          <p>No {tab} found.</p>
        </div>
      )}
    </div>
  )
}
