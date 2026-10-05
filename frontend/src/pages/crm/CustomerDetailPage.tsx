// =============================================================================
// RestaurantFlow — Customer Detail Page
// Phase 17
// =============================================================================

import { useState, useEffect } from 'react'
import { useParams, NavLink } from 'react-router-dom'
import crmApi, { Customer, LoyaltyAccount, CustomerFeedback, CustomerVisit } from '@/services/crm'

type Tab = 'overview' | 'orders' | 'visits' | 'loyalty' | 'feedback' | 'preferences' | 'consents'

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex justify-between py-2 border-b border-gray-100 last:border-0">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm text-gray-900 font-medium">{value ?? '—'}</span>
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-semibold text-gray-900 mt-1">{value}</p>
    </div>
  )
}

export function CustomerDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [customer, setCustomer] = useState<Customer | null>(null)
  const [loyalty, setLoyalty] = useState<LoyaltyAccount[]>([])
  const [feedback, setFeedback] = useState<CustomerFeedback[]>([])
  const [visits, setVisits] = useState<CustomerVisit[]>([])
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    Promise.all([
      crmApi.getCustomer(id),
      crmApi.getCustomerLoyalty(id),
    ])
      .then(([custRes, loyaltyRes]) => {
        setCustomer(custRes.data)
        setLoyalty(loyaltyRes.data)
      })
      .catch(() => setError('Failed to load customer details.'))
      .finally(() => setLoading(false))
  }, [id])

  useEffect(() => {
    if (!id || activeTab !== 'feedback') return
    crmApi.getCustomerFeedback(id).then(r => setFeedback(r.data.results ?? []))
  }, [id, activeTab])

  useEffect(() => {
    if (!id || activeTab !== 'visits') return
    crmApi.getCustomerVisits(id).then(r => setVisits(r.data.results ?? []))
  }, [id, activeTab])

  if (loading) return <div className="p-12 text-center text-gray-400 text-sm">Loading…</div>
  if (error || !customer) return (
    <div className="p-12 text-center text-red-500 text-sm">{error || 'Customer not found.'}</div>
  )

  const totalLoyaltyPoints = loyalty.reduce((s, a) => s + a.points_balance, 0)

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview',     label: 'Overview' },
    { id: 'orders',       label: 'Orders' },
    { id: 'visits',       label: 'Visits' },
    { id: 'loyalty',      label: 'Loyalty' },
    { id: 'feedback',     label: 'Feedback' },
    { id: 'preferences',  label: 'Preferences' },
    { id: 'consents',     label: 'Consents' },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">{customer.display_name}</h1>
          <p className="text-sm text-gray-400 mt-0.5">{customer.customer_number}</p>
          <div className="flex gap-2 mt-2">
            {customer.is_blocked && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">Blocked</span>
            )}
            {!customer.is_active && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">Inactive</span>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-400">Loyalty Points</p>
          <p className="text-3xl font-bold text-blue-600">{totalLoyaltyPoints.toLocaleString()}</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Orders" value={customer.total_orders} />
        <StatCard label="Total Visits" value={customer.total_visits} />
        <StatCard
          label="Lifetime Spend"
          value={parseFloat(customer.lifetime_spend).toLocaleString('en-IN', {
            style: 'currency', currency: 'INR', minimumFractionDigits: 0,
          })}
        />
        <StatCard
          label="Avg Order Value"
          value={
            customer.total_orders > 0
              ? (parseFloat(customer.lifetime_spend) / customer.total_orders).toLocaleString('en-IN', {
                  style: 'currency', currency: 'INR', minimumFractionDigits: 0,
                })
              : '—'
          }
        />
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-1 -mb-px overflow-x-auto">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeTab === t.id
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'overview' && (
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Contact Information</h3>
              <InfoRow label="Phone" value={customer.phone || customer.masked_phone} />
              <InfoRow label="Email" value={customer.email || customer.masked_email} />
              <InfoRow label="Date of Birth" value={customer.date_of_birth} />
              <InfoRow label="Gender" value={customer.gender} />
              <InfoRow label="Language" value={customer.preferred_language} />
            </div>
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Activity</h3>
              <InfoRow
                label="First Order"
                value={customer.first_order_at ? new Date(customer.first_order_at).toLocaleDateString() : undefined}
              />
              <InfoRow
                label="Last Order"
                value={customer.last_order_at ? new Date(customer.last_order_at).toLocaleDateString() : undefined}
              />
              <InfoRow
                label="Last Visit"
                value={customer.last_visit_at ? new Date(customer.last_visit_at).toLocaleDateString() : undefined}
              />
              <InfoRow
                label="Member Since"
                value={new Date(customer.created_at).toLocaleDateString()}
              />
            </div>
            {customer.notes && (
              <div className="md:col-span-2 bg-yellow-50 border border-yellow-200 rounded-xl p-5">
                <h3 className="text-sm font-semibold text-yellow-800 mb-2">Notes</h3>
                <p className="text-sm text-yellow-700">{customer.notes}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'loyalty' && (
          <div className="space-y-4">
            {loyalty.length === 0 ? (
              <div className="text-center text-gray-400 text-sm py-8">No loyalty accounts.</div>
            ) : (
              loyalty.map(acc => (
                <div key={acc.id} className="bg-white border border-gray-200 rounded-xl p-5">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="font-semibold text-gray-900">{acc.program_name}</h3>
                      <p className="text-xs text-gray-400 mt-0.5">
                        Earned: {acc.lifetime_points_earned.toLocaleString()} pts · 
                        Redeemed: {acc.lifetime_points_redeemed.toLocaleString()} pts
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-400">Balance</p>
                      <p className="text-2xl font-bold text-blue-600">{acc.points_balance.toLocaleString()}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'feedback' && (
          <div className="space-y-3">
            {feedback.length === 0 ? (
              <div className="text-center text-gray-400 text-sm py-8">No feedback yet.</div>
            ) : (
              feedback.map(fb => (
                <div key={fb.id} className="bg-white border border-gray-200 rounded-xl p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">
                        {'★'.repeat(fb.rating)}{'☆'.repeat(5 - fb.rating)}
                      </span>
                      <span className="text-sm text-gray-500">{fb.branch_name}</span>
                    </div>
                    <span className="text-xs text-gray-400">
                      {new Date(fb.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {fb.comment && (
                    <p className="text-sm text-gray-700 mt-2">{fb.comment}</p>
                  )}
                  <span className={`mt-2 inline-block px-2 py-0.5 text-xs rounded-full ${
                    fb.status === 'RESOLVED' ? 'bg-green-100 text-green-700' :
                    fb.status === 'HIDDEN' ? 'bg-gray-100 text-gray-500' :
                    'bg-blue-100 text-blue-700'
                  }`}>
                    {fb.status}
                  </span>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'visits' && (
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">#</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Branch</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Date</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {visits.length === 0 ? (
                  <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No visits recorded.</td></tr>
                ) : visits.map(v => (
                  <tr key={v.id}>
                    <td className="px-4 py-3 text-gray-500">{v.visit_number}</td>
                    <td className="px-4 py-3 text-gray-900">{v.branch_name}</td>
                    <td className="px-4 py-3 text-gray-600">{v.visit_type.replace('_', ' ')}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {new Date(v.visit_started_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 text-xs rounded-full ${
                        v.status === 'COMPLETED' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}>{v.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'orders' && (
          <CustomerOrdersTab customerId={id!} />
        )}

        {activeTab === 'preferences' && (
          <CustomerPreferencesTab customerId={id!} />
        )}

        {activeTab === 'consents' && (
          <CustomerConsentsTab customerId={id!} />
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-tab components
// ---------------------------------------------------------------------------

function CustomerOrdersTab({ customerId }: { customerId: string }) {
  const [orders, setOrders] = useState<unknown[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    crmApi.getCustomerOrders(customerId)
      .then(r => setOrders((r.data as any).results ?? []))
      .finally(() => setLoading(false))
  }, [customerId])

  if (loading) return <div className="text-center text-gray-400 text-sm py-8">Loading…</div>

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200">
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Order</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Branch</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Date</th>
            <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase">Total</th>
            <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {orders.length === 0 ? (
            <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">No orders found.</td></tr>
          ) : (orders as any[]).map((o: any) => (
            <tr key={o.order_id}>
              <td className="px-4 py-3 font-medium text-gray-900">{o.order_number}</td>
              <td className="px-4 py-3 text-gray-600">{o.branch_name}</td>
              <td className="px-4 py-3 text-gray-500 text-xs">
                {new Date(o.order_date).toLocaleDateString()}
              </td>
              <td className="px-4 py-3 text-right text-gray-700">
                {o.bill_total
                  ? parseFloat(o.bill_total).toLocaleString('en-IN', {
                      style: 'currency', currency: 'INR', minimumFractionDigits: 0,
                    })
                  : '—'}
              </td>
              <td className="px-4 py-3">
                <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-600">{o.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CustomerPreferencesTab({ customerId }: { customerId: string }) {
  const [prefs, setPrefs] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    crmApi.getCustomerPreferences(customerId)
      .then(r => setPrefs(r.data))
      .finally(() => setLoading(false))
  }, [customerId])

  if (loading) return <div className="text-center text-gray-400 text-sm py-8">Loading…</div>
  if (!prefs) return <div className="text-center text-gray-400 text-sm py-8">No preferences set.</div>

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 max-w-lg">
      <InfoRow label="Order Type" value={prefs.preferred_order_type?.replace('_', ' ')} />
      <InfoRow label="Dietary" value={prefs.dietary_preference?.replace('_', ' ')} />
      {prefs.allergy_note && <InfoRow label="Allergies" value={prefs.allergy_note} />}
      {prefs.special_request_note && <InfoRow label="Special Requests" value={prefs.special_request_note} />}
    </div>
  )
}

function CustomerConsentsTab({ customerId }: { customerId: string }) {
  const [consents, setConsents] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    crmApi.getConsents(customerId)
      .then(r => setConsents(r.data))
      .finally(() => setLoading(false))
  }, [customerId])

  if (loading) return <div className="text-center text-gray-400 text-sm py-8">Loading…</div>

  return (
    <div className="space-y-2">
      {consents.length === 0 ? (
        <div className="text-center text-gray-400 text-sm py-8">No consent records.</div>
      ) : consents.map((c: any) => (
        <div key={c.id} className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-xl">
          <span className="text-sm text-gray-700">{c.consent_type.replace(/_/g, ' ')}</span>
          <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
            c.status === 'GRANTED' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}>
            {c.status}
          </span>
        </div>
      ))}
    </div>
  )
}
