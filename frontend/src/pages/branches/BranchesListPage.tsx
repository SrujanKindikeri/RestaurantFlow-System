// =============================================================================
// RestaurantFlow — Branches List Page (all branches, admin view)
// =============================================================================

import { useState } from 'react'
import type { Branch } from '@/types'
import {
  useAllBranches,
  useDisableBranch,
  useReactivateBranch,
} from '@/hooks/useBranches'
import { BranchCard } from '@/components/branch/BranchCard'
import { PageHeader } from '@/components/ui/PageHeader'
import { ConfirmDialog } from '@/components/ui/Modal'
import { EmptyState } from '@/components/ui/EmptyState'
import { useToast } from '@/components/ui/Toast'

export function BranchesListPage() {
  const { data, isLoading, isError } = useAllBranches()
  const disableBranch = useDisableBranch()
  const reactivateBranch = useReactivateBranch()
  const { toast } = useToast()

  const [confirm, setConfirm] = useState<{
    b: Branch
    action: 'disable' | 'reactivate'
  } | null>(null)

  async function handleConfirm() {
    if (!confirm) return
    const { b, action } = confirm
    try {
      if (action === 'disable') {
        await disableBranch.mutateAsync(b.id)
        toast(`"${b.name}" disabled.`, 'warning')
      } else {
        await reactivateBranch.mutateAsync(b.id)
        toast(`"${b.name}" reactivated.`, 'success')
      }
    } catch {
      toast('Action failed. Please try again.', 'error')
    } finally {
      setConfirm(null)
    }
  }

  const branches = data?.results ?? []

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Branches"
        description="All physical locations across all restaurants."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Branches' }]}
      />

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-20 rounded-xl bg-gray-900/60 border border-gray-800 animate-pulse"
            />
          ))}
        </div>
      )}

      {isError && (
        <div
          className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400"
          role="alert"
        >
          Failed to load branches.
        </div>
      )}

      {!isLoading && !isError && branches.length === 0 && (
        <EmptyState
          title="No branches yet"
          description="Add branches from a restaurant's detail page."
        />
      )}

      {!isLoading && !isError && branches.length > 0 && (
        <div className="space-y-3">
          {branches.map((b) => (
            <BranchCard
              key={b.id}
              branch={b}
              onDisable={(branch) => setConfirm({ b: branch, action: 'disable' })}
              onReactivate={(branch) => setConfirm({ b: branch, action: 'reactivate' })}
            />
          ))}
          <p className="text-xs text-gray-700 text-right pt-1">
            {data?.count} branch{data?.count !== 1 ? 'es' : ''} total
          </p>
        </div>
      )}

      <ConfirmDialog
        open={!!confirm}
        onClose={() => setConfirm(null)}
        onConfirm={handleConfirm}
        title={
          confirm?.action === 'disable'
            ? `Disable "${confirm?.b.name}"?`
            : `Reactivate "${confirm?.b.name}"?`
        }
        message={
          confirm?.action === 'disable'
            ? 'This branch will be marked as inactive.'
            : 'This will reactivate the branch.'
        }
        confirmLabel={confirm?.action === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirm?.action === 'disable' ? 'danger' : 'success'}
        loading={disableBranch.isPending || reactivateBranch.isPending}
      />
    </div>
  )
}
