// =============================================================================
// RestaurantFlow — Counter Sessions Page
// Phase 4
// =============================================================================

import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useSessions, useCloseSession, useForceCloseSession } from '@/hooks/useCounters'
import { PageHeader } from '@/components/ui/PageHeader'
import { Modal } from '@/components/ui/Modal'
import { SessionStatusBadge } from '@/components/counter/CounterStatusBadge'
import { CloseSessionForm } from '@/components/counter/CloseSessionForm'
import { ForceCloseForm } from '@/components/counter/ForceCloseForm'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/contexts/AuthContext'
import { formatCurrency, formatDifference } from '@/utils/money'
import type { CounterSession, CloseSessionPayload, ForceCloseSessionPayload } from '@/types'

export function CounterSessionsPage() {
  const [searchParams] = useSearchParams()
  const { hasPermission } = useAuth()
  const { toast } = useToast()

  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') ?? '')
  const [closeSession, setCloseSession] = useState<CounterSession | null>(null)
  const [forceClose, setForceClose]     = useState<CounterSession | null>(null)

  const params: Record<string, string | number> = {}
  const counterParam = searchParams.get('counter')
  const branchParam  = searchParams.get('branch')
  if (counterParam) params.counter = counterParam
  if (branchParam)  params.branch  = branchParam
  if (statusFilter) params.status  = statusFilter

  const { data, isLoading, isError } = useSessions(params)
  const closeMutation      = useCloseSession(closeSession?.id ?? '')
  const forceCloseMutation = useForceCloseSession(forceClose?.id ?? '')

  const canClose      = hasPermission('counter.session.close')
  const canForceClose = hasPermission('counter.session.force_close')

  async function handleClose(data: CloseSessionPayload) {
    await closeMutation.mutateAsync(data)
    setCloseSession(null)
    toast('Session closed.', 'success')
  }

  async function handleForceClose(data: ForceCloseSessionPayload) {
    await forceCloseMutation.mutateAsync(data)
    setForceClose(null)
    toast('Session force-closed.', 'warning')
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Counter Sessions"
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Sessions' }]}
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          aria-label="Filter by status"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="CLOSED">Closed</option>
          <option value="FORCE_CLOSED">Force Closed</option>
        </select>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load sessions.
        </div>
      )}

      {!isLoading && !isError && data?.results.length === 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-12 text-center">
          <p className="text-gray-500 text-sm">No sessions found.</p>
        </div>
      )}

      {!isLoading && data && data.results.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-x-auto">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Counter</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden sm:table-cell">Opened By</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden md:table-cell">Opened At</th>
                <th className="text-right px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Opening</th>
                <th className="text-right px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden lg:table-cell">Expected</th>
                <th className="text-right px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden lg:table-cell">Actual</th>
                <th className="text-right px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden lg:table-cell">Diff</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Status</th>
                <th className="px-4 py-3" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {data.results.map((s) => {
                const diff = formatDifference(s.cash_difference)
                return (
                  <tr key={s.id} className="border-b border-gray-800/50 hover:bg-gray-800/20">
                    <td className="px-4 py-3">
                      <Link
                        to={`/counters/${s.counter}`}
                        className="text-gray-200 hover:text-brand-400 font-medium transition-colors"
                      >
                        {s.counter_code}
                      </Link>
                      <p className="text-xs text-gray-600">{s.branch_name}</p>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell text-gray-400 text-xs">
                      {s.opened_by_name}
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell text-gray-500 text-xs">
                      {new Date(s.opened_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-gray-300">
                      {formatCurrency(s.opening_cash)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-gray-400 hidden lg:table-cell">
                      {formatCurrency(s.expected_cash)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-xs text-gray-400 hidden lg:table-cell">
                      {s.actual_cash ? formatCurrency(s.actual_cash) : '—'}
                    </td>
                    <td className={`px-4 py-3 text-right font-mono text-xs hidden lg:table-cell ${diff.colorClass}`}>
                      {s.cash_difference !== null ? diff.label : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <SessionStatusBadge status={s.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        {s.status === 'OPEN' && canClose && (
                          <button
                            onClick={() => setCloseSession(s)}
                            className="text-xs text-red-400 hover:text-red-300 transition-colors px-2 py-1 rounded hover:bg-red-500/5"
                          >
                            Close
                          </button>
                        )}
                        {s.status === 'OPEN' && canForceClose && (
                          <button
                            onClick={() => setForceClose(s)}
                            className="text-xs text-gray-500 hover:text-red-400 transition-colors px-2 py-1 rounded hover:bg-red-500/5"
                          >
                            Force
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-700">
            {data.count} session{data.count !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      {/* Close modal */}
      {closeSession && (
        <Modal
          open={!!closeSession}
          onClose={() => setCloseSession(null)}
          title="Close Counter Session"
          size="md"
        >
          <CloseSessionForm
            session={closeSession}
            onSubmit={handleClose}
            onCancel={() => setCloseSession(null)}
            loading={closeMutation.isPending}
          />
        </Modal>
      )}

      {/* Force close modal */}
      {forceClose && (
        <Modal
          open={!!forceClose}
          onClose={() => setForceClose(null)}
          title="Force Close Session"
          size="md"
        >
          <ForceCloseForm
            session={forceClose}
            onSubmit={handleForceClose}
            onCancel={() => setForceClose(null)}
            loading={forceCloseMutation.isPending}
          />
        </Modal>
      )}
    </div>
  )
}
