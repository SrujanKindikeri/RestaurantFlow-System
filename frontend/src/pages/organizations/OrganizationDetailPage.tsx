// =============================================================================
// RestaurantFlow — Organization Detail Page
// =============================================================================

import { useState } from 'react'
import { useParams } from 'react-router-dom'
import type { Restaurant, RestaurantCreatePayload } from '@/types'
import {
  useOrganization,
  useUpdateOrganization,
  useDisableOrganization,
  useReactivateOrganization,
} from '@/hooks/useOrganizations'
import { useCreateRestaurant, useDisableRestaurant, useReactivateRestaurant } from '@/hooks/useRestaurants'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { ActiveBadge, Badge } from '@/components/ui/Badge'
import { StatCard } from '@/components/ui/StatCard'
import { EmptyState } from '@/components/ui/EmptyState'
import { OrganizationForm } from '@/components/organization/OrganizationForm'
import { RestaurantCard } from '@/components/restaurant/RestaurantCard'
import { RestaurantForm } from '@/components/restaurant/RestaurantForm'
import { useToast } from '@/components/ui/Toast'

export function OrganizationDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { data: org, isLoading, isError } = useOrganization(id ?? '')
  const updateOrg = useUpdateOrganization(id ?? '')
  const disableOrg = useDisableOrganization()
  const reactivateOrg = useReactivateOrganization()
  const createRestaurant = useCreateRestaurant(id ?? '')
  const disableRestaurant = useDisableRestaurant()
  const reactivateRestaurant = useReactivateRestaurant()
  const { toast } = useToast()

  const [showEdit, setShowEdit] = useState(false)
  const [showAddRestaurant, setShowAddRestaurant] = useState(false)
  const [confirmOrg, setConfirmOrg] = useState<'disable' | 'reactivate' | null>(null)
  const [confirmRestaurant, setConfirmRestaurant] = useState<{ r: Restaurant; action: 'disable' | 'reactivate' } | null>(null)

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="space-y-4">
          <div className="h-8 w-56 bg-gray-800 rounded animate-pulse" />
          <div className="h-32 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
        </div>
      </div>
    )
  }

  if (isError || !org) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Organization not found or could not be loaded.
        </div>
      </div>
    )
  }

  async function handleEdit(payload: Parameters<typeof updateOrg.mutateAsync>[0]) {
    try {
      await updateOrg.mutateAsync(payload)
      setShowEdit(false)
      toast('Organization updated.', 'success')
    } catch {
      toast('Failed to update organization.', 'error')
    }
  }

  async function handleOrgConfirm() {
    if (!confirmOrg) return
    try {
      if (confirmOrg === 'disable') {
        await disableOrg.mutateAsync(org!.id)
        toast(`"${org!.name}" disabled.`, 'warning')
      } else {
        await reactivateOrg.mutateAsync(org!.id)
        toast(`"${org!.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmOrg(null)
    }
  }

  async function handleAddRestaurant(payload: RestaurantCreatePayload) {
    try {
      await createRestaurant.mutateAsync(payload)
      setShowAddRestaurant(false)
      toast('Restaurant created.', 'success')
    } catch {
      toast('Failed to create restaurant.', 'error')
    }
  }

  async function handleRestaurantConfirm() {
    if (!confirmRestaurant) return
    const { r, action } = confirmRestaurant
    try {
      if (action === 'disable') {
        await disableRestaurant.mutateAsync(r.id)
        toast(`"${r.name}" disabled.`, 'warning')
      } else {
        await reactivateRestaurant.mutateAsync(r.id)
        toast(`"${r.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmRestaurant(null)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title={org.name}
        crumbs={[
          { label: 'Home', to: '/' },
          { label: 'Organizations', to: '/organizations' },
          { label: org.name },
        ]}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => setShowEdit(true)}>
              Edit
            </Button>
            {org.is_active ? (
              <Button variant="danger" size="sm" onClick={() => setConfirmOrg('disable')}>
                Disable
              </Button>
            ) : (
              <Button variant="success" size="sm" onClick={() => setConfirmOrg('reactivate')}>
                Reactivate
              </Button>
            )}
          </div>
        }
      />

      {/* Summary */}
      <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-5 mb-8">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <ActiveBadge is_active={org.is_active} />
              <Badge variant="info">{org.currency}</Badge>
              <Badge variant="default">{org.timezone}</Badge>
            </div>
            {org.legal_name && (
              <p className="text-sm text-gray-400">{org.legal_name}</p>
            )}
            {org.tax_id && (
              <p className="text-xs text-gray-600 mt-0.5">Tax ID: {org.tax_id}</p>
            )}
          </div>
          <div className="text-sm text-gray-500 space-y-1 text-right">
            {org.email && <p>✉ {org.email}</p>}
            {org.phone && <p>📞 {org.phone}</p>}
            {org.city && (
              <p>
                📍 {[org.city, org.state, org.country].filter(Boolean).join(', ')}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
        <StatCard label="Restaurants" value={org.restaurant_count} color="default" />
        <StatCard label="Active" value={org.active_restaurant_count} color="green" />
        <StatCard
          label="Branches"
          value={org.restaurants?.reduce((s, r) => s + (r.branch_count ?? 0), 0) ?? '—'}
          color="blue"
        />
        <StatCard
          label="Active Branches"
          value={org.restaurants?.reduce((s, r) => s + (r.active_branch_count ?? 0), 0) ?? '—'}
          color="green"
        />
      </div>

      {/* Restaurants */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">
          Restaurants
        </h2>
        {org.is_active && (
          <Button variant="primary" size="sm" onClick={() => setShowAddRestaurant(true)}>
            + Add Restaurant
          </Button>
        )}
      </div>

      {org.restaurants.length === 0 ? (
        <EmptyState
          title="No restaurants yet"
          description="Add the first restaurant to this organization."
          actionLabel={org.is_active ? 'Add Restaurant' : undefined}
          onAction={org.is_active ? () => setShowAddRestaurant(true) : undefined}
        />
      ) : (
        <div className="space-y-3">
          {org.restaurants.map((r) => (
            <RestaurantCard
              key={r.id}
              restaurant={r}
              onDisable={(restaurant) =>
                setConfirmRestaurant({ r: restaurant, action: 'disable' })
              }
              onReactivate={(restaurant) =>
                setConfirmRestaurant({ r: restaurant, action: 'reactivate' })
              }
            />
          ))}
        </div>
      )}

      {/* Edit org modal */}
      <Modal
        open={showEdit}
        onClose={() => setShowEdit(false)}
        title="Edit Organization"
        size="lg"
      >
        <OrganizationForm
          initial={org}
          onSubmit={handleEdit}
          onCancel={() => setShowEdit(false)}
          submitLabel="Save Changes"
        />
      </Modal>

      {/* Add restaurant modal */}
      <Modal
        open={showAddRestaurant}
        onClose={() => setShowAddRestaurant(false)}
        title="Add Restaurant"
        description={`Adding to: ${org.name}`}
        size="lg"
      >
        <RestaurantForm
          onSubmit={handleAddRestaurant}
          onCancel={() => setShowAddRestaurant(false)}
          submitLabel="Create Restaurant"
        />
      </Modal>

      {/* Confirm org action */}
      <ConfirmDialog
        open={!!confirmOrg}
        onClose={() => setConfirmOrg(null)}
        onConfirm={handleOrgConfirm}
        title={confirmOrg === 'disable' ? `Disable "${org.name}"?` : `Reactivate "${org.name}"?`}
        message={
          confirmOrg === 'disable'
            ? 'Disabling prevents new restaurants from being created. Existing data is preserved.'
            : 'This will reactivate the organization.'
        }
        confirmLabel={confirmOrg === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirmOrg === 'disable' ? 'danger' : 'success'}
        loading={disableOrg.isPending || reactivateOrg.isPending}
      />

      {/* Confirm restaurant action */}
      <ConfirmDialog
        open={!!confirmRestaurant}
        onClose={() => setConfirmRestaurant(null)}
        onConfirm={handleRestaurantConfirm}
        title={
          confirmRestaurant?.action === 'disable'
            ? `Disable "${confirmRestaurant?.r.name}"?`
            : `Reactivate "${confirmRestaurant?.r.name}"?`
        }
        message={
          confirmRestaurant?.action === 'disable'
            ? 'Disabling this restaurant prevents new branches from being created under it.'
            : 'This will reactivate the restaurant.'
        }
        confirmLabel={confirmRestaurant?.action === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirmRestaurant?.action === 'disable' ? 'danger' : 'success'}
        loading={disableRestaurant.isPending || reactivateRestaurant.isPending}
      />
    </div>
  )
}
