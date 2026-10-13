// =============================================================================
// RestaurantFlow — Cashier Operational Dashboard
// Phase 19: Advanced POS & Restaurant Operations
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getOperationsDashboard, getPOSSessions, holdOrder } from '@/services/operations'
import { listOrders } from '@/services/orders'

export function CashierPage() {
  const [dashboard, setDashboard] = useState<any>(null)
  const [session, setSession] = useState<any>(null)
  const [heldOrders, setHeldOrders] = useState<any[]>([])
  const [pendingBills, setPendingBills] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const [dashRes, sessionRes, ordersRes] = await Promise.all([
        getOperationsDashboard(),
        getPOSSessions(),
        listOrders({ status: 'ON_HOLD' }),
      ])
      setDashboard(dashRes.data)
      setSession(sessionRes.data.find((s: any) => s.status === 'ACTIVE'))
      setHeldOrders(ordersRes.data.results ?? ordersRes.data)
    } catch {
      setError('Failed to load cashier data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="p-8 text-gray-400">Loading cashier dashboard…</div>

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Cashier Dashboard</h1>
          <p className="text-sm text-gray-500">{dashboard?.branch_name ?? 'Branch'}</p>
        </div>
        <button onClick={load} className="text-xs bg-gray-800 border border-gray-700 text-gray-400 hover:text-white rounded-lg px-3 py-1.5">
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      {/* Session banner */}
      <div className={`rounded-xl p-4 border ${session ? 'border-green-500/20 bg-green-500/5' : 'border-yellow-500/20 bg-yellow-500/5'}`}>
        {session ? (
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-400">Counter Session Active</p>
              <p className="text-xs text-gray-500 mt-0.5">Counter: {session.counter_code} · Since {new Date(session.started_at).toLocaleTimeString()}</p>
            </div>
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          </div>
        ) : (
          <div>
            <p className="text-sm font-medium text-yellow-400">No Active POS Session</p>
            <Link to="/counter-sessions" className="text-xs text-gray-500 underline mt-0.5 block">Open a counter session</Link>
          </div>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Open Orders" value={dashboard?.orders?.open ?? 0} />
        <StatCard label="Held Orders" value={dashboard?.orders?.on_hold ?? 0} color="yellow" />
        <StatCard label="Pending Bills" value={dashboard?.billing?.pending_payment ?? 0} color="orange" />
        <StatCard label="Kitchen Ready" value={dashboard?.kitchen?.ready ?? 0} color="green" />
      </div>

      {/* Quick actions */}
      <div>
        <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <QuickAction to="/operations/pos" label="New Order" icon="➕" />
          <QuickAction to="/billing/bills" label="Pending Bills" icon="🧾" />
          <QuickAction to="/payments" label="Payments" icon="💳" />
          <QuickAction to="/operations/shifts" label="Shifts" icon="🕐" />
        </div>
      </div>

      {/* Held orders */}
      <div>
        <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">Held Orders</h2>
        {heldOrders.length === 0 ? (
          <p className="text-sm text-gray-600">No held orders</p>
        ) : (
          <div className="space-y-2">
            {heldOrders.map((o: any) => (
              <div key={o.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-white">{o.order_number}</p>
                  <p className="text-xs text-gray-500">{o.order_type.replace('_', '-')} · {o.items?.length ?? 0} items</p>
                </div>
                <Link
                  to={`/operations/pos?resume=${o.id}`}
                  className="text-xs bg-brand-500/10 text-brand-400 border border-brand-500/20 rounded-lg px-3 py-1.5 hover:bg-brand-500/20"
                >
                  Resume
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

const StatCard = ({ label, value, color = 'brand' }: { label: string; value: number | string; color?: string }) => (
  <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
    <p className="text-xs text-gray-500 mb-1">{label}</p>
    <p className={`text-2xl font-bold text-${color}-400`}>{value}</p>
  </div>
)

const QuickAction = ({ to, label, icon }: { to: string; label: string; icon: string }) => (
  <Link
    to={to}
    className="bg-gray-900 hover:bg-gray-800 border border-gray-800 rounded-xl p-4 flex flex-col items-center gap-2 text-center transition-colors"
  >
    <span className="text-2xl">{icon}</span>
    <span className="text-xs text-gray-300">{label}</span>
  </Link>
)
