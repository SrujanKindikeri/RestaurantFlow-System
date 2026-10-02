// =============================================================================
// RestaurantFlow — Counter Detail Page
// Phase 4
// =============================================================================

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  useCounter,
  useUpdateCounter,
  useDisableCounter,
  useReactivateCounter,
  useOpenSession,
  useCloseSession,
  useForceCloseSession,
  useCreateAssignment,
  useDeactivateAssignment,
  useShifts,
} from '@/hooks/useCounters'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { CounterStatusBadge, SessionStatusBadge } from '@/components/counter/CounterStatusBadge'
import { CounterForm } from '@/components/counter/CounterForm'
import { OpenSessionForm } from '@/components/counter/OpenSessionForm'
import { CloseSessionForm } from '@/components/counter/CloseSessionForm'
import { ForceCloseForm } from '@/components/counter/ForceCloseForm'
import { AssignCounterForm } from '@/components/counter/AssignCounterForm'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/contexts/AuthContext'
import { formatCurrency } from '@/utils/money'
import type { CounterUpdatePayload, CounterAssignmentCreatePayload, ForceCloseSessionPayload } from '@/types'

export function CounterDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { hasPermission } = useAuth()
  const { toast } = useToast()

  const { data: counter, isLoading, isError } = useCounter(id ?? '')
  const { data: shiftsData } = useShifts(
    counter ? { branch: counter.branch } : undefined,
  )
  const updateCounter       = useUpdateCounter(id ?? '')
  const disableCounter      = useDisableCounter()
  const reactivateCounter   = useReactivateCounter()
  const openSession         = useOpenSession(id ?? '')
  const createAssignment    = useCreateAssignment()
  const deactivateAssignment = useDeactivateAssignment()

  const [showEdit, setShowEdit]             = useState(false)
  const [showOpen, setShowOpen]             = useState(false)
  const [showAssign, setShowAssign]         = useState(false)
  const [confirmDisable, setConfirmDisable] = useState(false)
  const [confirmReactivate, setConfirmReactivate] = useState(false)

  // Session modals — keyed on session id
  const [closeSessionId, setCloseSessionId]           = useState<string | null>(null)
  const [forceCloseSessionId, setForceCloseSessionId] = useState<string | null>(null)

  const closeSession      = useCloseSession(closeSessionId ?? '')
  const forceCloseSession = useForceCloseSession(forceCloseSessionId ?? '')

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="h-48 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
      </div>
    )
  }

  if (isError || !counter) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Counter not found or you don't have access.
        </div>
      </div>
    )
  }

  const currentSession = counter.current_session
  const activeAssignments = counter.active_assignments ?? []
  const shifts = shiftsData?.results ?? []

  async function handleEdit(payload: CounterUpdatePayload) {
    await updateCounter.mutateAsync(payload)
    setShowEdit(false)
    toast('Counter updated.', 'success')
  }

  async function handleOpenSession(data: { opening_cash: string; shift?: string | null }) {
    await openSession.mutateAsync(data)
    setShowOpen(false)
    toast('Counter session opened.', 'success')
  }

  async function handleCloseSession(data: { actual_cash: string; closing_note: string }) {
    await closeSession.mutateAsync(data)
    setCloseSessionId(null)
    toast('Session closed.', 'success')
  }

  async function handleForceClose(data: ForceCloseSessionPayload) {
    await forceCloseSession.mutateAsync(data)
    setForceCloseSessionId(null)
    toast('Session force-closed.', 'warning')
  }

  async function handleAssign(data: CounterAssignmentCreatePayload) {
    await createAssignment.mutateAsync(data)
    setShowAssign(false)
    toast('Cashier assigned.', 'success')
  }

  const sessionForClose = currentSession
    ? {
        id: currentSession.id,
        counter: counter.id,
        counter_code: counter.code,
        counter_name: counter.name,
        branch_id: counter.branch,
        branch_name: counter.branch_name,
        restaurant_name: counter.restaurant_name,
        shift: null,
        shift_name: null,
        opened_by: 0,
        opened_by_email: currentSession.opened_by_email,
        opened_by_name: currentSession.opened_by_name,
        closed_by: null,
        closed_by_email: null,
        opened_at: currentSession.opened_at,
        closed_at: null,
        opening_cash: currentSession.opening_cash,
        expected_cash: currentSession.expected_cash,
        actual_cash: null,
        cash_difference: null,
        status: currentSession.status,
        closing_note: '',
        created_at: currentSession.opened_at,
        updated_at: currentSession.opened_at,
      } as const
    : null

  const canUpdate       = hasPermission('counter.update')
  const canDisable      = hasPermission('counter.disable')
  const canAssign       = hasPermission('counter.assign')
  const canOpenSession  = hasPermission('counter.session.open')
  const canCloseSession = hasPermission('counter.session.close')
  const canForceClose   = hasPermission('counter.session.force_close')

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10 space-y-6">
      <PageHeader
        title={`${counter.code} — ${counter.name}`}
        crumbs={[
          { label: 'Home', to: '/' },
          { label: 'Counters', to: '/counters' },
          { label: counter.name },
        ]}
        actions={
          <div className="flex gap-2 flex-wrap">
            {canUpdate && (
              <Button variant="secondary" size="sm" onClick={() => setShowEdit(true)}>
                Edit
              </Button>
            )}
            {canAssign && (
              <Button variant="secondary" size="sm" onClick={() => setShowAssign(true)}>
                Assign Cashier
              </Button>
            )}
            {counter.status === 'ACTIVE' && !currentSession && canOpenSession && (
              <Button variant="primary" size="sm" onClick={() => setShowOpen(true)}>
                Open Counter
              </Button>
            )}
            {currentSession && canCloseSession && (
              <Button
                variant="danger"
                size="sm"
                onClick={() => setCloseSessionId(currentSession.id)}
              >
                Close Counter
              </Button>
            )}
            {currentSession && canForceClose && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setForceCloseSessionId(currentSession.id)}
              >
                Force Close
              </Button>
            )}
            {counter.status === 'ACTIVE' && canDisable && (
              <Button variant="danger" size="sm" onClick={() => setConfirmDisable(true)}>
                Disable
              </Button>
            )}
            {counter.status !== 'ACTIVE' && canUpdate && (
              <Button variant="success" size="sm" onClick={() => setConfirmReactivate(true)}>
                Reactivate
              </Button>
            )}
          </div>
        }
      />

      {/* Counter info */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-5 space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
            {counter.code}
          </span>
          <CounterStatusBadge status={counter.status} />
          <span className="text-xs text-gray-600">{counter.counter_type.replace('_', ' ')}</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Branch</p>
            <p className="text-gray-300">{counter.branch_name}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Restaurant</p>
            <p className="text-gray-300">{counter.restaurant_name}</p>
          </div>
          {counter.location && (
            <div>
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Location</p>
              <p className="text-gray-300">{counter.location}</p>
            </div>
          )}
          {counter.description && (
            <div className="sm:col-span-2">
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Description</p>
              <p className="text-gray-400 text-xs">{counter.description}</p>
            </div>
          )}
        </div>

        <div className="border-t border-gray-800 pt-3 text-xs text-gray-700 flex gap-4">
          <span>Created: {new Date(counter.created_at).toLocaleDateString()}</span>
          <span>Updated: {new Date(counter.updated_at).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Current Session */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-5">
        <h2 className="text-xs text-gray-600 uppercase tracking-wide mb-3">Current Session</h2>
        {currentSession ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <SessionStatusBadge status={currentSession.status} />
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-xs text-gray-600 mb-0.5">Opened By</p>
                <p className="text-gray-300">{currentSession.opened_by_name}</p>
                <p className="text-xs text-gray-600">{currentSession.opened_by_email}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-0.5">Opened At</p>
                <p className="text-gray-300">
                  {new Date(currentSession.opened_at).toLocaleString()}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-0.5">Opening Cash</p>
                <p className="text-gray-300 font-medium font-mono">
                  {formatCurrency(currentSession.opening_cash)}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-0.5">Expected Cash</p>
                <p className="text-gray-300 font-medium font-mono">
                  {formatCurrency(currentSession.expected_cash)}
                </p>
              </div>
            </div>
            <div className="pt-1">
              <Link
                to={`/counter-sessions?counter=${counter.id}`}
                className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
              >
                View all sessions →
              </Link>
            </div>
          </div>
        ) : (
          <p className="text-gray-600 text-sm">
            No active session.{' '}
            {counter.status === 'ACTIVE' && canOpenSession && (
              <button
                onClick={() => setShowOpen(true)}
                className="text-brand-400 hover:text-brand-300 transition-colors"
              >
                Open one now →
              </button>
            )}
          </p>
        )}
      </div>

      {/* Active Assignments */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xs text-gray-600 uppercase tracking-wide">Active Assignments</h2>
          {canAssign && (
            <Button variant="ghost" size="sm" onClick={() => setShowAssign(true)}>
              + Assign
            </Button>
          )}
        </div>

        {activeAssignments.length === 0 ? (
          <p className="text-gray-600 text-sm">No active assignments.</p>
        ) : (
          <ul className="space-y-2">
            {activeAssignments.map((a) => (
              <li key={a.id} className="flex items-center justify-between text-sm">
                <div>
                  <span className="text-gray-300">{a.user_name}</span>
                  <span className="text-gray-600 text-xs ml-2">{a.user_email}</span>
                </div>
                {canAssign && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={async () => {
                      await deactivateAssignment.mutateAsync(a.id)
                      toast('Assignment removed.', 'warning')
                    }}
                  >
                    Remove
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Edit modal */}
      <Modal open={showEdit} onClose={() => setShowEdit(false)} title="Edit Counter" size="lg">
        <CounterForm
          initial={counter}
          onSubmit={handleEdit}
          onCancel={() => setShowEdit(false)}
          submitLabel="Save Changes"
          loading={updateCounter.isPending}
        />
      </Modal>

      {/* Open session modal */}
      <Modal open={showOpen} onClose={() => setShowOpen(false)} title="Open Counter" size="md">
        <OpenSessionForm
          counter={counter}
          shifts={shifts}
          onSubmit={handleOpenSession}
          onCancel={() => setShowOpen(false)}
          loading={openSession.isPending}
        />
      </Modal>

      {/* Close session modal */}
      {sessionForClose && closeSessionId && (
        <Modal
          open={!!closeSessionId}
          onClose={() => setCloseSessionId(null)}
          title="Close Counter"
          size="md"
        >
          <CloseSessionForm
            session={sessionForClose}
            onSubmit={handleCloseSession}
            onCancel={() => setCloseSessionId(null)}
            loading={closeSession.isPending}
          />
        </Modal>
      )}

      {/* Force close modal */}
      {sessionForClose && forceCloseSessionId && (
        <Modal
          open={!!forceCloseSessionId}
          onClose={() => setForceCloseSessionId(null)}
          title="Force Close Session"
          size="md"
        >
          <ForceCloseForm
            session={sessionForClose}
            onSubmit={handleForceClose}
            onCancel={() => setForceCloseSessionId(null)}
            loading={forceCloseSession.isPending}
          />
        </Modal>
      )}

      {/* Assign cashier modal */}
      <Modal open={showAssign} onClose={() => setShowAssign(false)} title="Assign Cashier" size="md">
        <AssignCounterForm
          counter={counter}
          onSubmit={handleAssign}
          onCancel={() => setShowAssign(false)}
          loading={createAssignment.isPending}
        />
      </Modal>

      {/* Disable confirm */}
      <ConfirmDialog
        open={confirmDisable}
        onClose={() => setConfirmDisable(false)}
        onConfirm={async () => {
          await disableCounter.mutateAsync(counter.id)
          setConfirmDisable(false)
          toast(`"${counter.name}" disabled.`, 'warning')
        }}
        title={`Disable "${counter.name}"?`}
        message="Counter will be inactive. Any open session should be closed first."
        confirmLabel="Disable"
        confirmVariant="danger"
        loading={disableCounter.isPending}
      />

      {/* Reactivate confirm */}
      <ConfirmDialog
        open={confirmReactivate}
        onClose={() => setConfirmReactivate(false)}
        onConfirm={async () => {
          await reactivateCounter.mutateAsync(counter.id)
          setConfirmReactivate(false)
          toast(`"${counter.name}" reactivated.`, 'success')
        }}
        title={`Reactivate "${counter.name}"?`}
        message="Counter will be set to Active and can accept new sessions."
        confirmLabel="Reactivate"
        confirmVariant="success"
        loading={reactivateCounter.isPending}
      />
    </div>
  )
}
