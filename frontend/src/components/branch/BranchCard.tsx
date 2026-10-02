// =============================================================================
// RestaurantFlow — Branch Card (list item)
// =============================================================================

import { Link } from 'react-router-dom'
import type { Branch } from '@/types'
import { ActiveBadge, Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/cn'

interface BranchCardProps {
  branch: Branch
  onDisable: (b: Branch) => void
  onReactivate: (b: Branch) => void
}

export function BranchCard({ branch, onDisable, onReactivate }: BranchCardProps) {
  return (
    <div
      className={cn(
        'group rounded-xl bg-gray-900/60 border px-5 py-4',
        'hover:border-gray-700 transition-colors',
        branch.is_active ? 'border-gray-800' : 'border-gray-800/50 opacity-75',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-white truncate">{branch.name}</h3>
            <Badge variant="default">{branch.code}</Badge>
            <ActiveBadge is_active={branch.is_active} />
          </div>
          {branch.restaurant_name && (
            <p className="text-xs text-gray-600 mt-0.5">{branch.restaurant_name}</p>
          )}
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
            {branch.city && (
              <span>
                📍 {branch.city}
                {branch.state ? `, ${branch.state}` : ''}
              </span>
            )}
            {branch.phone && <span>📞 {branch.phone}</span>}
            {branch.email && <span>✉ {branch.email}</span>}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <Link to={`/branches/${branch.id}`}>
            <Button variant="ghost" size="sm">
              View
            </Button>
          </Link>
          <Link to={`/branches/${branch.id}/edit`}>
            <Button variant="ghost" size="sm">
              Edit
            </Button>
          </Link>
          {branch.is_active ? (
            <Button variant="danger" size="sm" onClick={() => onDisable(branch)}>
              Disable
            </Button>
          ) : (
            <Button
              variant="success"
              size="sm"
              onClick={() => onReactivate(branch)}
            >
              Reactivate
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
