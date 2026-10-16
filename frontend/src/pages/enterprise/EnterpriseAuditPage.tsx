// =============================================================================
// RestaurantFlow — Enterprise Audit Log Page
// Phase 20
// =============================================================================

import { useEffect, useState } from 'react'
import { ClipboardList, RefreshCw } from 'lucide-react'
import { enterpriseApi, EnterpriseAuditLog } from '@/services/enterprise'

const ACTION_COLOR: Record<string, string> = {
  BRANCH_OPENED:              'bg-green-100 text-green-700',
  BRANCH_CLOSED:              'bg-orange-100 text-orange-700',
  BRANCH_REOPENED:            'bg-blue-100 text-blue-700',
  BRANCH_STATUS_CHANGED:      'bg-blue-50 text-blue-600',
  CONFIGURATION_CREATED:      'bg-purple-100 text-purple-700',
  CONFIGURATION_UPDATED:      'bg-purple-100 text-purple-700',
  CONFIGURATION_ROLLED_BACK:  'bg-yellow-100 text-yellow-800',
  MENU_ROLLOUT_CREATED:       'bg-gray-100 text-gray-700',
  MENU_ROLLOUT_EXECUTED:      'bg-green-100 text-green-700',
  MENU_ROLLOUT_FAILED:        'bg-red-100 text-red-700',
  STAFF_ASSIGNED:             'bg-blue-100 text-blue-700',
  STAFF_TRANSFER_REQUESTED:   'bg-yellow-100 text-yellow-800',
  STAFF_TRANSFER_COMPLETED:   'bg-green-100 text-green-700',
  APPROVAL_POLICY_CREATED:    'bg-purple-50 text-purple-600',
  APPROVAL_POLICY_UPDATED:    'bg-purple-50 text-purple-600',
}

export function EnterpriseAuditPage() {
  const [logs, setLogs] = useState<EnterpriseAuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionFilter, setActionFilter] = useState('')
  const [branchFilter, setBranchFilter] = useState('')

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (actionFilter) params.action = actionFilter
      if (branchFilter) params.branch_id = branchFilter
      const res = await enterpriseApi.getAuditLogs(params)
      setLogs(Array.isArray(res) ? res : [])
    } catch {
      setError('Failed to load audit log.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [actionFilter, branchFilter])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <ClipboardList className="h-6 w-6 text-blue-600" aria-hidden="true" />
            Enterprise Audit Log
          </h1>
          <p className="text-sm text-gray-500 mt-1">Immutable record of all enterprise actions</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          aria-label="Refresh audit log"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="mb-5 flex gap-3 flex-wrap">
        <div>
          <label htmlFor="action-filter" className="block text-xs font-medium text-gray-600 mb-1">Action</label>
          <select
            id="action-filter"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="">All Actions</option>
            {Object.keys(ACTION_COLOR).map((a) => (
              <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="branch-filter" className="block text-xs font-medium text-gray-600 mb-1">Branch ID</label>
          <input
            id="branch-filter"
            type="text"
            value={branchFilter}
            onChange={(e) => setBranchFilter(e.target.value)}
            placeholder="Branch UUID…"
            className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-4" role="alert">{error}</div>
      )}

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-14 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!loading && logs.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <ClipboardList className="h-10 w-10 mx-auto mb-2 opacity-40" aria-hidden="true" />
          <p>No audit entries found.</p>
        </div>
      )}

      {!loading && logs.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-100" role="table">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">When</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Description</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell">Actor</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden lg:table-cell">Branch</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium whitespace-nowrap ${ACTION_COLOR[log.action] ?? 'bg-gray-100 text-gray-600'}`}>
                      {log.action.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-700 max-w-sm">
                    {log.description}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 hidden md:table-cell">
                    {log.performed_by?.email ?? 'System'}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 hidden lg:table-cell">
                    {log.branch?.name ?? '—'}
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
