// =============================================================================
// RestaurantFlow — Operations Dashboard
// Phase 19: Advanced POS & Restaurant Operations
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getOperationsDashboard } from '@/services/operations'

interface DashboardData {
  branch_name?: string
  timestamp?: string
  pos?: { active_sessions: number }
  orders?: { open: number; on_hold: number }
  billing?: { pending_payment: number }
  kitchen?: { backlog: number; ready: number }
  tables?: { total: number; occupied: number; available: number }
  current_shift?: { id: string; shift_type: string; started_at: string } | null
}

const StatCard = ({
  label,
  value,
  color = 'brand',
}: {
  label: string
  value: number | string
  color?: string
}) => (
  <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
    <p className="text-xs text-gray-500 uppercase tracking-widest mb-1">{label}</p>
    <p className={`text-3xl font-bold text-${color}-400`}>{value}</p>
  </div>
)

const QuickLink = ({ to, label, icon }: { to: string; label: string; icon: React.ReactNode }) => (
  <Link
    to={to}
    className="flex items-center gap-3 bg-gray-900 hover:bg-gray-800/80 border border-gray-800 rounded-xl p-4 transition-colors"
  >
    <span className="text-brand-400">{icon}</span>
    <span className="text-sm text-gray-200 font-medium">{label}</span>
  </Link>
)

export function OperationsDashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getOperationsDashboard()
      .then((res) => setData(res.data))
      .catch(() => setError('Failed to load dashboard'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-gray-400">Loading operations dashboard…</div>

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Operations</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data?.branch_name ?? 'Branch'} · Phase 19
          </p>
        </div>
        {data?.current_shift ? (
          <span className="inline-flex items-center gap-1.5 text-xs bg-green-500/10 text-green-400 border border-green-500/20 rounded-full px-3 py-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            {data.current_shift.shift_type} shift active
          </span>
        ) : (
          <span className="text-xs text-gray-600 border border-gray-800 rounded-full px-3 py-1">
            No active shift
          </span>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Active POS Sessions" value={data?.pos?.active_sessions ?? 0} color="brand" />
        <StatCard label="Open Orders" value={data?.orders?.open ?? 0} color="yellow" />
        <StatCard label="Held Orders" value={data?.orders?.on_hold ?? 0} color="gray" />
        <StatCard label="Pending Bills" value={data?.billing?.pending_payment ?? 0} color="orange" />
        <StatCard label="Kitchen Backlog" value={data?.kitchen?.backlog ?? 0} color="red" />
        <StatCard label="Ready to Serve" value={data?.kitchen?.ready ?? 0} color="green" />
        <StatCard label="Tables Occupied" value={data?.tables?.occupied ?? 0} color="blue" />
        <StatCard label="Tables Available" value={data?.tables?.available ?? 0} color="green" />
      </div>

      {/* Quick links */}
      <div>
        <h2 className="text-xs text-gray-500 uppercase tracking-widest mb-3">Quick Access</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          <QuickLink to="/operations/pos" label="POS Terminal" icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
          } />
          <QuickLink to="/operations/tables" label="Table Map" icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 10h18M3 14h18M10 10V4m0 16V14M14 10V4m0 16V14" />
            </svg>
          } />
          <QuickLink to="/operations/waiter" label="Waiter View" icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          } />
          <QuickLink to="/operations/cashier" label="Cashier" icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          } />
          <QuickLink to="/operations/shifts" label="Shifts" icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          } />
          <QuickLink to="/kitchen" label="Kitchen" icon={
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
              <path strokeLinecap="round" strokeLinejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0" />
            </svg>
          } />
        </div>
      </div>
    </div>
  )
}
