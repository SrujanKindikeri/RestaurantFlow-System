// =============================================================================
// RestaurantFlow — Payment Status Badge
// Phase 9
// =============================================================================

import type { PaymentStatus, BillPaymentStatus, RefundStatus } from '@/types'

const PAYMENT_STATUS_STYLES: Record<PaymentStatus, string> = {
  PENDING:            'bg-yellow-900/40 border-yellow-700 text-yellow-400',
  COMPLETED:          'bg-green-900/40 border-green-700 text-green-400',
  FAILED:             'bg-red-900/40 border-red-700 text-red-400',
  CANCELLED:          'bg-gray-800 border-gray-700 text-gray-400',
  REFUNDED:           'bg-blue-900/40 border-blue-700 text-blue-400',
  PARTIALLY_REFUNDED: 'bg-purple-900/40 border-purple-700 text-purple-400',
}

const BILL_PAYMENT_STATUS_STYLES: Record<BillPaymentStatus, string> = {
  UNPAID:         'bg-red-900/40 border-red-800 text-red-400',
  PARTIALLY_PAID: 'bg-yellow-900/40 border-yellow-700 text-yellow-400',
  PAID:           'bg-green-900/40 border-green-700 text-green-400',
  OVERPAID:       'bg-orange-900/40 border-orange-700 text-orange-400',
}

const REFUND_STATUS_STYLES: Record<RefundStatus, string> = {
  REQUESTED: 'bg-yellow-900/40 border-yellow-700 text-yellow-400',
  APPROVED:  'bg-blue-900/40 border-blue-700 text-blue-400',
  REJECTED:  'bg-red-900/40 border-red-700 text-red-400',
  PROCESSED: 'bg-green-900/40 border-green-700 text-green-400',
  CANCELLED: 'bg-gray-800 border-gray-700 text-gray-400',
}

export function PaymentStatusBadge({ status }: { status: PaymentStatus }) {
  const cls = PAYMENT_STATUS_STYLES[status] ?? 'bg-gray-800 border-gray-700 text-gray-400'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border font-medium ${cls}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

export function BillPaymentStatusBadge({ status }: { status: BillPaymentStatus }) {
  const cls = BILL_PAYMENT_STATUS_STYLES[status] ?? 'bg-gray-800 border-gray-700 text-gray-400'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border font-medium ${cls}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

export function RefundStatusBadge({ status }: { status: RefundStatus }) {
  const cls = REFUND_STATUS_STYLES[status] ?? 'bg-gray-800 border-gray-700 text-gray-400'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border font-medium ${cls}`}>
      {status}
    </span>
  )
}
