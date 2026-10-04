// =============================================================================
// RestaurantFlow — Reporting Date Range Utilities
// Phase 14
// =============================================================================

export type DatePreset =
  | 'today'
  | 'yesterday'
  | 'last_7_days'
  | 'last_30_days'
  | 'this_month'
  | 'prev_month'
  | 'custom'

export interface DateRange {
  date_from: string
  date_to: string
  label: string
}

function fmt(d: Date): string {
  return d.toISOString().split('T')[0]
}

export function getDateRange(preset: DatePreset): DateRange {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  switch (preset) {
    case 'today':
      return { date_from: fmt(today), date_to: fmt(today), label: 'Today' }

    case 'yesterday': {
      const y = new Date(today)
      y.setDate(y.getDate() - 1)
      return { date_from: fmt(y), date_to: fmt(y), label: 'Yesterday' }
    }

    case 'last_7_days': {
      const s = new Date(today)
      s.setDate(s.getDate() - 6)
      return { date_from: fmt(s), date_to: fmt(today), label: 'Last 7 Days' }
    }

    case 'last_30_days': {
      const s = new Date(today)
      s.setDate(s.getDate() - 29)
      return { date_from: fmt(s), date_to: fmt(today), label: 'Last 30 Days' }
    }

    case 'this_month': {
      const s = new Date(today.getFullYear(), today.getMonth(), 1)
      return { date_from: fmt(s), date_to: fmt(today), label: 'This Month' }
    }

    case 'prev_month': {
      const e = new Date(today.getFullYear(), today.getMonth(), 0)
      const s = new Date(e.getFullYear(), e.getMonth(), 1)
      return { date_from: fmt(s), date_to: fmt(e), label: 'Previous Month' }
    }

    default:
      return { date_from: fmt(today), date_to: fmt(today), label: 'Custom' }
  }
}

export function formatCurrency(value: string | null | undefined, symbol = '₹'): string {
  if (value == null) return '—'
  const n = parseFloat(value)
  if (isNaN(n)) return '—'
  if (n >= 100_000) return `${symbol}${(n / 100_000).toFixed(1)}L`
  if (n >= 1_000) return `${symbol}${(n / 1_000).toFixed(1)}K`
  return `${symbol}${n.toFixed(2)}`
}

export function formatGrowth(pct: string | null | undefined): {
  label: string
  positive: boolean
} {
  if (pct == null) return { label: '—', positive: true }
  const n = parseFloat(pct)
  if (isNaN(n)) return { label: '—', positive: true }
  const label = `${n >= 0 ? '+' : ''}${n.toFixed(1)}%`
  return { label, positive: n >= 0 }
}

export function formatSeconds(sec: number | null | undefined): string {
  if (sec == null) return '—'
  if (sec < 60) return `${Math.round(sec)}s`
  const m = Math.floor(sec / 60)
  const s = Math.round(sec % 60)
  return `${m}m ${s}s`
}
