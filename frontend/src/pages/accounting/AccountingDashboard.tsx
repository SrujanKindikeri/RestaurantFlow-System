// =============================================================================
// RestaurantFlow — Accounting Dashboard
// Phase 13
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getAccountingDashboard, type AccountingDashboard } from '@/services/accounting'
import { useAuth } from '@/contexts/AuthContext'

const fmt = (v: string | number | undefined) =>
  Number(v ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

interface StatCardProps {
  label: string
  value: string | number
  to: string
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info'
  prefix?: string
}

function StatCard({ label, value, to, variant = 'default', prefix = '₹' }: StatCardProps) {
  const colours: Record<string, string> = {
    default: 'text-white',
    success: 'text-green-400',
    warning: 'text-amber-400',
    danger: 'text-red-400',
    info: 'text-blue-400',
  }
  return (
    <Link
      to={to}
      className="bg-gray-800 border border-gray-700 rounded-xl p-5 hover:border-gray-600 transition-colors block"
    >
      <p className="text-xs text-gray-500 uppercase tracking-wider mb-2">{label}</p>
      <p className={`text-2xl font-bold ${colours[variant]}`}>
        {prefix}{typeof value === 'number' ? fmt(value) : value}
      </p>
    </Link>
  )
}

function StatusBadge({ balanced }: { balanced: boolean }) {
  if (balanced) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">
        <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
        BALANCED
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-500/10 text-red-400 border border-red-500/20">
      <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
      IMBALANCED
    </span>
  )
}

export function AccountingDashboard() {
  const { user } = useAuth()
  const [data, setData] = useState<AccountingDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  useEffect(() => {
    if (!restaurantId) {
      setLoading(false)
      return
    }
    getAccountingDashboard(restaurantId)
      .then(setData)
      .catch((e) => setError(e?.response?.data?.detail ?? 'Failed to load accounting dashboard'))
      .finally(() => setLoading(false))
  }, [restaurantId])

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Accounting</h1>
          <p className="text-sm text-gray-500 mt-1">
            Double-entry ledger, chart of accounts, and financial statements
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            to="/accounting/journals/new"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            + New Journal Entry
          </Link>
        </div>
      </div>

      {/* Loading skeleton */}
      {loading && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl p-5 animate-pulse h-24" />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>
      )}

      {!restaurantId && !loading && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 text-amber-400 text-sm">
          No restaurant selected. Please select a restaurant to view accounting data.
        </div>
      )}

      {data && (
        <>
          {/* Accounting health */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 flex flex-wrap items-center gap-6">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Trial Balance</p>
              <StatusBadge balanced={data.trial_balance_balanced} />
              {!data.trial_balance_balanced && (
                <p className="text-xs text-red-400 mt-1">
                  Variance: ₹{fmt(data.trial_balance_variance)}
                </p>
              )}
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Balance Sheet</p>
              <StatusBadge balanced={data.balance_sheet_balanced} />
            </div>
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Open Periods</p>
              <span className={`text-2xl font-bold ${data.open_periods_count === 0 ? 'text-amber-400' : 'text-white'}`}>
                {data.open_periods_count}
              </span>
            </div>
          </div>

          {/* P&L metrics */}
          <div>
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
              Profit & Loss
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard label="Total Revenue" value={fmt(data.total_revenue)} to="/accounting/profit-loss" variant="success" />
              <StatCard label="Cost of Goods Sold" value={fmt(data.total_cogs)} to="/accounting/profit-loss" variant="warning" />
              <StatCard label="Gross Profit" value={fmt(data.gross_profit)} to="/accounting/profit-loss"
                variant={Number(data.gross_profit) >= 0 ? 'success' : 'danger'} />
              <StatCard label="Operating Profit" value={fmt(data.operating_profit)} to="/accounting/profit-loss"
                variant={Number(data.operating_profit) >= 0 ? 'success' : 'danger'} />
            </div>
          </div>

          {/* Balance Sheet metrics */}
          <div>
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
              Balance Sheet
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              <StatCard label="Total Assets" value={fmt(data.total_assets)} to="/accounting/balance-sheet" variant="info" />
              <StatCard label="Total Liabilities" value={fmt(data.total_liabilities)} to="/accounting/balance-sheet" variant="warning" />
              <StatCard label="Total Equity" value={fmt(data.total_equity)} to="/accounting/balance-sheet" variant="success" />
            </div>
          </div>

          {/* Quick links */}
          <div>
            <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
              Quick Access
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Chart of Accounts', to: '/accounting/accounts' },
                { label: 'Journal Entries', to: '/accounting/journals' },
                { label: 'General Ledger', to: '/accounting/general-ledger' },
                { label: 'Trial Balance', to: '/accounting/trial-balance' },
                { label: 'Profit & Loss', to: '/accounting/profit-loss' },
                { label: 'Balance Sheet', to: '/accounting/balance-sheet' },
                { label: 'Cash Flow', to: '/accounting/cash-flow' },
                { label: 'Periods', to: '/accounting/periods' },
              ].map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="bg-gray-800 border border-gray-700 hover:border-gray-600 rounded-lg p-4 text-sm text-gray-300 hover:text-white transition-colors text-center"
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
