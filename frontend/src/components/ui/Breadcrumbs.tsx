// =============================================================================
// RestaurantFlow — Breadcrumbs
// =============================================================================

import { Link } from 'react-router-dom'
import { cn } from '@/utils/cn'

export interface Crumb {
  label: string
  to?: string
}

interface BreadcrumbsProps {
  crumbs: Crumb[]
  className?: string
}

export function Breadcrumbs({ crumbs, className }: BreadcrumbsProps) {
  return (
    <nav
      aria-label="Breadcrumb"
      className={cn('flex items-center gap-1 text-xs text-gray-600', className)}
    >
      {crumbs.map((crumb, i) => {
        const isLast = i === crumbs.length - 1
        return (
          <span key={i} className="flex items-center gap-1">
            {i > 0 && (
              <svg
                className="h-3 w-3 text-gray-700 flex-shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
            )}
            {isLast || !crumb.to ? (
              <span className={cn(isLast ? 'text-gray-300' : 'text-gray-600')}>
                {crumb.label}
              </span>
            ) : (
              <Link
                to={crumb.to}
                className="text-gray-500 hover:text-gray-300 transition-colors"
              >
                {crumb.label}
              </Link>
            )}
          </span>
        )
      })}
    </nav>
  )
}
