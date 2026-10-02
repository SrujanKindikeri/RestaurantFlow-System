// =============================================================================
// RestaurantFlow — Users List Page
// Phase 3
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { ActiveBadge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { useUsers, useDisableUser, useReactivateUser } from '@/hooks/useUsers'
import { useAuth } from '@/contexts/AuthContext'
import { useToast } from '@/components/ui/Toast'
import { ConfirmDialog } from '@/components/ui/Modal'
import type { User } from '@/types'
import { cn } from '@/utils/cn'

const SCOPE_COLORS: Record<string, string> = {
  COMPANY_HEAD: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  CENTRAL_ADMIN: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30',
  RESTAURANT_OWNER: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  RESTAURANT_MANAGER: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
  CASHIER: 'bg-green-500/10 text-green-400 border-green-500/30',
  WAITER: 'bg-teal-500/10 text-teal-400 border-teal-500/30',
  KITCHEN_STAFF: 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  INVENTORY_STAFF: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  ACCOUNTANT: 'bg-pink-500/10 text-pink-400 border-pink-500/30',
}

function RoleBadge({ code, name }: { code: string; name: string }) {
  const cls = SCOPE_COLORS[code] ?? 'bg-gray-700/60 text-gray-300 border-gray-600/60'
  return (
    <span className={cn('inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium', cls)}>
      {name}
    </span>
  )
}

export function UsersListPage() {
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  const { toast } = useToast()
  const [search, setSearch] = useState('')
  const [confirmUser, setConfirmUser] = useState<User | null>(null)
  const [confirmAction, setConfirmAction] = useState<'disable' | 'reactivate' | null>(null)

  const { data, isLoading, error } = useUsers({ search: search || undefined })
  const disableMutation = useDisableUser()
  const reactivateMutation = useReactivateUser()

  const canCreate = hasPermission('user.create')
  const canDisable = hasPermission('user.disable')

  function openConfirm(user: User, action: 'disable' | 'reactivate') {
    setConfirmUser(user)
    setConfirmAction(action)
  }

  function closeConfirm() {
    setConfirmUser(null)
    setConfirmAction(null)
  }

  async function handleConfirm() {
    if (!confirmUser || !confirmAction) return
    try {
      if (confirmAction === 'disable') {
        await disableMutation.mutateAsync(confirmUser.id)
        toast(`${confirmUser.full_name} has been disabled.`, 'success')
      } else {
        await reactivateMutation.mutateAsync(confirmUser.id)
        toast(`${confirmUser.full_name} has been reactivated.`, 'success')
      }
      closeConfirm()
    } catch {
      toast('Action failed. Please try again.', 'error')
    }
  }

  return (
    <div className="px-4 sm:px-6 py-8 max-w-7xl mx-auto">
      <PageHeader
        title="Users"
        description="Manage users and their role assignments."
        crumbs={[{ label: 'Dashboard', to: '/' }, { label: 'Users' }]}
        actions={
          canCreate ? (
            <Button variant="primary" onClick={() => navigate('/users/new')}>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Add User
            </Button>
          ) : undefined
        }
      />

      {/* Search */}
      <div className="mb-4 max-w-xs">
        <Input
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Table */}
      <div className="rounded-xl border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" role="table" aria-label="Users">
            <thead>
              <tr className="border-b border-gray-800 bg-gray-900/60">
                <th scope="col" className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Name</th>
                <th scope="col" className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide hidden sm:table-cell">Email</th>
                <th scope="col" className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide hidden md:table-cell">Roles</th>
                <th scope="col" className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide hidden lg:table-cell">Employee Code</th>
                <th scope="col" className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Status</th>
                <th scope="col" className="px-4 py-3"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-600 text-sm">
                    Loading users…
                  </td>
                </tr>
              )}
              {error && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-red-400 text-sm">
                    Failed to load users.
                  </td>
                </tr>
              )}
              {!isLoading && !error && data?.results.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-gray-600 text-sm">
                    No users found.
                  </td>
                </tr>
              )}
              {data?.results.map((user) => {
                const roles = user.scope?.roles ?? []
                const employeeCode = user.profile?.employee_code
                return (
                  <tr
                    key={user.id}
                    className="border-b border-gray-800/60 hover:bg-gray-800/30 transition-colors"
                  >
                    {/* Name */}
                    <td className="px-4 py-3">
                      <button
                        onClick={() => navigate(`/users/${user.id}`)}
                        className="flex items-center gap-3 text-left hover:text-brand-400 transition-colors"
                      >
                        <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-xs font-semibold text-gray-300 flex-shrink-0">
                          {(user.first_name?.[0] ?? user.email[0]).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-medium text-gray-100">{user.full_name}</p>
                          <p className="text-xs text-gray-500 sm:hidden">{user.email}</p>
                        </div>
                      </button>
                    </td>
                    {/* Email */}
                    <td className="px-4 py-3 text-gray-400 hidden sm:table-cell">{user.email}</td>
                    {/* Roles */}
                    <td className="px-4 py-3 hidden md:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {roles.length === 0 && (
                          <span className="text-xs text-gray-600">—</span>
                        )}
                        {roles.slice(0, 2).map((r) => (
                          <RoleBadge key={r.assignment_id} code={r.role_code} name={r.role_name} />
                        ))}
                        {roles.length > 2 && (
                          <span className="text-xs text-gray-600">+{roles.length - 2}</span>
                        )}
                      </div>
                    </td>
                    {/* Employee code */}
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs hidden lg:table-cell">
                      {employeeCode || '—'}
                    </td>
                    {/* Status */}
                    <td className="px-4 py-3">
                      <ActiveBadge is_active={user.is_active} />
                    </td>
                    {/* Actions */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2 justify-end">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => navigate(`/users/${user.id}`)}
                        >
                          View
                        </Button>
                        {canDisable && user.is_active && (
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => openConfirm(user, 'disable')}
                          >
                            Disable
                          </Button>
                        )}
                        {canDisable && !user.is_active && (
                          <Button
                            variant="success"
                            size="sm"
                            onClick={() => openConfirm(user, 'reactivate')}
                          >
                            Reactivate
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination info */}
      {data && data.count > 0 && (
        <p className="mt-3 text-xs text-gray-600">
          Showing {data.results.length} of {data.count} users
        </p>
      )}

      {/* Confirm dialog */}
      <ConfirmDialog
        open={!!confirmUser}
        onClose={closeConfirm}
        onConfirm={handleConfirm}
        title={confirmAction === 'disable' ? 'Disable User' : 'Reactivate User'}
        message={
          confirmAction === 'disable'
            ? `Disable ${confirmUser?.full_name}? They will lose access immediately.`
            : `Reactivate ${confirmUser?.full_name}? They will regain access.`
        }
        confirmLabel={confirmAction === 'disable' ? 'Disable' : 'Reactivate'}
        confirmVariant={confirmAction === 'disable' ? 'danger' : 'success'}
        loading={disableMutation.isPending || reactivateMutation.isPending}
      />
    </div>
  )
}
