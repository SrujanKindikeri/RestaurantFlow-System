// =============================================================================
// RestaurantFlow — Enterprise Dashboard
// Phase 20
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2, GitBranch, CheckCircle2, AlertTriangle,
  Clock, Users, RefreshCw, ArrowRight, BarChart2, Settings,
} from 'lucide-react'
import { enterpriseApi, EnterpriseDashboard as TDashboard } from '@/services/enterprise'

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------
function KpiCard({
  title, value, subtitle, icon, color = 'blue', linkTo,
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  color?: string
  linkTo?: string
}) {
  const colorMap: Record<string, string> = {
    blue:   'bg-blue-50 text-blue-700',
    green:  'bg-green-50 text-green-700',
    red:    'bg-red-50 text-red-700',
    orange: 'bg-orange-50 text-orange-700',
    yellow: 'bg-yellow-50 text-yellow-700',
    gray:   'bg-gray-50 text-gray-700',
  }
  const card = (
    <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-start gap-3 hover:shadow-sm transition-shadow">
      <div className={`p-2 rounded-lg flex-shrink-0 ${colorMap[color] ?? colorMap.blue}`} aria-hidden="true">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5">{value}</p>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
  if (linkTo) return <Link to={linkTo} className="block focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg">{card}</Link>
  return card
}

// ---------------------------------------------------------------------------
// Status badge
// ---------------------------------------------------------------------------
function StatusBadge({ label, count, color }: { label: string; count: number; color: string }) {
  if (count === 0) return null
  const colors: Record<string, string> = {
    red:    'bg-red-100 text-red-700',
    yellow: 'bg-yellow-100 text-yellow-800',
    blue:   'bg-blue-100 text-blue-700',
    gray:   'bg-gray-100 text-gray-600',
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${colors[color] ?? colors.gray}`}>
      {label}: {count}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main dashboard
// ---------------------------------------------------------------------------
export function EnterpriseDashboard() {
  const [data, setData] = useState<TDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const result = await enterpriseApi.getDashboard()
      setData(result)
    } catch {
      setError('Failed to load enterprise dashboard.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Enterprise Operations</h1>
          <p className="text-sm text-gray-500 mt-1">Multi-branch configuration and management</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          aria-label="Refresh dashboard"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-6" role="alert">
          {error}
        </div>
      )}

      {/* Skeleton */}
      {loading && !data && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-24 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {/* KPI Grid */}
      {data && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
            <KpiCard
              title="Total Restaurants"
              value={data.total_restaurants}
              icon={<Building2 className="h-5 w-5" />}
              color="blue"
              linkTo="/enterprise/branches"
            />
            <KpiCard
              title="Total Branches"
              value={data.total_branches}
              icon={<GitBranch className="h-5 w-5" />}
              color="blue"
              linkTo="/enterprise/branches"
            />
            <KpiCard
              title="Active Branches"
              value={data.active_branches}
              icon={<CheckCircle2 className="h-5 w-5" />}
              color="green"
            />
            <KpiCard
              title="Temporarily Closed"
              value={data.temporarily_closed}
              icon={<Clock className="h-5 w-5" />}
              color={data.temporarily_closed > 0 ? 'orange' : 'gray'}
            />
            <KpiCard
              title="Pending Closures"
              value={data.pending_closures}
              subtitle="Awaiting approval"
              icon={<AlertTriangle className="h-5 w-5" />}
              color={data.pending_closures > 0 ? 'yellow' : 'gray'}
              linkTo="/enterprise/schedules"
            />
            <KpiCard
              title="Pending Rollouts"
              value={data.pending_rollouts}
              subtitle="In progress"
              icon={<BarChart2 className="h-5 w-5" />}
              color={data.pending_rollouts > 0 ? 'blue' : 'gray'}
              linkTo="/enterprise/rollouts"
            />
            <KpiCard
              title="Pending Transfers"
              value={data.pending_transfers}
              subtitle="Staff transfers"
              icon={<Users className="h-5 w-5" />}
              color={data.pending_transfers > 0 ? 'orange' : 'gray'}
              linkTo="/enterprise/staff"
            />
            <KpiCard
              title="Failed Rollouts"
              value={data.failed_rollouts_24h}
              subtitle="Last 24 hours"
              icon={<AlertTriangle className="h-5 w-5" />}
              color={data.failed_rollouts_24h > 0 ? 'red' : 'gray'}
              linkTo="/enterprise/rollouts"
            />
          </div>

          {/* Quick nav */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { label: 'Branch Management',   sub: 'Status, schedules, closures', to: '/enterprise/branches',          icon: <GitBranch className="h-5 w-5" /> },
              { label: 'Configuration',        sub: 'Hierarchy, effective values', to: '/enterprise/configuration',     icon: <Settings className="h-5 w-5" /> },
              { label: 'Menu Rollouts',        sub: 'Availability & pricing',       to: '/enterprise/rollouts',          icon: <BarChart2 className="h-5 w-5" /> },
              { label: 'Staff Management',     sub: 'Assignments & transfers',      to: '/enterprise/staff',             icon: <Users className="h-5 w-5" /> },
              { label: 'Approval Policies',    sub: 'Thresholds & permissions',     to: '/enterprise/approval-policies', icon: <CheckCircle2 className="h-5 w-5" /> },
              { label: 'Audit Log',            sub: 'Full enterprise history',      to: '/enterprise/audit',             icon: <AlertTriangle className="h-5 w-5" /> },
            ].map(({ label, sub, to, icon }) => (
              <Link
                key={to}
                to={to}
                className="bg-white rounded-lg border border-gray-200 p-4 flex items-center justify-between hover:shadow-sm hover:border-blue-300 transition group focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={label}
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-gray-50 rounded-lg text-gray-600 group-hover:text-blue-600 transition" aria-hidden="true">
                    {icon}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{label}</p>
                    <p className="text-xs text-gray-500">{sub}</p>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-blue-500 transition" aria-hidden="true" />
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
