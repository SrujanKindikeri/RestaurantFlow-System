// =============================================================================
// RestaurantFlow — Roles List Page
// Phase 3
// =============================================================================

import { useState } from 'react'
import { PageHeader } from '@/components/ui/PageHeader'
import { Badge, ActiveBadge } from '@/components/ui/Badge'
import { Modal } from '@/components/ui/Modal'
import { useRoles } from '@/hooks/useRoles'
import type { Role } from '@/types'
import { cn } from '@/utils/cn'

const SCOPE_COLORS: Record<string, string> = {
  organization: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  restaurant: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  branch: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
}

function ScopeBadge({ scope }: { scope: string }) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium',
      SCOPE_COLORS[scope] ?? 'bg-gray-700/60 text-gray-300 border-gray-600/60',
    )}>
      {scope}
    </span>
  )
}

function RoleDetailModal({ role, onClose }: { role: Role; onClose: () => void }) {
  return (
    <Modal open title={role.name} onClose={onClose} size="lg">
      <div className="space-y-5">
        {/* Meta */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-600 mb-0.5">Code</p>
            <p className="font-mono text-gray-300">{role.code}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-0.5">Scope</p>
            <ScopeBadge scope={role.scope} />
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-0.5">System Role</p>
            <p className="text-gray-300">{role.is_system_role ? 'Yes' : 'No'}</p>
          </div>
          <div>
            <p className="text-xs text-gray-600 mb-0.5">Status</p>
            <ActiveBadge is_active={role.is_active} />
          </div>
        </div>

        {role.description && (
          <div>
            <p className="text-xs text-gray-600 mb-1">Description</p>
            <p className="text-sm text-gray-400">{role.description}</p>
          </div>
        )}

        {/* Permissions */}
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Permissions ({role.permission_codes.length})
          </p>
          {role.permission_codes.length === 0 ? (
            <p className="text-sm text-gray-600">No permissions assigned.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5 max-h-48 overflow-y-auto">
              {role.permission_codes.map((code) => (
                <span
                  key={code}
                  className="inline-flex items-center rounded-md bg-gray-800 border border-gray-700 px-2 py-0.5 text-xs font-mono text-gray-400"
                >
                  {code}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}

export function RolesListPage() {
  const { data, isLoading, error } = useRoles()
  const [selected, setSelected] = useState<Role | null>(null)

  return (
    <div className="px-4 sm:px-6 py-8 max-w-6xl mx-auto">
      <PageHeader
        title="Roles"
        description="System roles and their permission sets."
        crumbs={[{ label: 'Dashboard', to: '/' }, { label: 'Roles' }]}
      />

      {isLoading && (
        <p className="text-sm text-gray-600 py-8 text-center">Loading roles…</p>
      )}
      {error && (
        <p className="text-sm text-red-400 py-8 text-center">Failed to load roles.</p>
      )}

      {data && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.results.map((role) => (
            <button
              key={role.id}
              onClick={() => setSelected(role)}
              className={cn(
                'text-left rounded-xl border p-4 transition-all',
                'bg-gray-900 hover:bg-gray-800/80 hover:border-gray-700',
                role.is_active
                  ? 'border-gray-800'
                  : 'border-gray-800/40 opacity-60',
              )}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="min-w-0">
                  <p className="font-medium text-white text-sm truncate">{role.name}</p>
                  <p className="text-xs font-mono text-gray-600 mt-0.5">{role.code}</p>
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <ScopeBadge scope={role.scope} />
                  {role.is_system_role && (
                    <Badge variant="info">System</Badge>
                  )}
                </div>
              </div>

              {role.description && (
                <p className="text-xs text-gray-500 line-clamp-2 mb-3">{role.description}</p>
              )}

              <div className="flex items-center justify-between">
                <span className="text-xs text-gray-600">
                  {role.permission_codes.length} permission{role.permission_codes.length !== 1 ? 's' : ''}
                </span>
                <ActiveBadge is_active={role.is_active} />
              </div>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <RoleDetailModal role={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}
