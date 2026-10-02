// =============================================================================
// RestaurantFlow — Branch Detail Page
// =============================================================================

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  useBranch,
  useUpdateBranch,
  useDisableBranch,
  useReactivateBranch,
} from '@/hooks/useBranches'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { ActiveBadge, Badge } from '@/components/ui/Badge'
import { BranchForm } from '@/components/branch/BranchForm'
import { useToast } from '@/components/ui/Toast'

export function BranchDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: branch, isLoading, isError } = useBranch(id ?? '')
  const updateBranch = useUpdateBranch(id ?? '')
  const disableBranch = useDisableBranch()
  const reactivateBranch = useReactivateBranch()
  const { toast } = useToast()

  const [showEdit, setShowEdit] = useState(false)
  const [confirmAction, setConfirmAction] = useState<'disable' | 'reactivate' | null>(null)

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="h-32 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
      </div>
    )
  }

  if (isError || !branch) {
    return (
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Branch not found.
        </div>
      </div>
    )
  }

  async function handleEdit(payload: Parameters<typeof updateBranch.mutateAsync>[0]) {
    try {
      await updateBranch.mutateAsync(payload)
      setShowEdit(false)
      toast('Branch updated.', 'success')
    } catch {
      toast('Failed to update branch.', 'error')
    }
  }

  async function handleConfirm() {
    if (!confirmAction) return
    try {
      if (confirmAction === 'disable') {
        await disableBranch.mutateAsync(branch!.id)
        toast(`"${branch!.name}" disabled.`, 'warning')
      } else {
        await reactivateBranch.mutateAsync(branch!.id)
        toast(`"${branch!.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmAction(null)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title={branch.name}
        crumbs={[
          { label: 'Home', to: '/' },
          { label: 'Organizations', to: '/organizations' },
          {
            label: branch.restaurant_name,
            to: `/restaurants/${branch.restaurant}`,
          },
          { label: branch.name },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setShowEdit(true)}>
              Edit
            </Button>
            {branch.is_active ? (
              <Button variant="danger" size="sm" onClick={() => setConfirmAction('disable')}>
                Disable
              </Button>
            ) : (
              <Button variant="success" size="sm" onClick={() => setConfirmAction('reactivate')}>
                Reactivate
              </Button>
            )}
          </div>
        }
      />

      {/* Detail card */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-5 space-y-4">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant="default">{branch.code}</Badge>
          <ActiveBadge is_active={branch.is_active} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          {branch.restaurant_name && (
            <div>
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Restaurant</p>
              <p className="text-gray-300">{branch.restaurant_name}</p>
            </div>
          )}
          {branch.phone && (
            <div>
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Phone</p>
              <p className="text-gray-300">{branch.phone}</p>
            </div>
          )}
          {branch.email && (
            <div>
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Email</p>
              <p className="text-gray-300">{branch.email}</p>
            </div>
          )}
          {branch.city && (
            <div>
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Location</p>
              <p className="text-gray-300">
                {[branch.city, branch.state, branch.country].filter(Boolean).join(', ')}
              </p>
            </div>
          )}
          {branch.address && (
            <div className="sm:col-span-2">
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Address</p>
              <p className="text-gray-300">{branch.address}</p>
            </div>
          )}
          {(branch.latitude || branch.longitude) && (
            <div>
              <p className="text-xs text-gray-600 uppercase tracking-wide mb-0.5">Coordinates</p>
              <p className="text-gray-300 font-mono text-xs">
                {branch.latitude}, {branch.longitude}
              </p>
            </div>
          )}
        </div>

        {/* Settings summary */}
        {branch.settings && (
          <div className="border-t border-gray-800 pt-4">
            <p className="text-xs text-gray-600 uppercase tracking-wide mb-2">Settings</p>
            <div className="flex flex-wrap gap-3 text-xs text-gray-500">
              {branch.settings.opening_time && (
                <span>🕐 Opens {branch.settings.opening_time}</span>
              )}
              {branch.settings.closing_time && (
                <span>🕐 Closes {branch.settings.closing_time}</span>
              )}
              <span className="capitalize">
                🍽 {branch.settings.default_order_type.replace('_', ' ')}
              </span>
            </div>
          </div>
        )}

        <div className="border-t border-gray-800 pt-4 text-xs text-gray-700 flex gap-4">
          <span>Created: {new Date(branch.created_at).toLocaleDateString()}</span>
          <span>Updated: {new Date(branch.updated_at).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Edit modal */}
      <Modal open={showEdit} onClose={() => setShowEdit(false)} title="Edit Branch" size="lg">
        <BranchForm
          initial={branch}
          onSubmit={handleEdit}
          onCancel={() => setShowEdit(false)}
          submitLabel="Save Changes"
        />
      </Modal>

      {/* Confirm */}
      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirm}
        title={confirmAction === 'disable' ? `Disable "${branch.name}"?` : `Reactivate "${branch.name}"?`}
        message={
          confirmAction === 'disable'
            ? 'This branch will be marked as inactive.'
            : 'This will reactivate the branch.'
        }
        confirmLabel={confirmAction === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirmAction === 'disable' ? 'danger' : 'success'}
        loading={disableBranch.isPending || reactivateBranch.isPending}
      />
    </div>
  )
}
