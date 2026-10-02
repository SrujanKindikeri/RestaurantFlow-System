// =============================================================================
// RestaurantFlow — Card Component
// =============================================================================

import { cn } from '@/utils/cn'
import type { ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  title?: string
  description?: string
}

export function Card({ children, className, title, description }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-gray-700/60 bg-gray-900/60 backdrop-blur-sm p-5',
        className,
      )}
    >
      {(title || description) && (
        <div className="mb-4">
          {title && <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">{title}</h2>}
          {description && <p className="text-xs text-gray-500 mt-1">{description}</p>}
        </div>
      )}
      {children}
    </div>
  )
}
