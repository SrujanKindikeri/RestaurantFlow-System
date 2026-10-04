// =============================================================================
// RestaurantFlow — Reporting Dashboard
// Phase 14: Main analytics dashboard with KPI cards, charts, top items
// =============================================================================

import { useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { useDashboard, useSalesTrend, useTopSellingItems, useCategoryPerformance, usePaymentMethods } from '@/hooks/useReporting'
import { getDateRange, formatCurrency, formatGrowth, formatSeconds } from '@/utils/reportingDates'
import type { DatePreset } from '@/utils/reportingDates'
import type { ReportFilters } from '@/services/reporting'

// ---------------------------------------------------------------------------
// Date range preset selector
// ---------------------------------------------------------------------------
const DATE_PRESETS: { value: DatePreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: 'yesterday', label: 'Yesterday' },
  { value: 'last_7_days', label: 'Last 7 days' },
  { value: 'last_30_days', label: 'Last 30 days' },
  { value: 'this_month', label: 'This month' },
  { value: 'prev_month', label: 'Prev month' },
]

const CHART_COLORS = ['#6366f1', '#22d3ee', '#f59e0b', '#10b981', '#f43f5e', '#a78bfa']

// ---------------------------------------------------------------------------
// KPI Card
// ---------------------------------------------------------------------------
function KPICard({
  label, value, sub, growth, color = 'default', loading = false,
}: {
  label: string
  value: string
  sub?: string
  growth?: { label: string; positive: boolean }
  color?: 'default' | 'green' | 'blue' | 'purple' | 'yellow' | 'red'
  loading?: boolean
}) {
  const valueColors = {
    default: 'text-white',
    green: 'text-emerald-400',
    blue: 'text-blue-400',
    purple: 'text-purple-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
  }
  return (
    <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-5 py-4">
      <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">{label}</p>
      {loading ? (
        <div className="h-7 w-20 rounded bg-gray-800 animate-pulse mb-1" />
      ) : (
        <p className={`text-2xl font-semibold ${valueColors[color]}`}>{value}</p>
      )}
      {sub && <p className="mt-0.5 text-xs text-gray-600">{sub}</p>}
      {growth && !loading && (
        <p className={`mt-1 text-xs font-medium ${growth.positive ? 'text-emerald-400' : 'text-red-400'}`}>
          {growth.label} vs prev period
        </p>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Section header
// ---------------------------------------------------------------------------
function SectionHeader({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h2 className="text-xs font-semibold text-gray-600 uppercase tracking-widest">{title}</h2>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Empty / Error / Loading states
// ---------------------------------------------------------------------------
function ChartSkeleton() {
  return <div className="h-48 rounded-lg bg-gray-800 animate-pulse" />
}

function EmptyChart({ message = 'No data for this period' }: { message?: string }) {
  return (
    <div className="h-48 flex items-center justify-center rounded-lg border border-gray-800 bg-gray-900/40">
      <p className="text-xs text-gray-600">{message}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Dashboard
// ---------------------------------------------------------------------------
export function ReportingDashboard() {
  const [preset, setPreset] = useState<DatePreset>('today')
  const dateRange = getDateRange(preset)
  const filters: ReportFilters = {
    date_from: dateRange.date_from,
    date_to: dateRange.date_to,
  }

  const { data: dashboard, isLoading: dashLoading, isError: dashError } = useDashboard(filters)
  const { data: trendData, isLoading: trendLoading } = useSalesTrend({ ...filters, granularity: 'daily' })
  const { data: topItems, isLoading: topLoading } = useTopSellingItems({ ...filters, limit: 8, sort_by: 'revenue' })
  const { data: categories, isLoading: catLoading } = useCategoryPerformance(filters)
  const { data: methods, isLoading: methodsLoading } = usePaymentMethods(filters)

  const kpis = dashboard
  const trendRows = trendData?.data ?? []
  const topRows = topItems?.data ?? []
  const catRows = categories?.data ?? []
  const methodRows = methods?.data ?? []

  const growth_today = kpis?.sales?.today_vs_yesterday_growth
    ? formatGrowth(kpis.sales.today_vs_yesterday_growth)
    : undefined

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">Operational and financial insights for your restaurant</p>
        </div>

        {/* Date range selector */}
        <div className="flex gap-1.5 flex-wrap">
          {DATE_PRESETS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setPreset(opt.value)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                preset === opt.value
                  ? 'bg-brand-500/20 border-brand-500/40 text-brand-400'
                  : 'bg-gray-900/60 border-gray-800 text-gray-500 hover:text-gray-300 hover:border-gray-700'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {dashError && (
        <div className="rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-3 text-sm text-red-400">
          Failed to load dashboard data. Please check your connection and try again.
        </div>
      )}

      {/* Sales KPI cards */}
      <section aria-labelledby="sales-kpi-heading">
        <SectionHeader title="Sales" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <KPICard
            label="Net Sales"
            value={formatCurrency(kpis?.sales?.today_net_sales)}
            growth={growth_today}
            color="green"
            loading={dashLoading}
          />
          <KPICard
            label="Bills"
            value={String(kpis?.sales?.today_bill_count ?? '—')}
            loading={dashLoading}
          />
          <KPICard
            label="Avg Bill"
            value={formatCurrency(kpis?.sales?.today_average_bill_value)}
            loading={dashLoading}
          />
          <KPICard
            label="Orders"
            value={String(kpis?.orders?.today_total_orders ?? '—')}
            color="blue"
            loading={dashLoading}
          />
          <KPICard
            label="Avg Order"
            value={formatCurrency(kpis?.orders?.today_average_order_value)}
            loading={dashLoading}
          />
          <KPICard
            label="Collected"
            value={formatCurrency(kpis?.payments?.today_total_collected)}
            color="purple"
            loading={dashLoading}
          />
        </div>
      </section>

      {/* Operations KPI */}
      <section>
        <SectionHeader title="Operations" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <KPICard
            label="Kitchen Orders"
            value={String(kpis?.kitchen?.today_orders_received ?? '—')}
            sub={`${kpis?.kitchen?.today_orders_ready ?? 0} ready`}
            color="blue"
            loading={dashLoading}
          />
          <KPICard
            label="Avg Prep Time"
            value={formatSeconds(kpis?.kitchen?.today_avg_prep_time_seconds)}
            sub="kitchen preparation"
            loading={dashLoading}
          />
          <KPICard
            label="Low Stock"
            value={String(kpis?.inventory?.low_stock_count ?? '—')}
            color="yellow"
            loading={dashLoading}
          />
          <KPICard
            label="Out of Stock"
            value={String(kpis?.inventory?.out_of_stock_count ?? '—')}
            color="red"
            loading={dashLoading}
          />
        </div>
      </section>

      {/* Sales Trend Chart */}
      <section className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
        <SectionHeader title="Sales Trend" />
        {trendLoading ? (
          <ChartSkeleton />
        ) : trendRows.length === 0 ? (
          <EmptyChart />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendRows} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
              <XAxis
                dataKey="date"
                tick={{ fill: '#6b7280', fontSize: 11 }}
                tickFormatter={(d: string) => d.slice(5)}
              />
              <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickFormatter={(v: number) => `₹${(v/1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                labelStyle={{ color: '#9ca3af', fontSize: 12 }}
                formatter={(v: number) => [`₹${v.toLocaleString()}`, 'Net Sales']}
              />
              <Line
                type="monotone" dataKey="net_sales" name="Net Sales"
                stroke="#6366f1" strokeWidth={2} dot={false} activeDot={{ r: 4 }}
              />
              <Line
                type="monotone" dataKey="bill_count" name="Bills"
                stroke="#22d3ee" strokeWidth={1.5} dot={false} yAxisId={undefined}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </section>

      {/* Two columns: Top Items + Category Pie */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Top Selling Items */}
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
          <SectionHeader title="Top Selling Items" />
          {topLoading ? (
            <ChartSkeleton />
          ) : topRows.length === 0 ? (
            <EmptyChart message="No sales data for this period" />
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={topRows} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }}
                  tickFormatter={(v: number) => `₹${(v/1000).toFixed(0)}K`} />
                <YAxis type="category" dataKey="menu_item_name" tick={{ fill: '#d1d5db', fontSize: 11 }}
                  width={110} />
                <Tooltip
                  contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                  formatter={(v: number) => [`₹${v.toLocaleString()}`, 'Revenue']}
                />
                <Bar dataKey="net_revenue" fill="#6366f1" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Category Performance Pie */}
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
          <SectionHeader title="Category Sales" />
          {catLoading ? (
            <ChartSkeleton />
          ) : catRows.length === 0 ? (
            <EmptyChart />
          ) : (
            <div className="flex items-center gap-4">
              <ResponsiveContainer width="55%" height={200}>
                <PieChart>
                  <Pie
                    data={catRows}
                    dataKey="net_revenue"
                    nameKey="category"
                    cx="50%" cy="50%"
                    innerRadius={55} outerRadius={90}
                    paddingAngle={2}
                  >
                    {catRows.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 8 }}
                    formatter={(v: number) => [`₹${v.toLocaleString()}`, '']}
                  />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {catRows.slice(0, 6).map((r, i) => (
                  <div key={r.category} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
                      />
                      <span className="text-xs text-gray-400 truncate max-w-[90px]">{r.category}</span>
                    </div>
                    <span className="text-xs text-gray-500">{parseFloat(r.sales_percentage).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Payment methods + Kitchen/Inventory row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">

        {/* Payment Methods */}
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
          <SectionHeader title="Payment Methods" />
          {methodsLoading ? (
            <ChartSkeleton />
          ) : methodRows.length === 0 ? (
            <EmptyChart />
          ) : (
            <div className="space-y-3">
              {methodRows.map((r, i) => (
                <div key={r.payment_method} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-400">{r.payment_method}</span>
                    <span className="text-gray-300">{parseFloat(r.percentage).toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-800 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full transition-all"
                      style={{
                        width: `${Math.min(parseFloat(r.percentage), 100)}%`,
                        background: CHART_COLORS[i % CHART_COLORS.length],
                      }}
                    />
                  </div>
                  <p className="text-xs text-gray-600">{formatCurrency(r.total)} · {r.count} txns</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Kitchen KPIs */}
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
          <SectionHeader title="Kitchen" />
          <div className="space-y-4">
            {[
              { label: 'Orders Received', value: kpis?.kitchen?.today_orders_received },
              { label: 'Orders Ready', value: kpis?.kitchen?.today_orders_ready },
              { label: 'Orders Pending', value: kpis?.kitchen?.today_orders_pending },
              { label: 'Avg Prep Time', value: formatSeconds(kpis?.kitchen?.today_avg_prep_time_seconds) },
            ].map(item => (
              <div key={item.label} className="flex justify-between items-center">
                <span className="text-xs text-gray-500">{item.label}</span>
                <span className="text-sm font-medium text-gray-200">
                  {dashLoading ? '—' : (item.value ?? '—')}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Financial alerts */}
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 p-5">
          <SectionHeader title="Financials" />
          <div className="space-y-4">
            {[
              { label: 'Monthly Expenses', value: formatCurrency(kpis?.financials?.monthly_expenses) },
              { label: 'Outstanding Payables', value: formatCurrency(kpis?.financials?.outstanding_payables) },
              { label: 'Overdue Payables', value: formatCurrency(kpis?.financials?.overdue_payables), warn: true },
              { label: 'Refunds Today', value: formatCurrency(kpis?.payments?.today_refund_amount) },
            ].map(item => (
              <div key={item.label} className="flex justify-between items-center">
                <span className="text-xs text-gray-500">{item.label}</span>
                <span className={`text-sm font-medium ${item.warn ? 'text-red-400' : 'text-gray-200'}`}>
                  {dashLoading ? '—' : item.value}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
