// =============================================================================
// RestaurantFlow — User Detail Page
// Phase 3
// =============================================================================

import { useParams, useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { ActiveBadge } from '@/components/ui/Badge'
import { useUser, useDisableUser, useReactivateUser, useDisableRoleAssignment } from '@/hooks/useUsers'
import { useAuth } from '@/contexts/AuthContext'
import { useToast } from '@/components/ui/Toast'
import { ConfirmDialog } from '@/components/ui/Modal'
import { RoleAssignmentModal } from '@/components/users/RoleAssignmentModal'
import { useState } from 'react'
import type { UserRoleAssignment } from '@/types'
import { cn } from '@/utils/cn'

const SCOPE_BADGE: Record<string, string> = {
  organization: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  restaurant: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  branch: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">{children}</h2>
  )
}

function Field({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <dt className="text-xs text-gray-600 mb-0.5">{label}</dt>
      <dd className="text-sm text-gray-200">{value || <span className="text-gray-600">—</span>}</dd>
    </div>
  )
}

export function UserDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { hasPermission, user: currentUser } = useAuth()
  const { toast } = useToast()
  const userId = id ? parseInt(id, 10) : undefined

  const { data: user, isLoading, error } = useUser(userId)
  const disableMutation = useDisableUser()
  const reactivateMutation = useReactivateUser()
  const disableAssignment = useDisableRoleAssignment(userId ?? 0)

  const [showDisableConfirm, setShowDisableConfirm] = useState(false)
  const [assignmentToRemove, setAssignmentToRemove] = useState<UserRoleAssignment | null>(null)
  const [showRoleModal, setShowRoleModal] = useState(false)

  const canDisable = hasPermission('user.disable')
  const canManageRoles = hasPermission('role.manage')
  const isSelf = currentUser?.id === userId

  async function handleToggleStatus() {
    if (!user) return
    try {
      if (user.is_active) {
        await disableMutation.mutateAsync(user.id)
        toast(`${user.full_name} has been disabled.`, 'success')
      } else {
        await reactivateMutation.mutateAsync(user.id)
        toast(`${user.full_name} has been reactivated.`, 'success')
      }
      setShowDisableConfirm(false)
    } catch {
      toast('Action failed.', 'error')
    }
  }

  async function handleRemoveAssignment() {
    if (!assignmentToRemove) return
    try {
      await disableAssignment.mutateAsync(assignmentToRemove.id)
      toast('Role assignment removed.', 'success')
      setAssignmentToRemove(null)
    } catch {
      toast('Failed to remove assignment.', 'error')
    }
  }

  if (isLoading) {
    return (
      <div className="px-4 sm:px-6 py-8 max-w-5xl mx-auto flex items-center justify-center min-h-48">
        <p className="text-gray-600 text-sm">Loading user…</p>
      </div>
    )
  }

  if (error || !user) {
    return (
      <div className="px-4 sm:px-6 py-8 max-w-5xl mx-auto">
        <p className="text-red-400 text-sm">User not found or you do not have access.</p>
        <Button variant="ghost" size="sm" className="mt-4" onClick={() => navigate('/users')}>
          ← Back to Users
        </Button>
      </div>
    )
  }

  const activeAssignments = user.role_assignments?.filter((a) => a.is_active) ?? []

  return (
    <div className="px-4 sm:px-6 py-8 max-w-5xl mx-auto">
      <PageHeader
        title={user.full_name}
        description={user.email}
        crumbs={[
          { label: 'Dashboard', to: '/' },
          { label: 'Users', to: '/users' },
          { label: user.full_name },
        ]}
        actions={
          <div className="flex items-center gap-2">
            {canManageRoles && (
              <Button variant="secondary" size="sm" onClick={() => setShowRoleModal(true)}>
                Assign Role
              </Button>
            )}
            {canDisable && !isSelf && (
              <Button
                variant={user.is_active ? 'danger' : 'success'}
                size="sm"
                onClick={() => setShowDisableConfirm(true)}
              >
                {user.is_active ? 'Disable' : 'Reactivate'}
              </Button>
            )}
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* ---- Left column: Identity ---- */}
        <div className="lg:col-span-1 space-y-6">

          {/* Avatar + status */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-14 h-14 rounded-full bg-gray-700 flex items-center justify-center text-xl font-semibold text-gray-200 flex-shrink-0">
                {(user.first_name?.[0] ?? user.email[0]).toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="font-semibold text-white truncate">{user.full_name}</p>
                <ActiveBadge is_active={user.is_active} />
              </div>
            </div>

            <dl className="space-y-3">
              <Field label="Email" value={user.email} />
              <Field label="Phone" value={user.phone} />
              <Field label="Employee Code" value={user.profile?.employee_code} />
              <Field label="Display Name" value={user.profile?.display_name} />
              <Field label="Member Since" value={new Date(user.date_joined).toLocaleDateString()} />
              {user.last_login && (
                <Field label="Last Login" value={new Date(user.last_login).toLocaleString()} />
              )}
            </dl>
          </div>
        </div>

        {/* ---- Right column: Roles + Permissions ---- */}
        <div className="lg:col-span-2 space-y-6">

          {/* Role Assignments */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
              <SectionTitle>Role Assignments</SectionTitle>
              {canManageRoles && (
                <Button variant="ghost" size="sm" onClick={() => setShowRoleModal(true)}>
                  + Add
                </Button>
              )}
            </div>

            {activeAssignments.length === 0 ? (
              <p className="text-sm text-gray-600">No active role assignments.</p>
            ) : (
              <div className="space-y-2">
                {activeAssignments.map((a) => (
                  <div
                    key={a.id}
                    className="flex items-start justify-between gap-3 p-3 rounded-lg bg-gray-800/50 border border-gray-700/50"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-medium text-sm text-white">{a.role_detail.name}</span>
                        <span className={cn(
                          'inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium',
                          SCOPE_BADGE[a.role_detail.scope] ?? 'bg-gray-700/60 text-gray-300 border-gray-600/60'
                        )}>
                          {a.role_detail.scope}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 space-y-0.5">
                        {a.organization_name && <p>Org: {a.organization_name}</p>}
                        {a.restaurant_name && <p>Restaurant: {a.restaurant_name}</p>}
                        {a.branch_name && <p>Branch: {a.branch_name}</p>}
                      </div>
                    </div>
                    {canManageRoles && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-400 hover:text-red-300 flex-shrink-0"
                        onClick={() => setAssignmentToRemove(a)}
                      >
                        Remove
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Permissions */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <SectionTitle>Effective Permissions</SectionTitle>
            {user.permissions.length === 0 ? (
              <p className="text-sm text-gray-600">No permissions assigned.</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {user.permissions.map((p) => (
                  <span
                    key={p}
                    className="inline-flex items-center rounded-md bg-gray-800 border border-gray-700 px-2 py-0.5 text-xs font-mono text-gray-400"
                  >
                    {p}
                  </span>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>

      {/* Confirm disable/reactivate */}
      <ConfirmDialog
        open={showDisableConfirm}
        onClose={() => setShowDisableConfirm(false)}
        onConfirm={handleToggleStatus}
        title={user.is_active ? 'Disable User' : 'Reactivate User'}
        message={
          user.is_active
            ? `Disable ${user.full_name}? They will lose access immediately.`
            : `Reactivate ${user.full_name}?`
        }
        confirmLabel={user.is_active ? 'Disable' : 'Reactivate'}
        confirmVariant={user.is_active ? 'danger' : 'success'}
        loading={disableMutation.isPending || reactivateMutation.isPending}
      />

      {/* Confirm remove assignment */}
      <ConfirmDialog
        open={!!assignmentToRemove}
        onClose={() => setAssignmentToRemove(null)}
        onConfirm={handleRemoveAssignment}
        title="Remove Role Assignment"
        message={`Remove the ${assignmentToRemove?.role_detail.name} role from this user?`}
        confirmLabel="Remove"
        confirmVariant="danger"
        loading={disableAssignment.isPending}
      />

      {/* Role assignment modal */}
      {showRoleModal && userId && (
        <RoleAssignmentModal
          userId={userId}
          open={showRoleModal}
          onClose={() => setShowRoleModal(false)}
        />
      )}
    </div>
  )
}
