// =============================================================================
// RestaurantFlow — Stat Card
// =============================================================================

import { cn } from '@/utils/cn'

interface StatCardProps {
  label: string
  value: number | string
  sub?: string
  color?: 'default' | 'green' | 'blue' | 'purple' | 'yellow'
  loading?: boolean
}

const colorClasses = {
  default: 'text-white',
  green: 'text-green-400',
  blue: 'text-blue-400',
  purple: 'text-purple-400',
  yellow: 'text-yellow-400',
}

export function StatCard({
  label,
  value,
  sub,
  color = 'default',
  loading = false,
}: StatCardProps) {
  return (
    <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-5 py-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
        {label}
      </p>
      {loading ? (
        <div className="h-7 w-16 rounded bg-gray-800 animate-pulse" />
      ) : (
        <p className={cn('text-2xl font-semibold', colorClasses[color])}>
          {value}
        </p>
      )}
      {sub && (
        <p className="mt-1 text-xs text-gray-600">{sub}</p>
      )}
    </div>
  )
}
