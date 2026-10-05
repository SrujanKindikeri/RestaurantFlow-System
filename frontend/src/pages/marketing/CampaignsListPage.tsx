// =============================================================================
// RestaurantFlow — Campaigns List Page
// Phase 18
// =============================================================================

import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import marketingApi, { CampaignListItem, CampaignStatus, CampaignType } from '@/services/marketing'

const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'PENDING_APPROVAL', label: 'Pending Approval' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'SCHEDULED', label: 'Scheduled' },
  { value: 'RUNNING', label: 'Running' },
  { value: 'PAUSED', label: 'Paused' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'CANCELLED', label: 'Cancelled' },
]

const TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All Types' },
  { value: 'PROMOTION', label: 'Promotion' },
  { value: 'LOYALTY', label: 'Loyalty' },
  { value: 'REACTIVATION', label: 'Reactivation' },
  { value: 'NEW_CUSTOMER', label: 'New Customer' },
  { value: 'BIRTHDAY', label: 'Birthday' },
  { value: 'SEASONAL', label: 'Seasonal' },
  { value: 'ANNOUNCEMENT', label: 'Announcement' },
]

function StatusBadge({ status }: { status: CampaignStatus }) {
  const map: Record<string, string> = {
    RUNNING:          'bg-emerald-100 text-emerald-700',
    SCHEDULED:        'bg-blue-100 text-blue-700',
    PAUSED:           'bg-amber-100 text-amber-700',
    DRAFT:            'bg-gray-100 text-gray-600',
    PENDING_APPROVAL: 'bg-purple-100 text-purple-700',
    APPROVED:         'bg-teal-100 text-teal-700',
    COMPLETED:        'bg-gray-200 text-gray-700',
    CANCELLED:        'bg-red-100 text-red-600',
    FAILED:           'bg-red-200 text-red-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${map[status] ?? 'bg-gray-100 text-gray-500'}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

function formatDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function CampaignsListPage() {
  const navigate = useNavigate()
  const [campaigns, setCampaigns] = useState<CampaignListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const PAGE_SIZE = 20

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = { page: String(page) }
    if (search) params.search = search
    if (statusFilter) params.status = statusFilter
    if (typeFilter) params.campaign_type = typeFilter

    marketingApi.getCampaigns(params)
      .then(r => {
        setCampaigns(r.data.results)
        setTotal(r.data.count)
      })
      .catch(() => setError('Failed to load campaigns.'))
      .finally(() => setLoading(false))
  }, [page, search, statusFilter, typeFilter])

  useEffect(() => { load() }, [load])

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Campaigns</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} total campaigns</p>
        </div>
        <Link
          to="/marketing/campaigns/new"
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 font-medium"
        >
          + New Campaign
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search name or code…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
        />
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={typeFilter}
          onChange={e => { setTypeFilter(e.target.value); setPage(1) }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        {(search || statusFilter || typeFilter) && (
          <button
            onClick={() => { setSearch(''); setStatusFilter(''); setTypeFilter(''); setPage(1) }}
            className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 border border-gray-200 rounded-lg"
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : error ? (
        <div className="text-center text-red-500 text-sm py-12">{error}</div>
      ) : campaigns.length === 0 ? (
        <div className="text-center text-gray-400 text-sm py-12">
          <p>No campaigns found.</p>
          <Link to="/marketing/campaigns/new" className="text-blue-600 hover:underline mt-2 inline-block">
            Create your first campaign →
          </Link>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Campaign', 'Type', 'Status', 'Restaurant', 'Start', 'End', 'Created By', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {campaigns.map(c => (
                  <tr
                    key={c.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/marketing/campaigns/${c.id}`)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{c.name}</div>
                      <div className="text-xs text-gray-400 font-mono">{c.code}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-600">
                      {c.campaign_type.replace(/_/g, ' ')}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-3 text-gray-500">{c.restaurant_name || '—'}</td>
                    <td className="px-4 py-3 text-gray-500">{formatDate(c.start_at)}</td>
                    <td className="px-4 py-3 text-gray-500">{formatDate(c.end_at)}</td>
                    <td className="px-4 py-3 text-gray-400 text-xs">{c.created_by_email}</td>
                    <td className="px-4 py-3">
                      <Link
                        to={`/marketing/campaigns/${c.id}`}
                        className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                        onClick={e => e.stopPropagation()}
                      >
                        View →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>
            Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              className="px-3 py-1 border border-gray-200 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              ← Prev
            </button>
            <button
              disabled={page * PAGE_SIZE >= total}
              onClick={() => setPage(p => p + 1)}
              className="px-3 py-1 border border-gray-200 rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
