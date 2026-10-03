// =============================================================================
// RestaurantFlow — Kitchen Order Age Timer
// Phase 7
//
// Calculates age from the server-side received_at timestamp.
// Updates every second client-side (no DB polling).
// Shows warning colors when order has been waiting too long.
// =============================================================================

import { useEffect, useState } from 'react'
import { cn } from '@/utils/cn'

interface Props {
  receivedAt: string   // ISO timestamp from backend
  className?: string
}

function formatAge(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  if (m < 60) return `${m}:${String(s).padStart(2, '0')}`
  const h = Math.floor(m / 60)
  const mm = m % 60
  return `${h}h ${mm}m`
}

function ageColorClass(seconds: number): string {
  if (seconds > 1200) return 'text-red-400'   // > 20 min: red
  if (seconds > 600)  return 'text-orange-400' // > 10 min: orange
  if (seconds > 300)  return 'text-yellow-400' // > 5 min: yellow
  return 'text-gray-400'
}

export function KitchenOrderTimer({ receivedAt, className }: Props) {
  const received = new Date(receivedAt).getTime()

  const [age, setAge] = useState<number>(() =>
    Math.max(0, Math.floor((Date.now() - received) / 1000))
  )

  useEffect(() => {
    const interval = setInterval(() => {
      setAge(Math.max(0, Math.floor((Date.now() - received) / 1000)))
    }, 1000)
    return () => clearInterval(interval)
  }, [received])

  return (
    <span className={cn('font-mono text-sm tabular-nums', ageColorClass(age), className)}>
      {formatAge(age)}
    </span>
  )
}
