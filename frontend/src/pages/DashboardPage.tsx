// =============================================================================
// RestaurantFlow — Dashboard Page
// Phase 2: Organization stats + system health + quick links
// =============================================================================

import { Link } from 'react-router-dom'
import { useHealth } from '@/hooks/useHealth'
import { useOrganizationStats } from '@/hooks/useOrganizations'
import { StatusIndicator } from '@/components/StatusIndicator'
import { Card } from '@/components/Card'
import { StatCard } from '@/components/ui/StatCard'

export function DashboardPage() {
  const { data: healthData, isLoading: healthLoading, isError: healthError, dataUpdatedAt } = useHealth()
  const { data: stats, isLoading: statsLoading } = useOrganizationStats()

  const backendStatus = healthLoading ? 'loading' : healthError ? 'disconnected' : 'connected'
  const apiStatus = healthLoading ? 'loading' : healthData?.status === 'ok' ? 'connected' : 'disconnected'
  const lastChecked = dataUpdatedAt ? new Date(dataUpdatedAt).toLocaleTimeString() : null

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-xs text-brand-400 font-medium">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-500" />
            Phase 2 — Organizations
          </span>
        </div>
        <h1 className="text-2xl font-bold text-white mt-2">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1">
          Overview of your RestaurantFlow organizational structure.
        </p>
      </div>

      {/* Organization stats */}
      <section aria-labelledby="org-stats-heading" className="mb-8">
        <h2
          id="org-stats-heading"
          className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3"
        >
          Organization Overview
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <StatCard
            label="Organizations"
            value={stats?.total_organizations ?? '—'}
            loading={statsLoading}
            color="default"
          />
          <StatCard
            label="Active Orgs"
            value={stats?.active_organizations ?? '—'}
            loading={statsLoading}
            color="green"
          />
          <StatCard
            label="Restaurants"
            value={stats?.total_restaurants ?? '—'}
            loading={statsLoading}
            color="blue"
          />
          <StatCard
            label="Active Rests."
            value={stats?.active_restaurants ?? '—'}
            loading={statsLoading}
            color="green"
          />
          <StatCard
            label="Branches"
            value={stats?.total_branches ?? '—'}
            loading={statsLoading}
            color="purple"
          />
          <StatCard
            label="Active Branches"
            value={stats?.active_branches ?? '—'}
            loading={statsLoading}
            color="green"
          />
        </div>
      </section>

      {/* Quick links */}
      <section aria-labelledby="quick-links-heading" className="mb-8">
        <h2
          id="quick-links-heading"
          className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3"
        >
          Quick Links
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            {
              label: 'Organizations',
              to: '/organizations',
              desc: 'Manage companies and legal entities',
              color: 'text-brand-400',
              bg: 'bg-brand-500/10 border-brand-500/20 hover:border-brand-500/40',
            },
            {
              label: 'Restaurants',
              to: '/restaurants',
              desc: 'View and manage all restaurants',
              color: 'text-blue-400',
              bg: 'bg-blue-500/10 border-blue-500/20 hover:border-blue-500/40',
            },
            {
              label: 'Branches',
              to: '/branches',
              desc: 'View all physical locations',
              color: 'text-purple-400',
              bg: 'bg-purple-500/10 border-purple-500/20 hover:border-purple-500/40',
            },
          ].map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={`rounded-xl border px-5 py-4 transition-colors ${item.bg} group`}
            >
              <p className={`font-semibold text-sm ${item.color} mb-1`}>
                {item.label} →
              </p>
              <p className="text-xs text-gray-600 group-hover:text-gray-500 transition-colors">
                {item.desc}
              </p>
            </Link>
          ))}
        </div>
      </section>

      <div className="border-t border-gray-800 mb-8" />

      {/* System status */}
      <section aria-labelledby="system-status-heading">
        <h2
          id="system-status-heading"
          className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3"
        >
          System Status
        </h2>
        <Card description="Live connectivity check between frontend and backend.">
          <div className="flex flex-col gap-2">
            <StatusIndicator
              status={backendStatus}
              label="Backend"
              sublabel="Django REST API"
            />
            <StatusIndicator
              status={apiStatus}
              label="API"
              sublabel={healthData ? healthData.service : 'GET /api/health/'}
            />
          </div>
          {lastChecked && (
            <p className="text-xs text-gray-600 mt-3 text-right">
              Last checked: {lastChecked}
            </p>
          )}
          {healthError && (
            <div
              className="mt-4 rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-3 text-xs text-red-400"
              role="alert"
            >
              <strong className="font-semibold">Cannot reach backend.</strong>{' '}
              Make sure the Django server is running on{' '}
              <code className="font-mono">
                {import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'}
              </code>
              .
            </div>
          )}
        </Card>
      </section>

      {/* Phase roadmap */}
      <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 gap-2">
        {[
          { phase: '1', label: 'Foundation', done: true },
          { phase: '2', label: 'Organizations', active: true },
          { phase: '3', label: 'Users & Roles', active: false },
          { phase: '4', label: 'Counters & Sessions', active: false },
          { phase: '5', label: 'Menu', active: false },
          { phase: '6', label: 'Tables & Orders', active: false },
        ].map((item) => (
          <div
            key={item.phase}
            className={`rounded-lg px-3 py-2 text-xs border ${
              item.active
                ? 'bg-brand-500/10 border-brand-500/30 text-brand-400'
                : item.done
                ? 'bg-green-500/5 border-green-800/30 text-green-600'
                : 'bg-gray-900/40 border-gray-800 text-gray-700'
            }`}
          >
            <span className="font-semibold">Phase {item.phase}</span>
            {item.done && !item.active && (
              <span className="ml-1 text-green-700">✓</span>
            )}
            <div className="mt-0.5 text-[11px] opacity-80">{item.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
