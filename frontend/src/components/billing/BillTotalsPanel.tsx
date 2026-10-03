// =============================================================================
// RestaurantFlow — Bill Totals Panel
// Phase 8
//
// Displays the financial summary section of a bill:
//   Subtotal / Discount / Tax breakdown / Rounding / Grand Total
// =============================================================================

import type { Bill, BillCalculation } from '@/types'

type Totals = Pick<
  Bill,
  'subtotal' | 'discount_amount' | 'discount_type' | 'discount_value' |
  'taxable_amount' | 'tax_amount' | 'tax_breakdown' | 'rounding_amount' | 'grand_total'
> | BillCalculation & { discount_type?: Bill['discount_type']; discount_value?: string }

interface Props {
  totals: Totals
  currency?: string
}

function fmt(v: string, currency = '₹') {
  const n = parseFloat(v)
  if (isNaN(n)) return `${currency}0.00`
  return `${currency}${Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function BillTotalsPanel({ totals, currency = '₹' }: Props) {
  const hasDiscount = parseFloat(totals.discount_amount) > 0
  const hasRounding = parseFloat(totals.rounding_amount) !== 0
  const taxBreakdown = totals.tax_breakdown ?? {}
  const taxEntries = Object.entries(taxBreakdown).filter(([, v]) => parseFloat(v) > 0)

  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 overflow-hidden">
      <div className="px-4 py-3 space-y-2 text-sm">

        {/* Subtotal */}
        <div className="flex justify-between text-gray-300">
          <span>Subtotal</span>
          <span className="font-mono">{fmt(totals.subtotal, currency)}</span>
        </div>

        {/* Discount */}
        {hasDiscount && (
          <div className="flex justify-between text-amber-400">
            <span>
              Discount
              {'discount_type' in totals && totals.discount_type && (
                <span className="ml-1 text-gray-500 text-xs">
                  ({totals.discount_type === 'PERCENTAGE'
                    ? `${totals.discount_value}%`
                    : `Fixed ${fmt(totals.discount_value ?? '0', currency)}`})
                </span>
              )}
            </span>
            <span className="font-mono">−{fmt(totals.discount_amount, currency)}</span>
          </div>
        )}

        {/* Taxable amount (show only if discount was applied) */}
        {hasDiscount && (
          <div className="flex justify-between text-gray-400 text-xs border-t border-gray-800 pt-1">
            <span>Taxable amount</span>
            <span className="font-mono">{fmt(totals.taxable_amount, currency)}</span>
          </div>
        )}

        {/* Tax breakdown */}
        {taxEntries.length > 0 ? (
          taxEntries.map(([code, amount]) => (
            <div key={code} className="flex justify-between text-gray-400">
              <span>Tax ({code})</span>
              <span className="font-mono">{fmt(amount, currency)}</span>
            </div>
          ))
        ) : (
          parseFloat(totals.tax_amount) > 0 && (
            <div className="flex justify-between text-gray-400">
              <span>Tax</span>
              <span className="font-mono">{fmt(totals.tax_amount, currency)}</span>
            </div>
          )
        )}

        {/* Rounding */}
        {hasRounding && (
          <div className="flex justify-between text-gray-500 text-xs">
            <span>Rounding</span>
            <span className="font-mono">
              {parseFloat(totals.rounding_amount) > 0 ? '+' : ''}
              {fmt(totals.rounding_amount, currency)}
            </span>
          </div>
        )}

      </div>

      {/* Grand Total */}
      <div className="px-4 py-3 bg-gray-800/60 border-t border-gray-700 flex justify-between items-center">
        <span className="text-white font-semibold">TOTAL</span>
        <span className="text-white text-xl font-bold font-mono">
          {fmt(totals.grand_total, currency)}
        </span>
      </div>
    </div>
  )
}
