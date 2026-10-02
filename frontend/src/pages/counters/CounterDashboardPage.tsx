// =============================================================================
// RestaurantFlow — Counter Dashboard Page
// Phase 4
// =============================================================================

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useCounterDashboard } from '@/hooks/useCounters'
import { useAllBranches } from '@/hooks/useBranches'
import { PageHeader } from '@/components/ui/PageHeader'
import { CounterStatusBadge, SessionStatusBadge } from '@/components/counter/CounterStatusBadge'
import { formatCurrency } from '@/utils/money'
import type { CounterDashboardItem } from '@/types'

const counterTypeLabel: Record<string, string> = {
  MAIN_BILLING: 'Main Billing',
  TAKEAWAY: 'Takeaway',
  SNACKS: 'Snacks',
  DRIVE_THROUGH: 'Drive Through',
  OTHER: 'Other',
}

function CounterCard({ item }: { item: CounterDashboardItem }) {
  return (
    <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-hidden hover:border-gray-700 transition-colors">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 flex items-start justify-between border-b border-gray-800/60">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
              {item.code}
            </span>
            <CounterStatusBadge status={item.status} />
          </div>
          <Link
            to={`/counters/${item.id}`}
            className="text-gray-200 font-medium text-sm mt-1 block hover:text-brand-400 transition-colors"
          >
            {item.name}
          </Link>
          <p className="text-xs text-gray-600 mt-0.5">
            {counterTypeLabel[item.counter_type] ?? item.counter_type}
          </p>
        </div>
      </div>

      {/* Session info */}
      <div className="px-5 py-3">
        {item.current_session ? (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              <SessionStatusBadge status={item.current_session.status} />
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <p className="text-gray-600">Cashier</p>
                <p className="text-gray-300 truncate">{item.current_session.opened_by_name}</p>
              </div>
              <div>
                <p className="text-gray-600">Opened</p>
                <p className="text-gray-300">
                  {new Date(item.current_session.opened_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>
              <div className="col-span-2">
                <p className="text-gray-600">Opening Cash</p>
                <p className="text-gray-300 font-mono font-medium">
                  {formatCurrency(item.current_session.opening_cash)}
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-gray-600 py-1">
            {item.status === 'MAINTENANCE'
              ? '🔧 Under Maintenance'
              : item.status === 'INACTIVE'
              ? 'Counter Inactive'
              : 'No active session'}
            {item.assigned_cashier && item.status === 'ACTIVE' && (
              <p className="mt-1 text-gray-700">
                Assigned: {item.assigned_cashier.user_name}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export function CounterDashboardPage() {
  const [branchId, setBranchId] = useState('')
  const { data: branchesData }  = useAllBranches()
  const { data, isLoading, isError } = useCounterDashboard(branchId || undefined)

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Counter Dashboard"
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Counter Dashboard' }]}
        actions={
          <Link
            to="/counter-sessions"
            className="text-xs text-brand-400 hover:text-brand-300 transition-colors"
          >
            All Sessions →
          </Link>
        }
      />

      {/* Branch filter */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          aria-label="Filter by branch"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={branchId}
          onChange={(e) => setBranchId(e.target.value)}
        >
          <option value="">All Branches</option>
          {branchesData?.results.map((b) => (
            <option key={b.id} value={b.id}>{b.name}</option>
          ))}
        </select>
      </div>

      {/* Summary stats */}
      {data && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
          {[
            { label: 'Total', value: data.summary.total, color: 'text-gray-300' },
            { label: 'Active', value: data.summary.active, color: 'text-green-400' },
            { label: 'Sessions Open', value: data.summary.sessions_open, color: 'text-brand-400' },
            { label: 'Inactive', value: data.summary.inactive, color: 'text-gray-500' },
            { label: 'Maintenance', value: data.summary.maintenance, color: 'text-yellow-400' },
          ].map((stat) => (
            <div
              key={stat.label}
              className="rounded-lg bg-gray-900/60 border border-gray-800 px-4 py-3 text-center"
            >
              <p className={`text-2xl font-semibold ${stat.color}`}>{stat.value}</p>
              <p className="text-xs text-gray-600 mt-0.5">{stat.label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-36 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load counter dashboard.
        </div>
      )}

      {!isLoading && data && data.counters.length === 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-16 text-center">
          <p className="text-gray-500 text-sm">No counters available.</p>
          <Link
            to="/counters"
            className="mt-3 inline-block text-xs text-brand-400 hover:text-brand-300 transition-colors"
          >
            Manage Counters →
          </Link>
        </div>
      )}

      {/* Counter grid */}
      {!isLoading && data && data.counters.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.counters.map((item) => (
            <CounterCard key={item.id} item={item} />
          ))}
        </div>
      )}

      <p className="text-xs text-gray-700 mt-4 text-center">
        Auto-refreshes every 30 seconds.
      </p>
    </div>
  )
}
