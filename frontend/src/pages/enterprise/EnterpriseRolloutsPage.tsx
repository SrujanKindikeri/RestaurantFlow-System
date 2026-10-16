// =============================================================================
// RestaurantFlow — Enterprise Rollouts Page
// Phase 20
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart2, RefreshCw, Play, Eye, CheckCircle2, XCircle, Plus } from 'lucide-react'
import { enterpriseApi, MenuRollout, RolloutPreview } from '@/services/enterprise'

const STATUS_COLOR: Record<string, string> = {
  DRAFT:               'bg-gray-100 text-gray-600',
  PENDING_APPROVAL:    'bg-yellow-100 text-yellow-800',
  APPROVED:            'bg-blue-100 text-blue-700',
  SCHEDULED:           'bg-purple-100 text-purple-700',
  RUNNING:             'bg-orange-100 text-orange-800',
  COMPLETED:           'bg-green-100 text-green-700',
  PARTIALLY_COMPLETED: 'bg-yellow-100 text-yellow-800',
  FAILED:              'bg-red-100 text-red-700',
  CANCELLED:           'bg-gray-100 text-gray-500',
}

export function EnterpriseRolloutsPage() {
  const [rollouts, setRollouts] = useState<MenuRollout[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [restaurantId, setRestaurantId] = useState('')
  const [preview, setPreview] = useState<RolloutPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)
  const [executing, setExecuting] = useState<string | null>(null)

  function showToast(msg: string, type: 'success' | 'error') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  async function load() {
    if (!restaurantId) { setLoading(false); return }
    setLoading(true)
    setError(null)
    try {
      const res = await enterpriseApi.getRollouts(restaurantId)
      setRollouts(Array.isArray(res) ? res : [])
    } catch {
      setError('Failed to load rollouts.')
    } finally {
      setLoading(false)
    }
  }

  async function handlePreview(rolloutId: string) {
    setPreviewLoading(true)
    try {
      const p = await enterpriseApi.previewRollout(rolloutId)
      setPreview(p)
    } catch {
      showToast('Failed to generate preview.', 'error')
    } finally {
      setPreviewLoading(false)
    }
  }

  async function handleExecute(rolloutId: string) {
    setExecuting(rolloutId)
    try {
      const result = await enterpriseApi.executeRollout(rolloutId)
      showToast(`Executed: ${result.successful.length} succeeded, ${result.failed.length} failed.`, result.failed.length > 0 ? 'error' : 'success')
      load()
    } catch (e: any) {
      showToast(e?.response?.data?.message ?? 'Execution failed.', 'error')
    } finally {
      setExecuting(null)
    }
  }

  async function handleApprove(rolloutId: string) {
    try {
      await enterpriseApi.approveRollout(rolloutId)
      showToast('Rollout approved.', 'success')
      load()
    } catch {
      showToast('Approval failed.', 'error')
    }
  }

  useEffect(() => { if (restaurantId) load() }, [restaurantId])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm text-white ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`} role="alert">
          {toast.msg}
        </div>
      )}

      {/* Preview modal */}
      {preview && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 overflow-auto" role="dialog" aria-modal="true" aria-labelledby="preview-title">
          <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-auto">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 id="preview-title" className="font-semibold text-gray-900">Rollout Preview — {preview.menu_item.name}</h3>
              <button onClick={() => setPreview(null)} className="text-sm text-gray-500 hover:text-gray-700">Close</button>
            </div>
            <div className="p-5">
              <div className="flex gap-4 mb-4 text-sm">
                <div><span className="text-gray-500">Total:</span> <strong>{preview.total_branches}</strong></div>
                <div><span className="text-green-600">Will change:</span> <strong>{preview.will_change_count}</strong></div>
                <div><span className="text-orange-600">Will skip:</span> <strong>{preview.will_skip_count}</strong></div>
              </div>
              <div className="space-y-2">
                {preview.branches.map((b) => (
                  <div key={b.branch_id} className={`flex items-start justify-between px-3 py-2 rounded-lg text-sm ${b.will_change ? 'bg-green-50' : 'bg-gray-50'}`}>
                    <div>
                      <p className="font-medium text-gray-900">{b.branch_name}</p>
                      <p className="text-xs text-gray-500">
                        {b.current_value ?? '—'} → {b.new_value ?? '—'}
                        {b.skip_reason && <span className="ml-1 text-orange-600">({b.skip_reason})</span>}
                      </p>
                    </div>
                    <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full ${b.will_change ? 'bg-green-100 text-green-700' : 'bg-orange-100 text-orange-700'}`}>
                      {b.will_change ? 'Will change' : 'Skip'}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart2 className="h-6 w-6 text-blue-600" aria-hidden="true" />
            Menu & Price Rollouts
          </h1>
          <p className="text-sm text-gray-500 mt-1">Orchestrated branch-wide changes</p>
        </div>
        <button
          onClick={load}
          disabled={loading || !restaurantId}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          aria-label="Refresh rollouts"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Restaurant filter */}
      <div className="mb-5">
        <label htmlFor="rest-filter" className="block text-xs font-medium text-gray-600 mb-1">Restaurant ID</label>
        <input
          id="rest-filter"
          type="text"
          value={restaurantId}
          onChange={(e) => setRestaurantId(e.target.value)}
          placeholder="Restaurant UUID…"
          className="w-full max-w-sm text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
        />
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-4" role="alert">{error}</div>
      )}

      {!restaurantId && (
        <p className="text-center py-12 text-gray-400 text-sm">Enter a Restaurant ID to view rollouts.</p>
      )}

      {loading && restaurantId && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!loading && restaurantId && rollouts.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <BarChart2 className="h-10 w-10 mx-auto mb-2 opacity-40" aria-hidden="true" />
          <p>No rollouts found.</p>
        </div>
      )}

      {!loading && rollouts.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-100" role="table">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Item</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell">Scope</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rollouts.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-gray-900">{r.menu_item.name}</p>
                    <p className="text-xs text-gray-500">{r.menu_item.sku}</p>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">{r.rollout_type}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[r.status] ?? 'bg-gray-100 text-gray-600'}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600 hidden md:table-cell">{r.target_scope}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handlePreview(r.id)}
                        disabled={previewLoading}
                        className="text-xs text-blue-600 hover:underline flex items-center gap-1"
                        title="Preview rollout impact"
                      >
                        <Eye className="h-3.5 w-3.5" aria-hidden="true" /> Preview
                      </button>
                      {r.status === 'DRAFT' && (
                        <button
                          onClick={() => handleApprove(r.id)}
                          className="text-xs text-green-600 hover:underline flex items-center gap-1"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> Approve
                        </button>
                      )}
                      {(r.status === 'APPROVED' || r.status === 'DRAFT') && (
                        <button
                          onClick={() => handleExecute(r.id)}
                          disabled={executing === r.id}
                          className="text-xs text-orange-600 hover:underline flex items-center gap-1 disabled:opacity-50"
                        >
                          <Play className="h-3.5 w-3.5" aria-hidden="true" />
                          {executing === r.id ? '…' : 'Execute'}
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
