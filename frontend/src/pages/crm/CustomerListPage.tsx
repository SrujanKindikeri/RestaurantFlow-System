// =============================================================================
// RestaurantFlow — Customer List Page
// Phase 17
// =============================================================================

import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import crmApi, { Customer } from '@/services/crm'

function StatusBadge({ active, blocked }: { active: boolean; blocked: boolean }) {
  if (blocked) return <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">Blocked</span>
  if (!active) return <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-500">Inactive</span>
  return <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700">Active</span>
}

export function CustomerListPage() {
  const { user } = useAuth()
  const navigate = useNavigate()

  const [customers, setCustomers] = useState<Customer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  const PAGE_SIZE = 20

  const fetchCustomers = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params: Record<string, string> = { page: String(page) }
      if (search) params.search = search
      const res = await crmApi.listCustomers(params)
      setCustomers(res.data.results)
      setTotalCount(res.data.count)
    } catch {
      setError('Failed to load customers.')
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => { fetchCustomers() }, [fetchCustomers])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    fetchCustomers()
  }

  const totalPages = Math.ceil(totalCount / PAGE_SIZE)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Customers</h1>
          <p className="text-sm text-gray-500 mt-1">{totalCount} total customers</p>
        </div>
        <Link
          to="/customers/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
        >
          + New Customer
        </Link>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3">
        <input
          type="text"
          placeholder="Search by name, phone, email, or customer number…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="flex-1 px-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-gray-800 text-white text-sm rounded-lg hover:bg-gray-700 transition-colors"
        >
          Search
        </button>
        {search && (
          <button
            type="button"
            onClick={() => { setSearch(''); setPage(1) }}
            className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700"
          >
            Clear
          </button>
        )}
      </form>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>
      )}

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Loading customers…</div>
        ) : customers.length === 0 ? (
          <div className="p-12 text-center text-gray-400 text-sm">No customers found.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Customer</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Phone</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Email</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Orders</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Spend</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Last Visit</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-gray-500 uppercase tracking-wide">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {customers.map(c => (
                <tr
                  key={c.id}
                  className="hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => navigate(`/customers/${c.id}`)}
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{c.display_name}</div>
                    <div className="text-xs text-gray-400">{c.customer_number}</div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{c.masked_phone || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{c.masked_email || '—'}</td>
                  <td className="px-4 py-3 text-right text-gray-700">{c.total_orders}</td>
                  <td className="px-4 py-3 text-right text-gray-700">
                    {parseFloat(c.lifetime_spend).toLocaleString('en-IN', {
                      style: 'currency', currency: 'INR', minimumFractionDigits: 0,
                    })}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {c.last_visit_at
                      ? new Date(c.last_visit_at).toLocaleDateString()
                      : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge active={c.is_active} blocked={c.is_blocked} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>Page {page} of {totalPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1.5 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
