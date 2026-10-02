// =============================================================================
// RestaurantFlow — Restaurant Detail Page
// =============================================================================

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import type { Branch, BranchCreatePayload } from '@/types'
import {
  useRestaurant,
  useUpdateRestaurant,
  useDisableRestaurant,
  useReactivateRestaurant,
} from '@/hooks/useRestaurants'
import {
  useCreateBranch,
  useDisableBranch,
  useReactivateBranch,
} from '@/hooks/useBranches'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { ActiveBadge, Badge } from '@/components/ui/Badge'
import { StatCard } from '@/components/ui/StatCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { RestaurantForm } from '@/components/restaurant/RestaurantForm'
import { BranchCard } from '@/components/branch/BranchCard'
import { BranchForm } from '@/components/branch/BranchForm'
import { useToast } from '@/components/ui/Toast'

export function RestaurantDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: restaurant, isLoading, isError } = useRestaurant(id ?? '')
  const updateRestaurant = useUpdateRestaurant(id ?? '')
  const disableRestaurant = useDisableRestaurant()
  const reactivateRestaurant = useReactivateRestaurant()
  const createBranch = useCreateBranch(id ?? '')
  const disableBranch = useDisableBranch()
  const reactivateBranch = useReactivateBranch()
  const { toast } = useToast()

  const [showEdit, setShowEdit] = useState(false)
  const [showAddBranch, setShowAddBranch] = useState(false)
  const [confirmRestaurant, setConfirmRestaurant] = useState<'disable' | 'reactivate' | null>(null)
  const [confirmBranch, setConfirmBranch] = useState<{
    b: Branch
    action: 'disable' | 'reactivate'
  } | null>(null)

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="space-y-4">
          <div className="h-8 w-48 bg-gray-800 rounded animate-pulse" />
          <div className="h-28 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
        </div>
      </div>
    )
  }

  if (isError || !restaurant) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Restaurant not found.
        </div>
      </div>
    )
  }

  async function handleEdit(payload: Parameters<typeof updateRestaurant.mutateAsync>[0]) {
    try {
      await updateRestaurant.mutateAsync(payload)
      setShowEdit(false)
      toast('Restaurant updated.', 'success')
    } catch {
      toast('Failed to update restaurant.', 'error')
    }
  }

  async function handleRestaurantConfirm() {
    if (!confirmRestaurant) return
    try {
      if (confirmRestaurant === 'disable') {
        await disableRestaurant.mutateAsync(restaurant!.id)
        toast(`"${restaurant!.name}" disabled.`, 'warning')
      } else {
        await reactivateRestaurant.mutateAsync(restaurant!.id)
        toast(`"${restaurant!.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmRestaurant(null)
    }
  }

  async function handleAddBranch(payload: BranchCreatePayload) {
    try {
      await createBranch.mutateAsync(payload)
      setShowAddBranch(false)
      toast('Branch created.', 'success')
    } catch {
      toast('Failed to create branch.', 'error')
    }
  }

  async function handleBranchConfirm() {
    if (!confirmBranch) return
    const { b, action } = confirmBranch
    try {
      if (action === 'disable') {
        await disableBranch.mutateAsync(b.id)
        toast(`"${b.name}" disabled.`, 'warning')
      } else {
        await reactivateBranch.mutateAsync(b.id)
        toast(`"${b.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmBranch(null)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title={restaurant.name}
        crumbs={[
          { label: 'Home', to: '/' },
          { label: 'Organizations', to: '/organizations' },
          { label: restaurant.organization_name, to: `/organizations/${restaurant.organization}` },
          { label: restaurant.name },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setShowEdit(true)}>
              Edit
            </Button>
            {restaurant.is_active ? (
              <Button variant="danger" size="sm" onClick={() => setConfirmRestaurant('disable')}>
                Disable
              </Button>
            ) : (
              <Button variant="success" size="sm" onClick={() => setConfirmRestaurant('reactivate')}>
                Reactivate
              </Button>
            )}
          </div>
        }
      />

      {/* Summary card */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-5 mb-8">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <Badge variant="info">{restaurant.code}</Badge>
              <ActiveBadge is_active={restaurant.is_active} />
            </div>
            {restaurant.description && (
              <p className="text-sm text-gray-400 mt-1 max-w-xl">{restaurant.description}</p>
            )}
          </div>
          <div className="text-sm text-gray-500 space-y-1 text-right">
            {restaurant.email && <p>✉ {restaurant.email}</p>}
            {restaurant.phone && <p>📞 {restaurant.phone}</p>}
            {restaurant.city && <p>📍 {restaurant.city}</p>}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-3 mb-8">
        <StatCard label="Total Branches" value={restaurant.branch_count} />
        <StatCard label="Active Branches" value={restaurant.active_branch_count} color="green" />
      </div>

      {/* Branches */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Branches
        </h2>
        {restaurant.is_active && (
          <Button variant="primary" size="sm" onClick={() => setShowAddBranch(true)}>
            + Add Branch
          </Button>
        )}
      </div>

      {(restaurant.branches?.length ?? 0) === 0 ? (
        <EmptyState
          title="No branches yet"
          description="Add the first branch to this restaurant."
          actionLabel={restaurant.is_active ? 'Add Branch' : undefined}
          onAction={restaurant.is_active ? () => setShowAddBranch(true) : undefined}
        />
      ) : (
        <div className="space-y-3">
          {restaurant.branches?.map((b) => (
            <BranchCard
              key={b.id}
              branch={b}
              onDisable={(branch) => setConfirmBranch({ b: branch, action: 'disable' })}
              onReactivate={(branch) => setConfirmBranch({ b: branch, action: 'reactivate' })}
            />
          ))}
        </div>
      )}

      {/* Edit restaurant */}
      <Modal open={showEdit} onClose={() => setShowEdit(false)} title="Edit Restaurant" size="lg">
        <RestaurantForm
          initial={restaurant}
          onSubmit={handleEdit}
          onCancel={() => setShowEdit(false)}
          submitLabel="Save Changes"
        />
      </Modal>

      {/* Add branch */}
      <Modal
        open={showAddBranch}
        onClose={() => setShowAddBranch(false)}
        title="Add Branch"
        description={`Adding to: ${restaurant.name}`}
        size="lg"
      >
        <BranchForm
          onSubmit={handleAddBranch}
          onCancel={() => setShowAddBranch(false)}
          submitLabel="Create Branch"
        />
      </Modal>

      {/* Confirm restaurant */}
      <ConfirmDialog
        open={!!confirmRestaurant}
        onClose={() => setConfirmRestaurant(null)}
        onConfirm={handleRestaurantConfirm}
        title={confirmRestaurant === 'disable' ? `Disable "${restaurant.name}"?` : `Reactivate "${restaurant.name}"?`}
        message={
          confirmRestaurant === 'disable'
            ? 'Disabling prevents new branches from being created.'
            : 'This will reactivate the restaurant.'
        }
        confirmLabel={confirmRestaurant === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirmRestaurant === 'disable' ? 'danger' : 'success'}
        loading={disableRestaurant.isPending || reactivateRestaurant.isPending}
      />

      {/* Confirm branch */}
      <ConfirmDialog
        open={!!confirmBranch}
        onClose={() => setConfirmBranch(null)}
        onConfirm={handleBranchConfirm}
        title={
          confirmBranch?.action === 'disable'
            ? `Disable "${confirmBranch?.b.name}"?`
            : `Reactivate "${confirmBranch?.b.name}"?`
        }
        message={
          confirmBranch?.action === 'disable'
            ? 'This branch will be marked as inactive.'
            : 'This will reactivate the branch.'
        }
        confirmLabel={confirmBranch?.action === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirmBranch?.action === 'disable' ? 'danger' : 'success'}
        loading={disableBranch.isPending || reactivateBranch.isPending}
      />
    </div>
  )
}
