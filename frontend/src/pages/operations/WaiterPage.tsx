// =============================================================================
// RestaurantFlow — Waiter Operational View
// Phase 19: Advanced POS & Restaurant Operations
// Mobile/tablet-friendly view for waiting staff
// =============================================================================

import { useEffect, useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { getOperationalTables } from '@/services/operations'
import { listOrders } from '@/services/orders'

type Tab = 'tables' | 'orders' | 'ready' | 'bills'

const TabButton = ({ active, onClick, children, badge }: {
  active: boolean; onClick: () => void; children: React.ReactNode; badge?: number
}) => (
  <button
    onClick={onClick}
    className={`relative flex-1 py-2.5 text-sm font-medium transition-colors ${
      active ? 'text-brand-400 border-b-2 border-brand-400' : 'text-gray-500 hover:text-gray-300'
    }`}
  >
    {children}
    {badge !== undefined && badge > 0 && (
      <span className="absolute -top-1 right-1/4 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white flex items-center justify-center">
        {badge}
      </span>
    )}
  </button>
)

export function WaiterPage() {
  const { user } = useAuth()
  const [tab, setTab] = useState<Tab>('tables')
  const [tables, setTables] = useState<any[]>([])
  const [orders, setOrders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    Promise.all([
      getOperationalTables(),
      listOrders({ ...(user?.id != null ? { assigned_waiter: String(user.id) } : {}), status: 'CONFIRMED' }),
    ])
      .then(([t, o]) => {
        setTables(t)
        setOrders((o as any).results ?? o)
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])
  useEffect(() => {
    const id = setInterval(load, 20_000)
    return () => clearInterval(id)
  }, [])

  const myTables = tables.filter(t => t.has_open_session)
  const readyOrders = orders.filter((o: any) => o.kitchen_order?.status === 'READY')
  const pendingBills = orders.filter((o: any) => o.bill?.status === 'FINALIZED')

  return (
    <div className="max-w-lg mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">My Station</h1>
        <button onClick={load} className="text-xs text-gray-500 hover:text-gray-300 border border-gray-800 rounded-lg px-2 py-1">
          Refresh
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-gray-800">
        <TabButton active={tab === 'tables'} onClick={() => setTab('tables')} badge={myTables.length}>
          Tables
        </TabButton>
        <TabButton active={tab === 'orders'} onClick={() => setTab('orders')} badge={orders.length}>
          Orders
        </TabButton>
        <TabButton active={tab === 'ready'} onClick={() => setTab('ready')} badge={readyOrders.length}>
          Ready 🔔
        </TabButton>
        <TabButton active={tab === 'bills'} onClick={() => setTab('bills')} badge={pendingBills.length}>
          Bills
        </TabButton>
      </div>

      {loading && <p className="text-sm text-gray-500 text-center py-8">Loading…</p>}

      {/* Tables tab */}
      {!loading && tab === 'tables' && (
        <div className="space-y-2">
          {myTables.length === 0 && (
            <p className="text-sm text-gray-600 text-center py-8">No occupied tables</p>
          )}
          {myTables.map(t => (
            <div key={t.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-white">Table {t.table_number}</p>
                  <p className="text-xs text-gray-500">{t.section || 'Main'} · {t.guest_count} guests</p>
                </div>
                <span className={`text-xs border rounded-full px-2 py-0.5 ${
                  t.operational_status === 'BILL_PENDING'
                    ? 'border-yellow-500/40 text-yellow-400'
                    : 'border-blue-500/40 text-blue-400'
                }`}>
                  {t.operational_status.replace('_', ' ')}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Orders tab */}
      {!loading && tab === 'orders' && (
        <div className="space-y-2">
          {orders.length === 0 && (
            <p className="text-sm text-gray-600 text-center py-8">No assigned orders</p>
          )}
          {orders.map((o: any) => (
            <div key={o.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-2">
              <div className="flex justify-between items-center">
                <p className="font-semibold text-white">{o.order_number}</p>
                <span className="text-xs text-gray-500">{o.order_type.replace('_', '-')}</span>
              </div>
              {o.table && <p className="text-xs text-gray-500">Table {o.table.table_number}</p>}
              <div className="space-y-1">
                {(o.items ?? []).slice(0, 3).map((item: any, i: number) => (
                  <p key={i} className="text-xs text-gray-400">
                    {item.quantity}× {item.item_name_snapshot}
                  </p>
                ))}
                {(o.items?.length ?? 0) > 3 && (
                  <p className="text-xs text-gray-600">+{o.items.length - 3} more</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Ready tab */}
      {!loading && tab === 'ready' && (
        <div className="space-y-2">
          {readyOrders.length === 0 && (
            <p className="text-sm text-gray-600 text-center py-8">No orders ready to serve</p>
          )}
          {readyOrders.map((o: any) => (
            <div key={o.id} className="bg-green-500/5 border border-green-500/20 rounded-xl p-4">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-green-400">{o.order_number} — READY</p>
                {o.table && <p className="text-xs text-gray-400">Table {o.table.table_number}</p>}
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {(o.items ?? []).map((i: any) => i.item_name_snapshot).join(', ')}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* Bills tab */}
      {!loading && tab === 'bills' && (
        <div className="space-y-2">
          {pendingBills.length === 0 && (
            <p className="text-sm text-gray-600 text-center py-8">No pending bills</p>
          )}
          {pendingBills.map((o: any) => (
            <div key={o.id} className="bg-yellow-500/5 border border-yellow-500/20 rounded-xl p-4">
              <div className="flex justify-between items-center">
                <p className="font-semibold text-yellow-400">Bill Pending</p>
                {o.table && <p className="text-xs text-gray-400">Table {o.table.table_number}</p>}
              </div>
              <p className="text-xs text-gray-500 mt-1">{o.order_number}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
