// =============================================================================
// RestaurantFlow — Inventory Dashboard
// Phase 10
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getInventoryDashboard } from '@/services/inventory'
import type { InventoryDashboard } from '@/types'

interface StatCardProps {
  label: string
  value: number | string
  to: string
  variant?: 'default' | 'warning' | 'danger' | 'info'
}

function StatCard({ label, value, to, variant = 'default' }: StatCardProps) {
  const colours = {
    default: 'text-white',
    warning: 'text-amber-400',
    danger:  'text-red-400',
    info:    'text-brand-400',
  }
  return (
    <Link
      to={to}
      className="bg-gray-800 border border-gray-700 rounded-xl p-5 hover:border-gray-600 transition-colors"
    >
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-3xl font-bold ${colours[variant]}`}>{value}</p>
    </Link>
  )
}

export function InventoryDashboard() {
  const [data, setData] = useState<InventoryDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getInventoryDashboard()
      .then(r => setData(r.data))
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-white">Inventory</h1>
        <p className="text-sm text-gray-500 mt-1">Stock overview and quick links</p>
      </div>

      {loading && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-5 animate-pulse h-24" />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {data && (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <StatCard label="Total Items" value={data.total_items} to="/inventory/items" variant="default" />
          <StatCard label="Low Stock" value={data.low_stock} to="/inventory/stock?status=LOW_STOCK" variant="warning" />
          <StatCard label="Out of Stock" value={data.out_of_stock} to="/inventory/stock?status=OUT_OF_STOCK" variant="danger" />
          <StatCard label="Pending Purchases" value={data.pending_purchases} to="/inventory/purchases?status=APPROVED" variant="info" />
          <StatCard label="Pending Transfers" value={data.pending_transfers} to="/inventory/transfers?status=REQUESTED" variant="info" />
          <StatCard label="Pending Wastage" value={data.pending_wastage} to="/inventory/wastage?status=PENDING" variant="warning" />
        </div>
      )}

      {/* Quick navigation */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Quick Access</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Stock Overview', to: '/inventory/stock' },
            { label: 'Purchase Orders', to: '/inventory/purchases' },
            { label: 'Stock Transfers', to: '/inventory/transfers' },
            { label: 'Wastage', to: '/inventory/wastage' },
            { label: 'Adjustments', to: '/inventory/adjustments' },
            { label: 'Suppliers', to: '/inventory/suppliers' },
            { label: 'Items', to: '/inventory/items' },
            { label: 'Movement History', to: '/inventory/movements' },
          ].map(item => (
            <Link
              key={item.to}
              to={item.to}
              className="bg-gray-800/60 border border-gray-700 rounded-lg px-4 py-3 text-sm text-gray-300 hover:text-white hover:border-gray-600 transition-colors"
            >
              {item.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
