// =============================================================================
// RestaurantFlow — Money Formatting Utilities
// Phase 4
// =============================================================================

/**
 * Format a decimal string as INR currency.
 * e.g. "5000.00" → "₹5,000.00"
 */
export function formatCurrency(value: string | null | undefined, currency = 'INR'): string {
  if (value == null || value === '') return '—'
  const num = parseFloat(value)
  if (isNaN(num)) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(num)
}

/**
 * Format cash difference with sign and colour class.
 * Returns { label, colorClass }
 */
export function formatDifference(diff: string | null | undefined): {
  label: string
  colorClass: string
} {
  if (diff == null || diff === '') return { label: '—', colorClass: 'text-gray-500' }
  const num = parseFloat(diff)
  if (isNaN(num)) return { label: '—', colorClass: 'text-gray-500' }
  if (num > 0) return { label: `+${formatCurrency(diff)}`, colorClass: 'text-green-400' }
  if (num < 0) return { label: formatCurrency(diff), colorClass: 'text-red-400' }
  return { label: formatCurrency(diff), colorClass: 'text-gray-400' }
}

/**
 * Validate that a string is a valid non-negative decimal number.
 */
export function isValidCash(value: string): boolean {
  if (!value || value.trim() === '') return false
  const num = parseFloat(value)
  return !isNaN(num) && num >= 0
}
