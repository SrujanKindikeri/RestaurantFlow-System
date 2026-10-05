// =============================================================================
// RestaurantFlow — CRM Dashboard
// Phase 17
// =============================================================================

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import crmApi, { CRMDashboardKPIs, Customer } from '@/services/crm'

function KPICard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  )
}

export function CRMDashboard() {
  const [kpis, setKpis] = useState<CRMDashboardKPIs | null>(null)
  const [topCustomers, setTopCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    crmApi.getDashboard()
      .then(r => {
        setKpis(r.data.kpis)
        setTopCustomers(r.data.top_customers)
      })
      .catch(() => setError('Failed to load CRM dashboard.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-12 text-center text-gray-400 text-sm">Loading CRM dashboard…</div>
  if (error) return <div className="p-12 text-center text-red-500 text-sm">{error}</div>

  return (
    <div className="p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">CRM Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Customer intelligence overview</p>
        </div>
        <Link
          to="/customers"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          View All Customers
        </Link>
      </div>

      {/* KPI Grid */}
      {kpis && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard label="Total Customers" value={kpis.total_customers?.toLocaleString() ?? '—'} />
          <KPICard label="New (30d)" value={kpis.new_customers?.toLocaleString() ?? '—'} />
          <KPICard label="Returning" value={kpis.returning_customers?.toLocaleString() ?? '—'} />
          <KPICard label="Inactive (90d)" value={kpis.inactive_customers?.toLocaleString() ?? '—'}
            sub="No order in 90+ days" />
          <KPICard
            label="Avg Lifetime Spend"
            value={
              kpis.avg_lifetime_spend
                ? parseFloat(kpis.avg_lifetime_spend).toLocaleString('en-IN', {
                    style: 'currency', currency: 'INR', minimumFractionDigits: 0,
                  })
                : '—'
            }
          />
          <KPICard label="Avg Visits" value={kpis.avg_visits?.toFixed(1) ?? '—'} />
          <KPICard label="Avg Orders" value={kpis.avg_orders?.toFixed(1) ?? '—'} />
        </div>
      )}

      {/* Quick links */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800 mb-4">CRM Modules</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {[
            { label: 'Customers', to: '/customers', icon: '👥' },
            { label: 'Feedback', to: '/crm/feedback', icon: '⭐' },
            { label: 'Segments', to: '/crm/segments', icon: '🎯' },
            { label: 'Rewards', to: '/crm/rewards', icon: '🎁' },
            { label: 'Loyalty', to: '/crm/loyalty', icon: '💎' },
          ].map(item => (
            <Link
              key={item.to}
              to={item.to}
              className="flex items-center gap-3 p-4 bg-white border border-gray-200 rounded-xl hover:border-blue-300 hover:bg-blue-50 transition-colors"
            >
              <span className="text-2xl">{item.icon}</span>
              <span className="text-sm font-medium text-gray-700">{item.label}</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Top Customers */}
      {topCustomers.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Top Customers</h2>
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">#</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Customer</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Orders</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Lifetime Spend</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Last Visit</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {topCustomers.map((c, i) => (
                  <tr key={c.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-gray-400 text-xs">{i + 1}</td>
                    <td className="px-4 py-3">
                      <Link to={`/customers/${c.id}`} className="font-medium text-blue-600 hover:underline">
                        {c.display_name}
                      </Link>
                      <p className="text-xs text-gray-400">{c.customer_number}</p>
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700">{c.total_orders}</td>
                    <td className="px-4 py-3 text-right text-gray-700">
                      {parseFloat(c.lifetime_spend).toLocaleString('en-IN', {
                        style: 'currency', currency: 'INR', minimumFractionDigits: 0,
                      })}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {c.last_visit_at ? new Date(c.last_visit_at).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
