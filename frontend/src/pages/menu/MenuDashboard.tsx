// =============================================================================
// RestaurantFlow — Menu Dashboard
// Phase 5
// =============================================================================

import { Link } from 'react-router-dom'
import { useMenuDashboard } from '@/hooks/useMenu'
import { PageHeader } from '@/components/ui/PageHeader'

function StatCard({
  label,
  value,
  color = 'text-gray-200',
}: {
  label: string
  value: number
  color?: string
}) {
  return (
    <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-5 py-4 text-center">
      <p className={`text-3xl font-semibold ${color}`}>{value}</p>
      <p className="text-xs text-gray-600 mt-1">{label}</p>
    </div>
  )
}

export function MenuDashboard() {
  const { data, isLoading, isError } = useMenuDashboard()

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Menu"
        description="Manage categories, items, pricing, availability, and taxes."
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Menu' }]}
        actions={
          <div className="flex items-center gap-2">
            <Link
              to="/menu/items"
              className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-medium border border-brand-500/50 transition-colors"
            >
              + Add Item
            </Link>
          </div>
        }
      />

      {isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-20 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
            ))}
          </div>
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load menu dashboard.
        </div>
      )}

      {data && (
        <div className="space-y-8">
          {/* Items summary */}
          <section>
            <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3">
              Menu Overview
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              <StatCard label="Categories" value={data.categories.active} color="text-brand-400" />
              <StatCard label="Total Items" value={data.items.total} color="text-gray-200" />
              <StatCard label="Active Items" value={data.items.active} color="text-green-400" />
              <StatCard label="Available" value={data.items.available} color="text-green-400" />
              <StatCard label="Unavailable" value={data.items.unavailable} color="text-yellow-400" />
            </div>
          </section>

          {/* Quick actions */}
          <section>
            <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3">
              Manage
            </h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {[
                {
                  label: 'Categories',
                  to: '/menu/categories',
                  desc: `${data.categories.active} active`,
                  icon: '📂',
                },
                {
                  label: 'Menu Items',
                  to: '/menu/items',
                  desc: `${data.items.active} active`,
                  icon: '🍽️',
                },
                {
                  label: 'Pricing',
                  to: '/menu/pricing',
                  desc: 'Branch-specific prices',
                  icon: '₹',
                },
                {
                  label: 'Availability',
                  to: '/menu/availability',
                  desc: 'Branch availability',
                  icon: '📍',
                },
                {
                  label: 'Tax Rates',
                  to: '/menu/tax-rates',
                  desc: 'Tax configuration',
                  icon: '%',
                },
              ].map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className="rounded-xl bg-gray-900/60 border border-gray-800 hover:border-gray-700 px-5 py-4 flex items-start gap-4 transition-colors group"
                >
                  <span className="text-2xl">{item.icon}</span>
                  <div>
                    <p className="text-sm font-medium text-gray-200 group-hover:text-brand-400 transition-colors">
                      {item.label}
                    </p>
                    <p className="text-xs text-gray-600 mt-0.5">{item.desc}</p>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          {/* Branch availability breakdown */}
          {data.branches.length > 0 && (
            <section>
              <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3">
                Branch Availability
              </h2>
              <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-hidden">
                <table className="w-full text-sm" role="table">
                  <thead>
                    <tr className="border-b border-gray-800">
                      <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">
                        Branch
                      </th>
                      <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden sm:table-cell">
                        Restaurant
                      </th>
                      <th className="text-right px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">
                        Available Items
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.branches.map((branch) => (
                      <tr
                        key={branch.id}
                        className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
                      >
                        <td className="px-4 py-3 text-gray-200 text-sm">{branch.name}</td>
                        <td className="px-4 py-3 text-gray-500 text-xs hidden sm:table-cell">
                          {branch.restaurant_name}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <span className="font-mono text-green-400 text-sm font-medium">
                            {branch.available_items}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  )
}
