// =============================================================================
// RestaurantFlow — Order Detail Page
// Phase 6
// =============================================================================

import { useParams, useNavigate } from 'react-router-dom'
import {
  useOrder,
  useConfirmOrder,
  useCancelOrder,
} from '@/hooks/useOrders'
import {
  updateOrderItem,
  removeOrderItem,
} from '@/services/orders'
import { useQueryClient } from '@tanstack/react-query'
import { orderKeys } from '@/hooks/useOrders'
import { OrderStatusBadge, OrderTypeBadge } from '@/components/orders/OrderStatusBadge'
import { OrderItemList } from '@/components/orders/OrderItemList'
import { OrderSummary } from '@/components/orders/OrderSummary'
import { Card } from '@/components/Card'
import { useAuth } from '@/contexts/AuthContext'

export function OrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user } = useAuth()

  const { data: order, isLoading, error } = useOrder(id!)
  const confirmMutation = useConfirmOrder()
  const cancelMutation  = useCancelOrder()

  const canConfirm = user?.scope?.permissions?.includes('order.confirm')
  const canCancel  =
    user?.scope?.permissions?.includes('order.cancel') ||
    user?.scope?.permissions?.includes('order.cancel.confirmed')

  async function handleUpdateQuantity(itemId: string, delta: number) {
    if (!order || !id) return
    const item = order.items.find((i) => i.id === itemId)
    if (!item) return
    const newQty = parseFloat(item.quantity) + delta
    if (newQty <= 0) {
      await handleRemove(itemId)
      return
    }
    await updateOrderItem(itemId, { quantity: newQty.toFixed(3) })
    qc.invalidateQueries({ queryKey: orderKeys.detail(id) })
  }

  async function handleRemove(itemId: string) {
    if (!id) return
    await removeOrderItem(itemId)
    qc.invalidateQueries({ queryKey: orderKeys.detail(id) })
  }

  function handleConfirm() {
    if (!id) return
    confirmMutation.mutate(id, {
      onSuccess: () => navigate(`/orders/${id}`),
    })
  }

  function handleCancel() {
    if (!id) return
    const reason = window.prompt('Cancellation reason (optional):') ?? ''
    cancelMutation.mutate({ id, data: { reason } })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-32" role="status" aria-label="Loading order">
        <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="p-6 text-center">
        <p className="text-sm text-red-400">Order not found.</p>
        <button
          onClick={() => navigate('/orders')}
          className="mt-2 text-xs text-brand-400 hover:text-brand-300 transition-colors"
        >
          ← Back to orders
        </button>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 max-w-3xl mx-auto space-y-5">
      {/* Back */}
      <button
        onClick={() => navigate('/orders')}
        className="text-xs text-gray-500 hover:text-brand-400 transition-colors flex items-center gap-1"
        aria-label="Back to orders list"
      >
        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
        </svg>
        Orders
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-lg font-bold text-gray-100 font-mono">
              {order.order_number}
            </h1>
            <OrderStatusBadge status={order.status} />
            <OrderTypeBadge type={order.order_type} />
          </div>
          <p className="text-xs text-gray-500 mt-1">{order.branch_name}</p>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2">
          {order.status === 'DRAFT' && canConfirm && (
            <button
              onClick={handleConfirm}
              disabled={confirmMutation.isPending || order.item_count === 0}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-brand-500 hover:bg-brand-400 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {confirmMutation.isPending ? 'Confirming…' : 'Confirm Order'}
            </button>
          )}
          {order.status !== 'CANCELLED' && canCancel && (
            <button
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-800 hover:bg-red-900/40 text-gray-300 hover:text-red-400 border border-gray-700 hover:border-red-800 transition-colors"
            >
              {cancelMutation.isPending ? 'Cancelling…' : 'Cancel'}
            </button>
          )}
        </div>
      </div>

      {/* POS link */}
      {order.status === 'DRAFT' && (
        <button
          onClick={() => navigate('/pos')}
          className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
        >
          → Open in POS screen
        </button>
      )}

      <div className="grid sm:grid-cols-2 gap-4">
        {/* Order info */}
        <Card title="Order Information">
          <dl className="space-y-2 text-sm">
            {([
              ['Table',      order.table_number ?? '—'],
              ['Section',    order.table_section ?? '—'],
              ['Counter',    order.counter_code ?? '—'],
              ['Waiter',     order.assigned_waiter_name ?? '—'],
              ['Created by', order.created_by_name],
              ['Guests',     String(order.guest_count ?? '—')],
              ['Created',    new Date(order.created_at).toLocaleString('en-IN')],
              ...(order.confirmed_at
                ? [['Confirmed', new Date(order.confirmed_at).toLocaleString('en-IN')]]
                : []),
              ...(order.cancelled_at
                ? [['Cancelled', new Date(order.cancelled_at).toLocaleString('en-IN')]]
                : []),
            ] as [string, string][]).map(([label, value]) => (
              <div key={label} className="flex justify-between gap-2">
                <dt className="text-gray-500 flex-shrink-0">{label}</dt>
                <dd className="text-gray-200 font-medium text-right">{value}</dd>
              </div>
            ))}
          </dl>
          {order.notes && (
            <p className="mt-3 text-xs text-gray-400 border-t border-gray-800 pt-2">
              <span className="text-gray-500">Note:</span> {order.notes}
            </p>
          )}
          {order.cancellation_reason && (
            <p className="mt-3 text-xs text-red-400 border-t border-gray-800 pt-2">
              <span className="text-red-500">Reason:</span> {order.cancellation_reason}
            </p>
          )}
        </Card>

        {/* Items */}
        <Card title="Order Items">
          <OrderItemList
            items={order.items}
            orderStatus={order.status}
            onUpdateQuantity={handleUpdateQuantity}
            onRemove={handleRemove}
          />
          <OrderSummary items={order.items} />
        </Card>
      </div>
    </div>
  )
}
