// =============================================================================
// RestaurantFlow — Organizations List Page
// =============================================================================

import { useState } from 'react'
import type { Organization } from '@/types'
import {
  useOrganizations,
  useCreateOrganization,
  useDisableOrganization,
  useReactivateOrganization,
} from '@/hooks/useOrganizations'
import { OrganizationCard } from '@/components/organization/OrganizationCard'
import { OrganizationForm } from '@/components/organization/OrganizationForm'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'

export function OrganizationsListPage() {
  const { data, isLoading, isError } = useOrganizations()
  const createOrg = useCreateOrganization()
  const disableOrg = useDisableOrganization()
  const reactivateOrg = useReactivateOrganization()
  const { toast } = useToast()

  const [showCreate, setShowCreate] = useState(false)
  const [confirmTarget, setConfirmTarget] = useState<Organization | null>(null)
  const [confirmAction, setConfirmAction] = useState<'disable' | 'reactivate'>('disable')

  async function handleCreate(payload: Parameters<typeof createOrg.mutateAsync>[0]) {
    try {
      await createOrg.mutateAsync(payload)
      setShowCreate(false)
      toast('Organization created.', 'success')
    } catch {
      toast('Failed to create organization.', 'error')
    }
  }

  function openDisable(org: Organization) {
    setConfirmTarget(org)
    setConfirmAction('disable')
  }

  function openReactivate(org: Organization) {
    setConfirmTarget(org)
    setConfirmAction('reactivate')
  }

  async function handleConfirm() {
    if (!confirmTarget) return
    try {
      if (confirmAction === 'disable') {
        await disableOrg.mutateAsync(confirmTarget.id)
        toast(`"${confirmTarget.name}" disabled.`, 'warning')
      } else {
        await reactivateOrg.mutateAsync(confirmTarget.id)
        toast(`"${confirmTarget.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed. Please try again.', 'error')
    } finally {
      setConfirmTarget(null)
    }
  }

  const organizations = data?.results ?? []

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Organizations"
        description="Manage the companies and legal entities that operate restaurants."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Organizations' }]}
        actions={
          <Button variant="primary" onClick={() => setShowCreate(true)}>
            + Add Organization
          </Button>
        }
      />

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-24 rounded-xl bg-gray-900/60 border border-gray-800 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Error */}
      {isError && (
        <div
          className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400"
          role="alert"
        >
          Failed to load organizations. Make sure the backend is running.
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && organizations.length === 0 && (
        <EmptyState
          title="No organizations yet"
          description="Create your first organization to get started."
          actionLabel="Add Organization"
          onAction={() => setShowCreate(true)}
        />
      )}

      {/* List */}
      {!isLoading && !isError && organizations.length > 0 && (
        <div className="space-y-3">
          {organizations.map((org) => (
            <OrganizationCard
              key={org.id}
              org={org}
              onDisable={openDisable}
              onReactivate={openReactivate}
            />
          ))}
          <p className="text-xs text-gray-700 text-right pt-1">
            {data?.count} organization{data?.count !== 1 ? 's' : ''} total
          </p>
        </div>
      )}

      {/* Create modal */}
      <Modal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        title="New Organization"
        description="Create a new company or legal entity."
        size="lg"
      >
        <OrganizationForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          submitLabel="Create Organization"
        />
      </Modal>

      {/* Confirm disable / reactivate */}
      <ConfirmDialog
        open={!!confirmTarget}
        onClose={() => setConfirmTarget(null)}
        onConfirm={handleConfirm}
        title={
          confirmAction === 'disable'
            ? `Disable "${confirmTarget?.name}"?`
            : `Reactivate "${confirmTarget?.name}"?`
        }
        message={
          confirmAction === 'disable'
            ? 'Disabling this organization will prevent new restaurants from being created under it. Existing data is preserved.'
            : 'This will reactivate the organization and allow new restaurants to be added.'
        }
        confirmLabel={confirmAction === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirmAction === 'disable' ? 'danger' : 'success'}
        loading={disableOrg.isPending || reactivateOrg.isPending}
      />
    </div>
  )
}
