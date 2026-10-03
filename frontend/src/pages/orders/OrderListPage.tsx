// =============================================================================
// RestaurantFlow — Order List Page
// Phase 6
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useOrders } from '@/hooks/useOrders'
import { OrderStatusBadge, OrderTypeBadge } from '@/components/orders/OrderStatusBadge'
import { Card } from '@/components/Card'
import type { OrderStatus, OrderType } from '@/types'

export function OrderListPage() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<OrderStatus | ''>('')
  const [typeFilter, setTypeFilter]  = useState<OrderType | ''>('')
  const [dateFilter, setDateFilter]  = useState('')
  const [page, setPage] = useState(1)

  const params: Record<string, string | number> = { page }
  if (statusFilter) params.status = statusFilter
  if (typeFilter)  params.order_type = typeFilter
  if (dateFilter)  params.date = dateFilter

  const { data, isLoading, error } = useOrders(params)

  const orders = data?.results ?? []
  const totalCount = data?.count ?? 0
  const pageSize = 20
  const totalPages = Math.ceil(totalCount / pageSize)

  return (
    <div className="p-4 sm:p-6 max-w-screen-xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-100">Orders</h1>
          <p className="text-xs text-gray-500 mt-0.5">{totalCount} total orders</p>
        </div>
        <button
          onClick={() => navigate('/orders/new')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-brand-500 hover:bg-brand-400 text-white transition-colors"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New Order
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value as OrderStatus | ''); setPage(1) }}
          className="px-3 py-1.5 rounded-lg text-xs bg-gray-800 border border-gray-700 text-gray-300 focus:outline-none focus:border-brand-500"
          aria-label="Filter by status"
        >
          <option value="">All statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="CONFIRMED">Confirmed</option>
          <option value="CANCELLED">Cancelled</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => { setTypeFilter(e.target.value as OrderType | ''); setPage(1) }}
          className="px-3 py-1.5 rounded-lg text-xs bg-gray-800 border border-gray-700 text-gray-300 focus:outline-none focus:border-brand-500"
          aria-label="Filter by order type"
        >
          <option value="">All types</option>
          <option value="DINE_IN">Dine In</option>
          <option value="COUNTER">Counter</option>
          <option value="TAKEAWAY">Takeaway</option>
        </select>
        <input
          type="date"
          value={dateFilter}
          onChange={(e) => { setDateFilter(e.target.value); setPage(1) }}
          className="px-3 py-1.5 rounded-lg text-xs bg-gray-800 border border-gray-700 text-gray-300 focus:outline-none focus:border-brand-500"
          aria-label="Filter by date"
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" aria-label="Loading orders" />
        </div>
      ) : error ? (
        <Card className="py-8 text-center">
          <p className="text-sm text-red-400">Failed to load orders.</p>
        </Card>
      ) : orders.length === 0 ? (
        <Card className="py-12 text-center">
          <p className="text-sm text-gray-500">No orders found.</p>
          <button
            onClick={() => navigate('/orders/new')}
            className="mt-3 text-xs text-brand-400 hover:text-brand-300 transition-colors"
          >
            Create the first order →
          </button>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm" role="table">
              <thead>
                <tr className="border-b border-gray-800">
                  {['Order #', 'Type', 'Branch', 'Table / Counter', 'Waiter', 'Items', 'Total', 'Status', 'Created'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wider whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                  <th className="px-4 py-3" aria-label="Actions" />
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60">
                {orders.map((order) => (
                  <tr
                    key={order.id}
                    className="hover:bg-gray-800/30 cursor-pointer transition-colors"
                    onClick={() => navigate(`/orders/${order.id}`)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-brand-400 whitespace-nowrap">
                      {order.order_number}
                    </td>
                    <td className="px-4 py-3">
                      <OrderTypeBadge type={order.order_type} />
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs truncate max-w-[120px]">
                      {order.branch_name}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">
                      {order.table_number ?? order.counter_code ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs truncate max-w-[100px]">
                      {order.assigned_waiter_name ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs text-center">
                      {order.item_count}
                    </td>
                    <td className="px-4 py-3 text-gray-200 text-xs font-medium whitespace-nowrap">
                      ₹{parseFloat(order.preview_total).toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <OrderStatusBadge status={order.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-[10px] whitespace-nowrap">
                      {new Date(order.created_at).toLocaleString('en-IN', {
                        dateStyle: 'short', timeStyle: 'short',
                      })}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <svg className="h-4 w-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                      </svg>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 rounded bg-gray-800 hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
