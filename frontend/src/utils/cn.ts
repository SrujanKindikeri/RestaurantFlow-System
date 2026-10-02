// =============================================================================
// RestaurantFlow — Class Name Utility
// Simple utility for conditionally joining Tailwind class names.
// =============================================================================

/**
 * Joins class names, filtering out falsy values.
 *
 * Usage:
 *   cn('base-class', isActive && 'active-class', undefined)
 *   // → 'base-class active-class'
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ')
}
