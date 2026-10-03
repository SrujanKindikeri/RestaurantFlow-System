// =============================================================================
// RestaurantFlow — Kitchen History Page
// Phase 7
// =============================================================================

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useKitchenHistory } from '@/hooks/useKitchen'
import { KitchenPriorityBadge } from '@/components/kitchen/KitchenPriorityBadge'
import { cn } from '@/utils/cn'
import type { KitchenOrder, KitchenOrderStatus } from '@/types'

const STATUS_BADGE: Record<KitchenOrderStatus, { bg: string; text: string }> = {
  NEW:       { bg: 'bg-blue-900/40',    text: 'text-blue-400' },
  ACCEPTED:  { bg: 'bg-orange-900/40',  text: 'text-orange-400' },
  PREPARING: { bg: 'bg-purple-900/40',  text: 'text-purple-400' },
  READY:     { bg: 'bg-green-900/40',   text: 'text-green-400' },
  CANCELLED: { bg: 'bg-gray-800',       text: 'text-gray-500' },
}

function StatusBadge({ status }: { status: KitchenOrderStatus }) {
  const cfg = STATUS_BADGE[status]
  return (
    <span className={cn('inline-flex px-2 py-0.5 rounded text-xs font-medium', cfg.bg, cfg.text)}>
      {status}
    </span>
  )
}

function HistoryRow({ order }: { order: KitchenOrder }) {
  const readyDuration = order.ready_at && order.received_at
    ? Math.round((new Date(order.ready_at).getTime() - new Date(order.received_at).getTime()) / 1000)
    : null

  const fmt = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m}:${String(s).padStart(2, '0')}`
  }

  return (
    <tr className="border-b border-gray-800 hover:bg-gray-900/50 transition-colors">
      <td className="px-4 py-3 font-mono text-sm text-white">{order.order_number}</td>
      <td className="px-4 py-3">
        <div className="text-sm text-gray-300">{order.order_type.replace('_', '-')}</div>
        {order.table_number && <div className="text-xs text-gray-600">T{order.table_number}</div>}
        {order.counter_code && <div className="text-xs text-gray-600">{order.counter_code}</div>}
      </td>
      <td className="px-4 py-3"><StatusBadge status={order.status} /></td>
      <td className="px-4 py-3"><KitchenPriorityBadge priority={order.priority} /></td>
      <td className="px-4 py-3 text-xs text-gray-400">
        {new Date(order.received_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </td>
      <td className="px-4 py-3 text-xs text-gray-400">
        {readyDuration !== null ? fmt(readyDuration) : '—'}
      </td>
      <td className="px-4 py-3 text-xs text-gray-500">
        {order.item_count} item{order.item_count !== 1 ? 's' : ''}
      </td>
    </tr>
  )
}

export function KitchenHistory() {
  const today = new Date().toISOString().split('T')[0]
  const [dateFrom, setDateFrom] = useState(today)
  const [dateTo, setDateTo] = useState(today)
  const [statusFilter, setStatusFilter] = useState('')

  const params = {
    date_from: dateFrom,
    date_to: dateTo,
    ...(statusFilter ? { status: statusFilter } : {}),
    ordering: '-received_at',
  }

  const { data, isLoading, isError } = useKitchenHistory(params)

  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white">Kitchen History</h1>
          <p className="text-sm text-gray-500 mt-0.5">Past kitchen orders and preparation times</p>
        </div>
        <Link
          to="/kitchen"
          className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
        >
          ← Live KDS
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5 bg-gray-900 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500" htmlFor="date-from">From</label>
          <input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={e => setDateFrom(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500" htmlFor="date-to">To</label>
          <input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={e => setDateTo(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500" htmlFor="status-filter">Status</label>
          <select
            id="status-filter"
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-brand-500"
          >
            <option value="">All</option>
            <option value="NEW">New</option>
            <option value="ACCEPTED">Accepted</option>
            <option value="PREPARING">Preparing</option>
            <option value="READY">Ready</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Results */}
      {isLoading && (
        <div className="flex items-center justify-center h-32 text-gray-500">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-500 mr-3" />
          Loading history…
        </div>
      )}

      {isError && (
        <div className="bg-red-900/20 border border-red-800 text-red-400 rounded-lg p-4 text-sm">
          Failed to load kitchen history.
        </div>
      )}

      {!isLoading && !isError && (
        <>
          <p className="text-xs text-gray-600 mb-3">
            {data?.count ?? 0} order{(data?.count ?? 0) !== 1 ? 's' : ''} found
          </p>
          <div className="rounded-lg border border-gray-800 overflow-hidden">
            <table className="w-full text-left" aria-label="Kitchen history table">
              <thead className="bg-gray-900 border-b border-gray-800">
                <tr>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Order #</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Priority</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Received</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Prep Time</th>
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Items</th>
                </tr>
              </thead>
              <tbody>
                {(data?.results ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-600">
                      No kitchen orders found for this date range.
                    </td>
                  </tr>
                ) : (
                  (data?.results ?? []).map(order => (
                    <HistoryRow key={order.id} order={order} />
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
