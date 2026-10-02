// =============================================================================
// RestaurantFlow — Formatters
// Shared formatting utilities for later phases (currency, dates, etc.)
// =============================================================================

/**
 * Format a number as a currency string.
 * Default locale: en-US, currency: USD.
 * Future phases can extend this to support per-restaurant currency settings.
 */
export function formatCurrency(
  amount: number,
  currency = 'USD',
  locale = 'en-US',
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(amount)
}

/**
 * Format an ISO date string to a human-readable local date.
 */
export function formatDate(isoString: string, locale = 'en-US'): string {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(new Date(isoString))
}

/**
 * Format an ISO date string to a local date + time string.
 */
export function formatDateTime(isoString: string, locale = 'en-US'): string {
  return new Intl.DateTimeFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(isoString))
}
