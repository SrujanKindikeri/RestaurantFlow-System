// =============================================================================
// RestaurantFlow — Central Control Dashboard
// Phase 15
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle, Building2, GitBranch, ShoppingCart,
  DollarSign, ChefHat, Package, CreditCard, FileText,
  Activity, RefreshCw, CheckCircle2, XCircle, AlertCircle,
} from 'lucide-react'
import { centralControlApi, CentralDashboard } from '@/services/centralControl'

// ---------------------------------------------------------------------------
// Severity badge helper
// ---------------------------------------------------------------------------

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, { bg: string; text: string; label: string }> = {
    CRITICAL: { bg: 'bg-red-100', text: 'text-red-800',    label: 'Critical' },
    HIGH:     { bg: 'bg-orange-100', text: 'text-orange-800', label: 'High' },
    MEDIUM:   { bg: 'bg-yellow-100', text: 'text-yellow-800', label: 'Medium' },
    LOW:      { bg: 'bg-blue-100',  text: 'text-blue-800',   label: 'Low' },
    INFO:     { bg: 'bg-gray-100',  text: 'text-gray-700',   label: 'Info' },
  }
  const { bg, text, label } = map[severity] || map.INFO
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${bg} ${text}`}
      role="status"
      aria-label={`Severity: ${label}`}
    >
      {label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------

interface KpiCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  color?: string
  linkTo?: string
  ariaLabel?: string
}

function KpiCard({ title, value, subtitle, icon, color = 'blue', linkTo, ariaLabel }: KpiCardProps) {
  const colorMap: Record<string, string> = {
    blue:   'bg-blue-50 text-blue-700',
    green:  'bg-green-50 text-green-700',
    red:    'bg-red-50 text-red-700',
    orange: 'bg-orange-50 text-orange-700',
    yellow: 'bg-yellow-50 text-yellow-700',
    gray:   'bg-gray-50 text-gray-700',
  }
  const iconColor = colorMap[color] || colorMap.blue

  const content = (
    <div className="bg-white rounded-lg border border-gray-200 p-4 flex items-start gap-3 hover:shadow-sm transition-shadow">
      <div className={`p-2 rounded-lg flex-shrink-0 ${iconColor}`} aria-hidden="true">
        {icon}
      </div>
      <div className="min-w-0">
        <p className="text-sm text-gray-500">{title}</p>
        <p className="text-2xl font-bold text-gray-900 mt-0.5" aria-label={ariaLabel || `${title}: ${value}`}>
          {value}
        </p>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )

  if (linkTo) {
    return <Link to={linkTo} className="block focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg">{content}</Link>
  }
  return content
}

// ---------------------------------------------------------------------------
// Alert summary row
// ---------------------------------------------------------------------------

function AlertSummary({ alerts }: { alerts: CentralDashboard['alerts'] }) {
  const rows = [
    { label: 'Critical', count: alerts.CRITICAL, color: 'text-red-600', bgColor: 'bg-red-50', icon: <XCircle className="w-4 h-4" aria-hidden="true" /> },
    { label: 'High',     count: alerts.HIGH,     color: 'text-orange-600', bgColor: 'bg-orange-50', icon: <AlertTriangle className="w-4 h-4" aria-hidden="true" /> },
    { label: 'Medium',   count: alerts.MEDIUM,   color: 'text-yellow-600', bgColor: 'bg-yellow-50', icon: <AlertCircle className="w-4 h-4" aria-hidden="true" /> },
    { label: 'Low',      count: alerts.LOW,      color: 'text-blue-600', bgColor: 'bg-blue-50', icon: <CheckCircle2 className="w-4 h-4" aria-hidden="true" /> },
  ]

  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {rows.map(({ label, count, color, bgColor, icon }) => (
        <div
          key={label}
          className={`${bgColor} rounded-lg p-3 flex items-center gap-2`}
          role="status"
          aria-label={`${label} alerts: ${count}`}
        >
          <span className={color}>{icon}</span>
          <div>
            <p className={`text-sm font-semibold ${color}`}>{count}</p>
            <p className="text-xs text-gray-500">{label}</p>
          </div>
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------

export function CentralControlDashboard() {
  const [data, setData] = useState<CentralDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const fetchDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await centralControlApi.getDashboard()
      setData(result)
      setLastRefresh(new Date())
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load dashboard.'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDashboard()
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboard, 30_000)
    return () => clearInterval(interval)
  }, [fetchDashboard])

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center h-64" role="status" aria-label="Loading dashboard">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" aria-hidden="true" />
        <span className="ml-3 text-gray-500">Loading dashboard…</span>
      </div>
    )
  }

  if (error && !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700" role="alert">
        <p className="font-medium">Dashboard unavailable</p>
        <p className="text-sm mt-1">{error}</p>
        <button
          onClick={fetchDashboard}
          className="mt-2 text-sm underline hover:no-underline focus:outline-none focus:ring-2 focus:ring-red-500 rounded"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data) return null

  const { restaurants, branches, operations, kitchen, inventory, financial, alerts, issues } = data

  return (
    <main className="space-y-6 p-4 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Central Control Center</h1>
          <p className="text-sm text-gray-500 mt-0.5">{data.organization_name}</p>
        </div>
        <div className="flex items-center gap-2">
          {lastRefresh && (
            <p className="text-xs text-gray-400">
              Updated {lastRefresh.toLocaleTimeString()}
            </p>
          )}
          <button
            onClick={fetchDashboard}
            disabled={loading}
            className="p-2 text-gray-500 hover:text-gray-900 rounded-lg hover:bg-gray-100 
                       focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            aria-label="Refresh dashboard"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          </button>
        </div>
      </div>

      {/* Organization Overview */}
      <section aria-labelledby="overview-heading">
        <h2 id="overview-heading" className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Organization Overview
        </h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <KpiCard
            title="Restaurants"
            value={restaurants.active}
            subtitle={`${restaurants.inactive} inactive`}
            icon={<Building2 className="w-5 h-5" />}
            color="blue"
            linkTo="/central-control/restaurants"
          />
          <KpiCard
            title="Branches"
            value={branches.active}
            subtitle={`${branches.total} total`}
            icon={<GitBranch className="w-5 h-5" />}
            color="blue"
            linkTo="/central-control/branches"
          />
          <KpiCard
            title="Orders Today"
            value={operations.orders_today.toLocaleString()}
            subtitle={`${operations.open_tables} open tables`}
            icon={<ShoppingCart className="w-5 h-5" />}
            color="green"
          />
          <KpiCard
            title="Sales Today"
            value={`₹${Number(operations.sales_today).toLocaleString()}`}
            subtitle={`${operations.open_counters} open counters`}
            icon={<DollarSign className="w-5 h-5" />}
            color="green"
          />
          <KpiCard
            title="Kitchen Pending"
            value={kitchen.pending_orders}
            subtitle={`${kitchen.delayed_orders} delayed`}
            icon={<ChefHat className="w-5 h-5" />}
            color={kitchen.delayed_orders > 0 ? 'orange' : 'green'}
            linkTo="/central-control/alerts?alert_type=KITCHEN_DELAY"
          />
          <KpiCard
            title="Low Stock"
            value={inventory.low_stock_items}
            subtitle={`${inventory.out_of_stock_items} out of stock`}
            icon={<Package className="w-5 h-5" />}
            color={inventory.out_of_stock_items > 0 ? 'red' : inventory.low_stock_items > 0 ? 'orange' : 'green'}
            linkTo="/central-control/alerts?alert_type=LOW_STOCK"
          />
          <KpiCard
            title="Overdue Payables"
            value={financial.overdue_payables}
            subtitle={`${financial.pending_expenses} pending expenses`}
            icon={<CreditCard className="w-5 h-5" />}
            color={financial.overdue_payables > 0 ? 'red' : 'gray'}
            linkTo="/central-control/alerts?alert_type=PAYABLE_OVERDUE"
          />
          <KpiCard
            title="Open Issues"
            value={issues.open}
            subtitle={`${issues.critical} critical`}
            icon={<FileText className="w-5 h-5" />}
            color={issues.critical > 0 ? 'red' : issues.open > 0 ? 'orange' : 'green'}
            linkTo="/central-control/issues"
          />
        </div>
      </section>

      {/* Active Alerts */}
      <section aria-labelledby="alerts-heading">
        <div className="flex items-center justify-between mb-3">
          <h2 id="alerts-heading" className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
            Active Alerts
          </h2>
          <Link
            to="/central-control/alerts"
            className="text-sm text-blue-600 hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
          >
            View all
          </Link>
        </div>
        <AlertSummary alerts={alerts} />
      </section>

      {/* Quick links */}
      <section aria-labelledby="quicklinks-heading">
        <h2 id="quicklinks-heading" className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Quick Navigation
        </h2>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            { to: '/central-control/alerts',       label: 'Alert Center',     icon: <AlertTriangle className="w-4 h-4" aria-hidden="true" /> },
            { to: '/central-control/issues',        label: 'Issue Center',     icon: <FileText className="w-4 h-4" aria-hidden="true" /> },
            { to: '/central-control/system-health', label: 'System Health',    icon: <Activity className="w-4 h-4" aria-hidden="true" /> },
            { to: '/central-control/events',        label: 'Event Timeline',   icon: <RefreshCw className="w-4 h-4" aria-hidden="true" /> },
          ].map(({ to, label, icon }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-2 p-3 bg-white border border-gray-200 rounded-lg 
                         hover:bg-gray-50 hover:shadow-sm transition-all text-sm text-gray-700
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {icon}
              {label}
            </Link>
          ))}
        </div>
      </section>
    </main>
  )
}
