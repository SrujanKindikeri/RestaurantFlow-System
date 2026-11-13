// =============================================================================
// RestaurantFlow — Central Control Issue Center
// Phase 15
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { centralControlApi, CentralIssue } from '@/services/centralControl'
import { FileText, RefreshCw, Search, PlusCircle } from 'lucide-react'

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800',
  HIGH:     'bg-orange-100 text-orange-800',
  MEDIUM:   'bg-yellow-100 text-yellow-800',
  LOW:      'bg-blue-100 text-blue-800',
}

const STATUS_COLORS: Record<string, string> = {
  OPEN:        'bg-red-50 text-red-700',
  ASSIGNED:    'bg-purple-50 text-purple-700',
  IN_PROGRESS: 'bg-blue-50 text-blue-700',
  RESOLVED:    'bg-green-50 text-green-700',
  CLOSED:      'bg-gray-100 text-gray-500',
  CANCELLED:   'bg-gray-50 text-gray-400',
}

function IssueRow({ issue, onAction }: { issue: CentralIssue; onAction: () => void }) {
  const [loading, setLoading] = useState(false)

  const act = async (fn: () => Promise<unknown>) => {
    setLoading(true)
    try { await fn(); onAction() } catch { /* ignore */ } finally { setLoading(false) }
  }

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3 text-sm font-medium text-gray-900">
        <span className="line-clamp-1">{issue.title}</span>
        <span className="text-xs text-gray-400 mt-0.5 block">{issue.category}</span>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${SEVERITY_COLORS[issue.severity] || ''}`}>
          {issue.severity}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[issue.status] || ''}`}>
          {issue.status.replace('_', ' ')}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-gray-500">{issue.restaurant?.name || '—'}</td>
      <td className="px-4 py-3 text-xs text-gray-500">{issue.assigned_to?.email || 'Unassigned'}</td>
      <td className="px-4 py-3 text-xs text-gray-500">
        {issue.due_at ? new Date(issue.due_at).toLocaleDateString() : '—'}
      </td>
      <td className="px-4 py-3">
        <div className="flex gap-1 flex-wrap">
          {issue.status === 'OPEN' && (
            <button
              onClick={() => act(() => centralControlApi.startIssue(issue.id))}
              disabled={loading}
              className="px-2 py-1 text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded 
                         hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              aria-label={`Start issue: ${issue.title}`}
            >
              Start
            </button>
          )}
          {(issue.status === 'ASSIGNED' || issue.status === 'IN_PROGRESS') && (
            <button
              onClick={() => {
                const note = window.prompt('Resolution note:') || ''
                act(() => centralControlApi.resolveIssue(issue.id, note))
              }}
              disabled={loading}
              className="px-2 py-1 text-xs bg-green-50 text-green-700 border border-green-200 rounded 
                         hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50"
              aria-label={`Resolve issue: ${issue.title}`}
            >
              Resolve
            </button>
          )}
          {issue.status === 'RESOLVED' && (
            <button
              onClick={() => act(() => centralControlApi.closeIssue(issue.id))}
              disabled={loading}
              className="px-2 py-1 text-xs bg-gray-50 text-gray-700 border border-gray-200 rounded 
                         hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-400 disabled:opacity-50"
              aria-label={`Close issue: ${issue.title}`}
            >
              Close
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

export function IssueCenterPage() {
  const [issues, setIssues] = useState<CentralIssue[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ severity: '', status: '', category: '', search: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await centralControlApi.getIssues({
        page,
        page_size: 20,
        ...(filters.severity ? { severity: filters.severity } : {}),
        ...(filters.status   ? { status: filters.status }     : {}),
        ...(filters.category ? { category: filters.category } : {}),
        ...(filters.search   ? { search: filters.search }     : {}),
      })
      setIssues(res.results)
      setTotal(res.count)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load issues.')
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => { load() }, [load])

  return (
    <main className="p-4 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-500" aria-hidden="true" />
            Issue Center
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} issues total</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg 
                       hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            aria-label="Refresh issues"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-40">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" aria-hidden="true" />
          <input
            type="search"
            placeholder="Search issues…"
            value={filters.search}
            onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); setPage(1) }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Search issues"
          />
        </div>
        {[
          { key: 'severity', label: 'All Severities', options: ['CRITICAL','HIGH','MEDIUM','LOW'] },
          { key: 'status',   label: 'All Statuses',   options: ['OPEN','ASSIGNED','IN_PROGRESS','RESOLVED','CLOSED','CANCELLED'] },
          { key: 'category', label: 'All Categories', options: ['OPERATIONS','KITCHEN','INVENTORY','PAYMENTS','FINANCE','ACCOUNTING','ACCESS','SYSTEM'] },
        ].map(({ key, label, options }) => (
          <select
            key={key}
            value={(filters as Record<string,string>)[key]}
            onChange={e => { setFilters(f => ({ ...f, [key]: e.target.value })); setPage(1) }}
            className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label={`Filter by ${key}`}
          >
            <option value="">{label}</option>
            {options.map(o => <option key={o} value={o}>{o.replace('_',' ')}</option>)}
          </select>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm mb-4" role="alert">{error}</div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm" aria-label="Issues list">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th scope="col" className="px-4 py-3 text-left">Issue</th>
              <th scope="col" className="px-4 py-3 text-left">Severity</th>
              <th scope="col" className="px-4 py-3 text-left">Status</th>
              <th scope="col" className="px-4 py-3 text-left">Restaurant</th>
              <th scope="col" className="px-4 py-3 text-left">Assignee</th>
              <th scope="col" className="px-4 py-3 text-left">Due</th>
              <th scope="col" className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && issues.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : issues.length === 0 ? (
              <tr><td colSpan={7} className="px-4 py-8 text-center text-gray-400">No issues found.</td></tr>
            ) : issues.map(issue => (
              <IssueRow key={issue.id} issue={issue} onAction={load} />
            ))}
          </tbody>
        </table>
      </div>

      {total > 20 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <p>Showing {(page-1)*20+1}–{Math.min(page*20,total)} of {total}</p>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1}
              className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              aria-label="Previous page">
              Previous
            </button>
            <button onClick={() => setPage(p => p+1)} disabled={page*20>=total}
              className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              aria-label="Next page">
              Next
            </button>
          </div>
        </div>
      )}
    </main>
  )
}
