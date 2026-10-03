// =============================================================================
// RestaurantFlow — Tables Dashboard
// Phase 6: Grid view of all dining tables grouped by section
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTables } from '@/hooks/useOrders'
import { useAuth } from '@/contexts/AuthContext'
import { TableGrid } from '@/components/orders/TableGrid'
import { Card } from '@/components/Card'
import type { DiningTable } from '@/types'

export function TablesDashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [sectionFilter, setSectionFilter] = useState('')
  const [occupiedFilter, setOccupiedFilter] = useState<'' | 'true' | 'false'>('')

  const params: Record<string, string | number | boolean> = {}
  if (sectionFilter) params.section = sectionFilter
  if (occupiedFilter !== '') params.occupied = occupiedFilter

  const { data, isLoading, error, refetch } = useTables(params)

  const tables = data?.results ?? []

  // Summary counts
  const totalTables   = tables.length
  const occupiedCount = tables.filter((t) => t.is_occupied).length
  const availableCount = tables.filter((t) => !t.is_occupied && t.status === 'ACTIVE').length
  const inactiveCount = tables.filter((t) => t.status === 'INACTIVE').length

  function handleSelectTable(table: DiningTable) {
    navigate(`/orders/new?table=${table.id}&session=${table.active_session_id ?? ''}`)
  }

  return (
    <div className="p-4 sm:p-6 max-w-screen-xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-gray-100">Tables</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            Dining table status across all your branches
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-gray-400 bg-gray-800 hover:bg-gray-700 transition-colors"
            aria-label="Refresh tables"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          {user?.scope?.permissions?.includes('table.create') && (
            <button
              onClick={() => navigate('/tables/new')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-brand-500 hover:bg-brand-400 text-white transition-colors"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5} aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              Add Table
            </button>
          )}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Total Tables',  value: totalTables,    color: 'text-gray-300' },
          { label: 'Occupied',      value: occupiedCount,  color: 'text-red-400' },
          { label: 'Available',     value: availableCount, color: 'text-emerald-400' },
          { label: 'Inactive',      value: inactiveCount,  color: 'text-gray-500' },
        ].map((stat) => (
          <Card key={stat.label} className="py-3 px-4">
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color} mt-0.5`}>{stat.value}</p>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        <select
          value={occupiedFilter}
          onChange={(e) => setOccupiedFilter(e.target.value as '' | 'true' | 'false')}
          className="px-3 py-1.5 rounded-lg text-xs bg-gray-800 border border-gray-700 text-gray-300 focus:outline-none focus:border-brand-500"
          aria-label="Filter by occupancy"
        >
          <option value="">All status</option>
          <option value="true">Occupied</option>
          <option value="false">Available</option>
        </select>
        <input
          type="text"
          placeholder="Filter by section…"
          value={sectionFilter}
          onChange={(e) => setSectionFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg text-xs bg-gray-800 border border-gray-700 text-gray-300 placeholder-gray-600 focus:outline-none focus:border-brand-500 w-44"
          aria-label="Filter by section"
        />
      </div>

      {/* Table grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-6 h-6 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" aria-label="Loading tables" />
        </div>
      ) : error ? (
        <Card className="py-8 text-center">
          <p className="text-sm text-red-400">Failed to load tables. Please refresh.</p>
        </Card>
      ) : (
        <Card>
          <TableGrid
            tables={tables}
            onSelectTable={handleSelectTable}
          />
        </Card>
      )}

      {/* Order list shortcut */}
      <div className="flex gap-3">
        <button
          onClick={() => navigate('/orders')}
          className="text-xs text-gray-500 hover:text-brand-400 transition-colors"
        >
          → View all orders
        </button>
        <button
          onClick={() => navigate('/orders/new')}
          className="text-xs text-gray-500 hover:text-brand-400 transition-colors"
        >
          → New counter / takeaway order
        </button>
      </div>
    </div>
  )
}
