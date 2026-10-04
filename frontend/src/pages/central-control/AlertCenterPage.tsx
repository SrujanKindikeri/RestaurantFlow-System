// =============================================================================
// RestaurantFlow — Central Control Alert Center
// Phase 15
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { centralControlApi, CentralAlert } from '@/services/centralControl'
import { AlertTriangle, RefreshCw, Search, Filter, CheckCircle, XCircle } from 'lucide-react'

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-100 text-red-800 border-red-200',
  HIGH:     'bg-orange-100 text-orange-800 border-orange-200',
  MEDIUM:   'bg-yellow-100 text-yellow-800 border-yellow-200',
  LOW:      'bg-blue-100 text-blue-800 border-blue-200',
  INFO:     'bg-gray-100 text-gray-700 border-gray-200',
}

const STATUS_COLORS: Record<string, string> = {
  OPEN:         'bg-red-50 text-red-700',
  ACKNOWLEDGED: 'bg-yellow-50 text-yellow-700',
  RESOLVED:     'bg-green-50 text-green-700',
  DISMISSED:    'bg-gray-100 text-gray-500',
  EXPIRED:      'bg-gray-50 text-gray-400',
}

function AlertRow({
  alert,
  onAcknowledge,
  onResolve,
  onDismiss,
}: {
  alert: CentralAlert
  onAcknowledge: (id: string) => void
  onResolve: (id: string) => void
  onDismiss: (id: string) => void
}) {
  const [loading, setLoading] = useState(false)

  const handle = async (action: () => Promise<void>) => {
    setLoading(true)
    try { await action() } catch { /* handled by parent */ } finally { setLoading(false) }
  }

  const isActive = alert.status === 'OPEN' || alert.status === 'ACKNOWLEDGED'

  return (
    <tr className="hover:bg-gray-50">
      <td className="px-4 py-3">
        <span
          className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${SEVERITY_COLORS[alert.severity] || SEVERITY_COLORS.INFO}`}
          aria-label={`Severity: ${alert.severity}`}
        >
          {alert.severity}
        </span>
      </td>
      <td className="px-4 py-3">
        <p className="font-medium text-gray-900 text-sm">{alert.title}</p>
        <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{alert.message}</p>
      </td>
      <td className="px-4 py-3 text-xs text-gray-500">{alert.alert_type.replace(/_/g, ' ')}</td>
      <td className="px-4 py-3 text-xs text-gray-500">{alert.restaurant?.name || '—'}</td>
      <td className="px-4 py-3 text-xs text-gray-500">{alert.branch?.name || '—'}</td>
      <td className="px-4 py-3">
        <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[alert.status] || ''}`}>
          {alert.status}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-gray-500">
        {new Date(alert.detected_at).toLocaleString()}
      </td>
      <td className="px-4 py-3">
        {isActive && (
          <div className="flex items-center gap-1">
            {alert.status === 'OPEN' && (
              <button
                onClick={() => handle(() => onAcknowledge(alert.id))}
                disabled={loading}
                className="px-2 py-1 text-xs bg-yellow-50 text-yellow-700 border border-yellow-200 
                           rounded hover:bg-yellow-100 focus:outline-none focus:ring-2 focus:ring-yellow-500 
                           disabled:opacity-50"
                aria-label={`Acknowledge alert: ${alert.title}`}
              >
                Ack
              </button>
            )}
            <button
              onClick={() => handle(() => onResolve(alert.id))}
              disabled={loading}
              className="px-2 py-1 text-xs bg-green-50 text-green-700 border border-green-200 
                         rounded hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-green-500 
                         disabled:opacity-50"
              aria-label={`Resolve alert: ${alert.title}`}
            >
              Resolve
            </button>
            <button
              onClick={() => handle(() => onDismiss(alert.id))}
              disabled={loading}
              className="px-2 py-1 text-xs bg-gray-50 text-gray-600 border border-gray-200 
                         rounded hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-400 
                         disabled:opacity-50"
              aria-label={`Dismiss alert: ${alert.title}`}
            >
              Dismiss
            </button>
          </div>
        )}
      </td>
    </tr>
  )
}

export function AlertCenterPage() {
  const [alerts, setAlerts] = useState<CentralAlert[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState({ severity: '', status: '', alert_type: '', search: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await centralControlApi.getAlerts({
        page,
        page_size: 20,
        ...(filters.severity ? { severity: filters.severity } : {}),
        ...(filters.status   ? { status: filters.status }     : {}),
        ...(filters.alert_type ? { alert_type: filters.alert_type } : {}),
        ...(filters.search   ? { search: filters.search }     : {}),
      })
      setAlerts(res.results)
      setTotal(res.count)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load alerts.')
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => { load() }, [load])

  const handleAcknowledge = async (id: string) => {
    await centralControlApi.acknowledgeAlert(id)
    load()
  }
  const handleResolve = async (id: string) => {
    const note = window.prompt('Resolution note (required for CRITICAL alerts):') || ''
    await centralControlApi.resolveAlert(id, note)
    load()
  }
  const handleDismiss = async (id: string) => {
    await centralControlApi.dismissAlert(id)
    load()
  }

  return (
    <main className="p-4 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <AlertTriangle className="w-6 h-6 text-orange-500" aria-hidden="true" />
            Alert Center
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} alerts total</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 
                     rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 
                     disabled:opacity-50"
          aria-label="Refresh alerts"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-40">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" aria-hidden="true" />
          <input
            type="search"
            placeholder="Search alerts…"
            value={filters.search}
            onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); setPage(1) }}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg 
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Search alerts"
          />
        </div>
        <select
          value={filters.severity}
          onChange={e => { setFilters(f => ({ ...f, severity: e.target.value })); setPage(1) }}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Filter by severity"
        >
          <option value="">All Severities</option>
          {['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={filters.status}
          onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1) }}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Filter by status"
        >
          <option value="">All Statuses</option>
          {['OPEN', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED', 'EXPIRED'].map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select
          value={filters.alert_type}
          onChange={e => { setFilters(f => ({ ...f, alert_type: e.target.value })); setPage(1) }}
          className="px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Filter by alert type"
        >
          <option value="">All Types</option>
          {['KITCHEN_DELAY','KITCHEN_BACKLOG','LOW_STOCK','OUT_OF_STOCK',
            'PAYMENT_FAILURE','PAYABLE_OVERDUE','COUNTER_SESSION_EXCEPTION'].map(t => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm mb-4" role="alert">{error}</div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
        <table className="w-full text-sm" aria-label="Alerts list">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              <th scope="col" className="px-4 py-3 text-left">Severity</th>
              <th scope="col" className="px-4 py-3 text-left">Alert</th>
              <th scope="col" className="px-4 py-3 text-left">Type</th>
              <th scope="col" className="px-4 py-3 text-left">Restaurant</th>
              <th scope="col" className="px-4 py-3 text-left">Branch</th>
              <th scope="col" className="px-4 py-3 text-left">Status</th>
              <th scope="col" className="px-4 py-3 text-left">Detected</th>
              <th scope="col" className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {loading && alerts.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">Loading…</td></tr>
            ) : alerts.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-gray-400">No alerts found.</td></tr>
            ) : alerts.map(alert => (
              <AlertRow
                key={alert.id}
                alert={alert}
                onAcknowledge={handleAcknowledge}
                onResolve={handleResolve}
                onDismiss={handleDismiss}
              />
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <p>Showing {(page - 1) * 20 + 1}–{Math.min(page * 20, total)} of {total}</p>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              aria-label="Previous page"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page * 20 >= total}
              className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              aria-label="Next page"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </main>
  )
}
