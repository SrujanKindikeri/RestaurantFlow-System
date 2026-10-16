// =============================================================================
// RestaurantFlow — Enterprise Branches Page
// Phase 20
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { GitBranch, RefreshCw, CheckCircle2, XCircle, Clock, Wrench } from 'lucide-react'
import { enterpriseApi, BranchStatus } from '@/services/enterprise'

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  ACTIVE:              { label: 'Active',             color: 'bg-green-100 text-green-700',  icon: <CheckCircle2 className="h-3.5 w-3.5" /> },
  TEMPORARILY_CLOSED:  { label: 'Temp. Closed',       color: 'bg-orange-100 text-orange-700', icon: <Clock className="h-3.5 w-3.5" /> },
  SCHEDULED_CLOSURE:   { label: 'Sched. Closure',     color: 'bg-yellow-100 text-yellow-800', icon: <Clock className="h-3.5 w-3.5" /> },
  MAINTENANCE:         { label: 'Maintenance',        color: 'bg-blue-100 text-blue-700',    icon: <Wrench className="h-3.5 w-3.5" /> },
  INACTIVE:            { label: 'Inactive',           color: 'bg-gray-100 text-gray-600',    icon: <XCircle className="h-3.5 w-3.5" /> },
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? { label: status, color: 'bg-gray-100 text-gray-600', icon: null }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`} role="status">
      <span aria-hidden="true">{cfg.icon}</span>
      {cfg.label}
    </span>
  )
}

export function EnterpriseBranchesPage() {
  const [branches, setBranches] = useState<BranchStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const res = await enterpriseApi.getBranches(statusFilter ? { status: statusFilter } : undefined)
      setBranches(Array.isArray(res) ? res : (res as any).results ?? [])
    } catch {
      setError('Failed to load branches.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [statusFilter])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <GitBranch className="h-6 w-6 text-blue-600" aria-hidden="true" />
            Branch Management
          </h1>
          <p className="text-sm text-gray-500 mt-1">Operational status for all branches</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          aria-label="Refresh branch list"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="mb-4 flex gap-2 flex-wrap">
        {['', 'ACTIVE', 'TEMPORARILY_CLOSED', 'MAINTENANCE', 'INACTIVE'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={`px-3 py-1.5 text-sm rounded-lg border transition ${
              statusFilter === s
                ? 'bg-blue-600 text-white border-blue-600'
                : 'border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            {s === '' ? 'All' : STATUS_CONFIG[s]?.label ?? s}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-4" role="alert">
          {error}
        </div>
      )}

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!loading && branches.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <GitBranch className="h-10 w-10 mx-auto mb-2 opacity-40" aria-hidden="true" />
          <p>No branches found.</p>
        </div>
      )}

      {/* Table */}
      {!loading && branches.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-100" role="table">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Branch</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden md:table-cell">Last Changed</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider hidden lg:table-cell">Reason</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {branches.map((b) => (
                <tr key={b.id} className="hover:bg-gray-50 transition">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 text-sm">{b.branch.name}</div>
                    <div className="text-xs text-gray-500">{b.branch.code}</div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={b.status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 hidden md:table-cell">
                    {b.status_changed_at
                      ? new Date(b.status_changed_at).toLocaleString()
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 hidden lg:table-cell max-w-xs truncate">
                    {b.status_reason || '—'}
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/enterprise/branches/${b.branch.id}`}
                      className="text-xs text-blue-600 hover:underline focus:outline-none focus:ring-1 focus:ring-blue-500 rounded"
                    >
                      View
                    </Link>
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
