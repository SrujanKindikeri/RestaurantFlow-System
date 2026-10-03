// =============================================================================
// RestaurantFlow — Bill Items Table
// Phase 8
// =============================================================================

import type { BillItem } from '@/types'

interface Props {
  items: BillItem[]
  currency?: string
}

function fmt(v: string, currency = '₹') {
  const n = parseFloat(v)
  if (isNaN(n)) return `${currency}0.00`
  return `${currency}${Math.abs(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function BillItemsTable({ items, currency = '₹' }: Props) {
  if (!items || items.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">No items on this bill.</div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-gray-500 text-xs uppercase">
            <th className="text-left py-2 pr-4">Item</th>
            <th className="text-right py-2 px-2">Qty</th>
            <th className="text-right py-2 px-2">Unit Price</th>
            <th className="text-right py-2 px-2">Gross</th>
            <th className="text-right py-2 px-2">Discount</th>
            <th className="text-right py-2 px-2">Taxable</th>
            <th className="text-right py-2 px-2">Tax%</th>
            <th className="text-right py-2 pl-2">Total</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const hasDiscount = parseFloat(item.discount_amount) > 0
            return (
              <tr key={item.id} className="border-b border-gray-800/50 text-gray-300">
                <td className="py-2.5 pr-4">
                  <div className="font-medium text-white">{item.item_name_snapshot}</div>
                  {item.sku_snapshot && (
                    <div className="text-xs text-gray-600 font-mono">{item.sku_snapshot}</div>
                  )}
                  {item.tax_code && (
                    <div className="text-xs text-gray-600">{item.tax_code}</div>
                  )}
                </td>
                <td className="py-2.5 px-2 text-right font-mono">{parseFloat(item.quantity).toFixed(item.quantity.includes('.') ? 3 : 0)}</td>
                <td className="py-2.5 px-2 text-right font-mono">{fmt(item.unit_price, currency)}</td>
                <td className="py-2.5 px-2 text-right font-mono">{fmt(item.gross_amount, currency)}</td>
                <td className="py-2.5 px-2 text-right font-mono text-amber-400">
                  {hasDiscount ? `−${fmt(item.discount_amount, currency)}` : '—'}
                </td>
                <td className="py-2.5 px-2 text-right font-mono">{fmt(item.taxable_amount, currency)}</td>
                <td className="py-2.5 px-2 text-right font-mono text-gray-500">
                  {parseFloat(item.tax_rate) > 0 ? `${parseFloat(item.tax_rate).toFixed(1)}%` : '—'}
                </td>
                <td className="py-2.5 pl-2 text-right font-mono font-semibold text-white">
                  {fmt(item.total_amount, currency)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
