// =============================================================================
// RestaurantFlow — Badge
// =============================================================================

import { cn } from '@/utils/cn'

type BadgeVariant = 'active' | 'inactive' | 'default' | 'warning' | 'info'

interface BadgeProps {
  variant?: BadgeVariant
  children: React.ReactNode
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  active: 'bg-green-500/10 text-green-400 border-green-500/30',
  inactive: 'bg-red-500/10 text-red-400 border-red-500/30',
  default: 'bg-gray-700/60 text-gray-300 border-gray-600/60',
  warning: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  info: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
}

export function Badge({ variant = 'default', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium',
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}

export function ActiveBadge({ is_active }: { is_active: boolean }) {
  return (
    <Badge variant={is_active ? 'active' : 'inactive'}>
      <span
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          is_active ? 'bg-green-400' : 'bg-red-400',
        )}
      />
      {is_active ? 'Active' : 'Disabled'}
    </Badge>
  )
}
