// =============================================================================
// RestaurantFlow — Organization Card (list item)
// =============================================================================

import { Link } from 'react-router-dom'
import type { Organization } from '@/types'
import { ActiveBadge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { cn } from '@/utils/cn'

interface OrganizationCardProps {
  org: Organization
  onDisable: (org: Organization) => void
  onReactivate: (org: Organization) => void
}

export function OrganizationCard({
  org,
  onDisable,
  onReactivate,
}: OrganizationCardProps) {
  return (
    <div
      className={cn(
        'group rounded-xl bg-gray-900/60 border px-5 py-4',
        'hover:border-gray-700 transition-colors',
        org.is_active ? 'border-gray-800' : 'border-gray-800/50 opacity-75',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left */}
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-white truncate">{org.name}</h3>
            <ActiveBadge is_active={org.is_active} />
          </div>
          {org.legal_name && (
            <p className="text-xs text-gray-600 mt-0.5">{org.legal_name}</p>
          )}
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500">
            {org.city && (
              <span>
                📍 {org.city}
                {org.country ? `, ${org.country}` : ''}
              </span>
            )}
            {org.currency && <span>💱 {org.currency}</span>}
            {org.email && <span>✉ {org.email}</span>}
          </div>
          <div className="mt-2 flex gap-4 text-xs">
            <span className="text-gray-600">
              <span className="text-gray-300 font-medium">
                {org.restaurant_count}
              </span>{' '}
              restaurant{org.restaurant_count !== 1 ? 's' : ''}
            </span>
            <span className="text-gray-600">
              <span className="text-green-400 font-medium">
                {org.active_restaurant_count}
              </span>{' '}
              active
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <Link to={`/organizations/${org.id}`}>
            <Button variant="ghost" size="sm">
              View
            </Button>
          </Link>
          <Link to={`/organizations/${org.id}/edit`}>
            <Button variant="ghost" size="sm">
              Edit
            </Button>
          </Link>
          {org.is_active ? (
            <Button
              variant="danger"
              size="sm"
              onClick={() => onDisable(org)}
            >
              Disable
            </Button>
          ) : (
            <Button
              variant="success"
              size="sm"
              onClick={() => onReactivate(org)}
            >
              Reactivate
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
