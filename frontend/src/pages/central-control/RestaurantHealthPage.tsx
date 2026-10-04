// =============================================================================
// RestaurantFlow — Restaurant Health Page
// Phase 15
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { centralControlApi, RestaurantHealth } from '@/services/centralControl'
import { RefreshCw, CheckCircle2, AlertTriangle, XCircle, WifiOff, HelpCircle } from 'lucide-react'

function HealthStatusBadge({ status }: { status: RestaurantHealth['health_status'] }) {
  const configs = {
    HEALTHY:  { label: 'Healthy',  icon: <CheckCircle2 className="w-4 h-4" aria-hidden="true" />, className: 'bg-green-100 text-green-800'  },
    WARNING:  { label: 'Warning',  icon: <AlertTriangle className="w-4 h-4" aria-hidden="true" />, className: 'bg-yellow-100 text-yellow-800' },
    CRITICAL: { label: 'Critical', icon: <XCircle className="w-4 h-4" aria-hidden="true" />,       className: 'bg-red-100 text-red-800'      },
    OFFLINE:  { label: 'Offline',  icon: <WifiOff className="w-4 h-4" aria-hidden="true" />,       className: 'bg-gray-100 text-gray-600'    },
    UNKNOWN:  { label: 'Unknown',  icon: <HelpCircle className="w-4 h-4" aria-hidden="true" />,    className: 'bg-gray-50 text-gray-500'     },
  }
  const { label, icon, className } = configs[status] || configs.UNKNOWN
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${className}`}
      role="status"
      aria-label={`Health status: ${label}`}
    >
      {icon}
      {label}
    </span>
  )
}

function MetricCell({ value, warning = false, critical = false }: { value: number | string; warning?: boolean; critical?: boolean }) {
  const color = critical ? 'text-red-600 font-semibold' : warning ? 'text-orange-600 font-medium' : 'text-gray-700'
  return <span className={color}>{value}</span>
}

export function RestaurantHealthPage() {
  const [restaurants, setRestaurants] = useState<RestaurantHealth[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await centralControlApi.getRestaurantHealth()
      setRestaurants(res.results)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return (
    <main className="p-4 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Restaurant Health</h1>
          <p className="text-sm text-gray-500 mt-0.5">Health status across all accessible restaurants</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg 
                     hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          aria-label="Refresh restaurant health"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm mb-4" role="alert">
          {error}
        </div>
      )}

      {loading && restaurants.length === 0 ? (
        <div className="flex items-center justify-center h-32" role="status" aria-label="Loading">
          <div className="animate-spin h-6 w-6 border-b-2 border-blue-600 rounded-full" aria-hidden="true" />
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto">
          <table className="w-full text-sm" aria-label="Restaurant health overview">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                <th scope="col" className="px-4 py-3 text-left">Restaurant</th>
                <th scope="col" className="px-4 py-3 text-left">Status</th>
                <th scope="col" className="px-4 py-3 text-right">Branches</th>
                <th scope="col" className="px-4 py-3 text-right">Sales Today</th>
                <th scope="col" className="px-4 py-3 text-right">Orders</th>
                <th scope="col" className="px-4 py-3 text-right">Kitchen</th>
                <th scope="col" className="px-4 py-3 text-right">Inventory</th>
                <th scope="col" className="px-4 py-3 text-right">Alerts</th>
                <th scope="col" className="px-4 py-3 text-right">Issues</th>
                <th scope="col" className="px-4 py-3 text-left">Health</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {restaurants.length === 0 && (
                <tr>
                  <td colSpan={10} className="px-4 py-8 text-center text-gray-400">No restaurants found.</td>
                </tr>
              )}
              {restaurants.map(r => (
                <tr key={r.restaurant_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{r.restaurant_name}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${r.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                      {r.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <MetricCell
                      value={`${r.active_branch_count}/${r.branch_count}`}
                      warning={r.active_branch_count < r.branch_count}
                    />
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">
                    ₹{Number(r.sales_today).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">{r.orders_today}</td>
                  <td className="px-4 py-3 text-right">
                    <MetricCell
                      value={`${r.delayed_kitchen_orders}/${r.pending_kitchen_orders}`}
                      warning={r.delayed_kitchen_orders > 0}
                      critical={r.delayed_kitchen_orders > 5}
                    />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <MetricCell
                      value={`${r.out_of_stock_items} OOS`}
                      warning={r.low_stock_items > 0}
                      critical={r.out_of_stock_items > 0}
                    />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <MetricCell
                      value={r.unresolved_alerts}
                      warning={r.unresolved_alerts > 0}
                      critical={r.unresolved_critical_alerts > 0}
                    />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <MetricCell
                      value={r.open_issues}
                      warning={r.open_issues > 0}
                      critical={r.critical_issues > 0}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <HealthStatusBadge status={r.health_status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}
