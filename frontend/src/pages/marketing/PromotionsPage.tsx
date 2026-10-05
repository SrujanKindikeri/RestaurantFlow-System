// =============================================================================
// RestaurantFlow — Promotions Page
// Phase 18
// =============================================================================

import { useState, useEffect, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import marketingApi, { PromotionListItem } from '@/services/marketing'
import { useAuth } from '@/contexts/AuthContext'

function ActiveBadge({ active }: { active: boolean }) {
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
      active ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'
    }`}>
      {active ? 'Active' : 'Inactive'}
    </span>
  )
}

function PromotionTypeBadge({ type }: { type: string }) {
  const map: Record<string, string> = {
    PERCENTAGE_DISCOUNT: 'bg-blue-50 text-blue-700',
    FIXED_DISCOUNT:      'bg-indigo-50 text-indigo-700',
    FREE_ITEM:           'bg-emerald-50 text-emerald-700',
    BUY_X_GET_Y:         'bg-amber-50 text-amber-700',
    LOYALTY_BONUS:       'bg-purple-50 text-purple-700',
    OTHER:               'bg-gray-50 text-gray-600',
  }
  const labels: Record<string, string> = {
    PERCENTAGE_DISCOUNT: '% Discount',
    FIXED_DISCOUNT:      'Fixed Off',
    FREE_ITEM:           'Free Item',
    BUY_X_GET_Y:         'Buy X Get Y',
    LOYALTY_BONUS:       'Loyalty Bonus',
    OTHER:               'Other',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${map[type] ?? 'bg-gray-50 text-gray-600'}`}>
      {labels[type] ?? type}
    </span>
  )
}

function formatDate(dt: string | null) {
  if (!dt) return '—'
  return new Date(dt).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function PromotionsPage() {
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  const [promotions, setPromotions] = useState<PromotionListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [activeFilter, setActiveFilter] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = { page: String(page) }
    if (search) params.search = search
    if (activeFilter !== '') params.is_active = activeFilter

    marketingApi.getPromotions(params)
      .then(r => { setPromotions(r.data.results); setTotal(r.data.count) })
      .catch(() => setError('Failed to load promotions.'))
      .finally(() => setLoading(false))
  }, [page, search, activeFilter])

  useEffect(() => { load() }, [load])

  async function toggleActive(promo: PromotionListItem) {
    setActionLoadingId(promo.id)
    try {
      if (promo.is_active) {
        await marketingApi.deactivatePromotion(promo.id)
      } else {
        await marketingApi.activatePromotion(promo.id)
      }
      load()
    } catch {
      // silently fail — show inline
    } finally {
      setActionLoadingId(null)
    }
  }

  const canCreate = hasPermission('marketing.promotion.create')
  const canActivate = hasPermission('marketing.promotion.activate')
  const canDeactivate = hasPermission('marketing.promotion.deactivate')

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Promotions</h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} total promotions</p>
        </div>
        {canCreate && (
          <Link
            to="/marketing/promotions/new"
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 font-medium"
          >
            + New Promotion
          </Link>
        )}
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
          value={activeFilter}
          onChange={e => { setActiveFilter(e.target.value); setPage(1) }}
          className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All</option>
          <option value="true">Active Only</option>
          <option value="false">Inactive Only</option>
        </select>
        {(search || activeFilter) && (
          <button
            onClick={() => { setSearch(''); setActiveFilter(''); setPage(1) }}
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
      ) : promotions.length === 0 ? (
        <div className="text-center text-gray-400 text-sm py-12">
          <p>No promotions found.</p>
          {canCreate && (
            <Link to="/marketing/promotions/new" className="text-blue-600 hover:underline mt-2 inline-block">
              Create your first promotion →
            </Link>
          )}
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Promotion', 'Type', 'Discount', 'Code', 'Valid', 'Usage', 'Status', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {promotions.map(p => (
                  <tr
                    key={p.id}
                    className="hover:bg-gray-50 cursor-pointer"
                    onClick={() => navigate(`/marketing/promotions/${p.id}`)}
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900">{p.name}</div>
                      <div className="text-xs text-gray-400">{p.restaurant_name || '—'}</div>
                    </td>
                    <td className="px-4 py-3"><PromotionTypeBadge type={p.promotion_type} /></td>
                    <td className="px-4 py-3 text-gray-600">
                      {p.discount_value
                        ? (p.discount_type === 'PERCENTAGE'
                          ? `${p.discount_value}%`
                          : `₹${p.discount_value}`)
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {p.code
                        ? <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded">{p.code}</span>
                        : <span className="text-gray-300">—</span>}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                      {formatDate(p.start_at)} – {formatDate(p.end_at)}
                    </td>
                    <td className="px-4 py-3 text-gray-500">
                      {p.current_usage_count}{p.usage_limit ? `/${p.usage_limit}` : ''}
                    </td>
                    <td className="px-4 py-3"><ActiveBadge active={p.is_active} /></td>
                    <td className="px-4 py-3" onClick={e => e.stopPropagation()}>
                      <div className="flex gap-2 items-center">
                        {(canActivate || canDeactivate) && (
                          <button
                            disabled={actionLoadingId === p.id}
                            onClick={() => toggleActive(p)}
                            className={`text-xs px-2 py-1 rounded border ${
                              p.is_active
                                ? 'border-red-200 text-red-600 hover:bg-red-50'
                                : 'border-emerald-200 text-emerald-600 hover:bg-emerald-50'
                            } disabled:opacity-40`}
                          >
                            {actionLoadingId === p.id ? '…' : p.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                        )}
                        <Link
                          to={`/marketing/promotions/${p.id}`}
                          className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                        >
                          View →
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {total > 20 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>Showing {((page - 1) * 20) + 1}–{Math.min(page * 20, total)} of {total}</span>
          <div className="flex gap-2">
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
              className="px-3 py-1 border border-gray-200 rounded disabled:opacity-40 hover:bg-gray-50">← Prev</button>
            <button disabled={page * 20 >= total} onClick={() => setPage(p => p + 1)}
              className="px-3 py-1 border border-gray-200 rounded disabled:opacity-40 hover:bg-gray-50">Next →</button>
          </div>
        </div>
      )}
    </div>
  )
}
