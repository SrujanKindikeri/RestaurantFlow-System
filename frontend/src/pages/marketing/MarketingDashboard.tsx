// =============================================================================
// RestaurantFlow — Marketing Dashboard
// Phase 18
// =============================================================================

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import marketingApi, { MarketingDashboardStats } from '@/services/marketing'

function KPICard({
  label,
  value,
  sub,
  color = 'blue',
}: {
  label: string
  value: string | number
  sub?: string
  color?: 'blue' | 'green' | 'amber' | 'purple' | 'red' | 'gray'
}) {
  const dotColor: Record<string, string> = {
    blue: 'bg-blue-500',
    green: 'bg-emerald-500',
    amber: 'bg-amber-500',
    purple: 'bg-purple-500',
    red: 'bg-red-500',
    gray: 'bg-gray-500',
  }
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-2">
      <div className="flex items-center gap-2">
        <span className={`inline-block w-2 h-2 rounded-full ${dotColor[color]}`} />
        <p className="text-xs text-gray-500 uppercase tracking-wide font-medium">{label}</p>
      </div>
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      {sub && <p className="text-xs text-gray-400">{sub}</p>}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    RUNNING:          'bg-emerald-100 text-emerald-700',
    SCHEDULED:        'bg-blue-100 text-blue-700',
    PAUSED:           'bg-amber-100 text-amber-700',
    DRAFT:            'bg-gray-100 text-gray-600',
    PENDING_APPROVAL: 'bg-purple-100 text-purple-700',
    APPROVED:         'bg-teal-100 text-teal-700',
    COMPLETED:        'bg-gray-200 text-gray-700',
    CANCELLED:        'bg-red-100 text-red-600',
    FAILED:           'bg-red-200 text-red-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[status] ?? 'bg-gray-100 text-gray-500'}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

export function MarketingDashboard() {
  const [stats, setStats] = useState<MarketingDashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    marketingApi.getDashboard()
      .then(r => setStats(r.data))
      .catch(() => setError('Failed to load marketing dashboard.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="p-12 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }
  if (error) {
    return <div className="p-12 text-center text-red-500 text-sm">{error}</div>
  }

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Marketing</h1>
          <p className="text-sm text-gray-500 mt-0.5">Campaigns, promotions and customer engagement</p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/marketing/campaigns/new"
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 font-medium"
          >
            + New Campaign
          </Link>
          <Link
            to="/marketing/promotions/new"
            className="px-4 py-2 bg-white border border-gray-200 text-gray-700 text-sm rounded-lg hover:bg-gray-50 font-medium"
          >
            + New Promotion
          </Link>
        </div>
      </div>

      {/* KPI Grid */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <KPICard
            label="Active Campaigns"
            value={stats.active_campaigns}
            color="green"
            sub="Currently running"
          />
          <KPICard
            label="Scheduled"
            value={stats.scheduled_campaigns}
            color="blue"
            sub="Upcoming"
          />
          <KPICard
            label="Pending Approvals"
            value={stats.pending_approvals}
            color={stats.pending_approvals > 0 ? 'amber' : 'gray'}
            sub="Need review"
          />
          <KPICard
            label="Total Conversions"
            value={stats.total_conversions.toLocaleString()}
            color="purple"
            sub="Directly attributed"
          />
          <KPICard
            label="Discount Given"
            value={`₹${parseFloat(stats.total_discount_given).toLocaleString()}`}
            color="red"
            sub="Across all promotions"
          />
        </div>
      )}

      {/* Quick Links */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          to="/marketing/campaigns"
          className="bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-sm transition-all group"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 bg-blue-50 rounded-lg flex items-center justify-center group-hover:bg-blue-100 transition-colors">
              <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                  d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13.683A4.001 4.001 0 017 6h1.832c4.1 0 7.625-1.234 9.168-3v14c-1.543-1.766-5.067-3-9.168-3H7a3.988 3.988 0 01-1.564-.317z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-sm">Campaigns</p>
              {stats && (
                <p className="text-xs text-gray-500">
                  {stats.active_campaigns} active · {stats.draft_campaigns} draft
                </p>
              )}
            </div>
          </div>
          <p className="text-xs text-gray-400">Manage customer outreach campaigns</p>
        </Link>

        <Link
          to="/marketing/promotions"
          className="bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-sm transition-all group"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 bg-emerald-50 rounded-lg flex items-center justify-center group-hover:bg-emerald-100 transition-colors">
              <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                  d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-sm">Promotions</p>
              {stats && (
                <p className="text-xs text-gray-500">
                  {stats.total_promotion_uses} total uses
                </p>
              )}
            </div>
          </div>
          <p className="text-xs text-gray-400">Discount codes and offers</p>
        </Link>

        <Link
          to="/marketing/analytics"
          className="bg-white border border-gray-200 rounded-xl p-5 hover:border-blue-300 hover:shadow-sm transition-all group"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-9 h-9 bg-purple-50 rounded-lg flex items-center justify-center group-hover:bg-purple-100 transition-colors">
              <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.75}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <p className="font-semibold text-gray-900 text-sm">Analytics</p>
              {stats && (
                <p className="text-xs text-gray-500">
                  ₹{parseFloat(stats.total_revenue_attributed).toLocaleString()} attributed
                </p>
              )}
            </div>
          </div>
          <p className="text-xs text-gray-400">Conversion & attribution metrics</p>
        </Link>
      </div>

      {/* Attribution Note */}
      <p className="text-xs text-gray-400 border-t border-gray-100 pt-4">
        Revenue figures represent <strong>directly attributed</strong> orders only.
        For official financial statements, use the Reporting module.
      </p>
    </div>
  )
}
