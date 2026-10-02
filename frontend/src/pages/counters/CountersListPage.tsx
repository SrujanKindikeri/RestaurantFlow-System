// =============================================================================
// RestaurantFlow — Counters List Page
// Phase 4
// =============================================================================

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCounters, useCreateCounter, useDisableCounter, useReactivateCounter } from '@/hooks/useCounters'
import { useAllBranches } from '@/hooks/useBranches'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { CounterStatusBadge, CounterStatusDot } from '@/components/counter/CounterStatusBadge'
import { CounterForm } from '@/components/counter/CounterForm'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/contexts/AuthContext'
import type { Counter, CounterCreatePayload, CounterUpdatePayload } from '@/types'

export function CountersListPage() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()

  const [branchFilter, setBranchFilter]   = useState('')
  const [statusFilter, setStatusFilter]   = useState('')
  const [showCreate, setShowCreate]       = useState(false)
  const [confirmAction, setConfirmAction] = useState<{
    type: 'disable' | 'reactivate'
    counter: Counter
  } | null>(null)

  const params: Record<string, string | number> = {}
  if (branchFilter) params.branch = branchFilter
  if (statusFilter) params.status = statusFilter

  const { data, isLoading, isError } = useCounters(params)
  const { data: branchesData }       = useAllBranches()
  const createCounter   = useCreateCounter()
  const disableCounter  = useDisableCounter()
  const reactivate      = useReactivateCounter()

  const canCreate  = hasPermission('counter.create')
  const canDisable = hasPermission('counter.disable')
  const canUpdate  = hasPermission('counter.update')

  async function handleCreate(payload: CounterCreatePayload | CounterUpdatePayload) {
    await createCounter.mutateAsync(payload as CounterCreatePayload)
    setShowCreate(false)
    toast('Counter created.', 'success')
  }

  async function handleConfirm() {
    if (!confirmAction) return
    try {
      if (confirmAction.type === 'disable') {
        await disableCounter.mutateAsync(confirmAction.counter.id)
        toast(`"${confirmAction.counter.name}" disabled.`, 'warning')
      } else {
        await reactivate.mutateAsync(confirmAction.counter.id)
        toast(`"${confirmAction.counter.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmAction(null)
    }
  }

  const counterTypeLabel: Record<string, string> = {
    MAIN_BILLING: 'Main Billing',
    TAKEAWAY: 'Takeaway',
    SNACKS: 'Snacks',
    DRIVE_THROUGH: 'Drive Through',
    OTHER: 'Other',
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Counters"
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Counters' }]}
        actions={
          canCreate ? (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              + Add Counter
            </Button>
          ) : undefined
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          aria-label="Filter by branch"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={branchFilter}
          onChange={(e) => setBranchFilter(e.target.value)}
        >
          <option value="">All Branches</option>
          {branchesData?.results.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>

        <select
          aria-label="Filter by status"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
          <option value="MAINTENANCE">Maintenance</option>
        </select>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load counters.
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && data?.results.length === 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-12 text-center">
          <p className="text-gray-500 text-sm">No counters found.</p>
          {canCreate && (
            <Button
              variant="primary"
              size="sm"
              className="mt-4"
              onClick={() => setShowCreate(true)}
            >
              Add your first counter
            </Button>
          )}
        </div>
      )}

      {/* Table */}
      {!isLoading && data && data.results.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-hidden">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Code</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Name</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden sm:table-cell">Type</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden md:table-cell">Branch</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Status</th>
                <th className="px-4 py-3" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {data.results.map((counter) => (
                <tr key={counter.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                      {counter.code}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <Link
                      to={`/counters/${counter.id}`}
                      className="text-gray-200 hover:text-brand-400 font-medium transition-colors"
                    >
                      {counter.name}
                    </Link>
                    {counter.location && (
                      <p className="text-xs text-gray-600 mt-0.5">{counter.location}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <span className="text-gray-500 text-xs">
                      {counterTypeLabel[counter.counter_type] ?? counter.counter_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell text-gray-500 text-xs">
                    {counter.branch_name}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      <CounterStatusDot status={counter.status} />
                      <CounterStatusBadge status={counter.status} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Link to={`/counters/${counter.id}`}>
                        <Button variant="ghost" size="sm">View</Button>
                      </Link>
                      {counter.status === 'ACTIVE' && canDisable && (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'disable', counter })}
                        >
                          Disable
                        </Button>
                      )}
                      {counter.status !== 'ACTIVE' && canUpdate && (
                        <Button
                          variant="success"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'reactivate', counter })}
                        >
                          Reactivate
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-700">
            {data.count} counter{data.count !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      {/* Create modal */}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Counter" size="lg">
        <CounterForm
          branchId={branchFilter || undefined}
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          submitLabel="Create Counter"
          loading={createCounter.isPending}
        />
      </Modal>

      {/* Confirm dialog */}
      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirm}
        title={
          confirmAction?.type === 'disable'
            ? `Disable "${confirmAction.counter.name}"?`
            : `Reactivate "${confirmAction?.counter.name}"?`
        }
        message={
          confirmAction?.type === 'disable'
            ? 'This counter will be marked inactive. No new sessions can be opened.'
            : 'This counter will be set back to Active.'
        }
        confirmLabel={confirmAction?.type === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirmAction?.type === 'disable' ? 'danger' : 'success'}
        loading={disableCounter.isPending || reactivate.isPending}
      />
    </div>
  )
}
