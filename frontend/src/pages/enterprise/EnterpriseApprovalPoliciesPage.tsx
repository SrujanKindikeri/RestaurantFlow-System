// =============================================================================
// RestaurantFlow — Enterprise Approval Policies Page
// Phase 20
// =============================================================================

import { useEffect, useState } from 'react'
import { CheckCircle2, RefreshCw, Plus } from 'lucide-react'
import { enterpriseApi, ApprovalPolicy } from '@/services/enterprise'

const SCOPE_COLOR: Record<string, string> = {
  BRANCH:     'bg-purple-100 text-purple-700',
  RESTAURANT: 'bg-blue-100 text-blue-700',
  COMPANY:    'bg-gray-100 text-gray-700',
}

export function EnterpriseApprovalPoliciesPage() {
  const [policies, setPolicies] = useState<ApprovalPolicy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [typeFilter, setTypeFilter] = useState('')
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  function showToast(msg: string, type: 'success' | 'error') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (typeFilter) params.policy_type = typeFilter
      const res = await enterpriseApi.getApprovalPolicies(params)
      setPolicies(Array.isArray(res) ? res : [])
    } catch {
      setError('Failed to load approval policies.')
    } finally {
      setLoading(false)
    }
  }

  async function handleToggle(policy: ApprovalPolicy) {
    try {
      await enterpriseApi.updateApprovalPolicy(policy.id, { is_active: !policy.is_active })
      showToast(`Policy ${policy.is_active ? 'deactivated' : 'activated'}.`, 'success')
      load()
    } catch {
      showToast('Failed to update policy.', 'error')
    }
  }

  useEffect(() => { load() }, [typeFilter])

  const policyTypes = ['EXPENSE', 'DISCOUNT', 'REFUND', 'WASTAGE', 'STOCK_TRANSFER', 'CONFIGURATION', 'PRICE_ROLLOUT']

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm text-white ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`} role="alert">
          {toast.msg}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <CheckCircle2 className="h-6 w-6 text-blue-600" aria-hidden="true" />
            Approval Policies
          </h1>
          <p className="text-sm text-gray-500 mt-1">Threshold-based approval rules by scope</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          aria-label="Refresh approval policies"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Type filter */}
      <div className="mb-4 flex gap-2 flex-wrap">
        <button
          onClick={() => setTypeFilter('')}
          className={`px-3 py-1.5 text-sm rounded-lg border transition ${typeFilter === '' ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 text-gray-700 hover:bg-gray-50'}`}
        >
          All
        </button>
        {policyTypes.map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1.5 text-sm rounded-lg border transition ${typeFilter === t ? 'bg-blue-600 text-white border-blue-600' : 'border-gray-300 text-gray-700 hover:bg-gray-50'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-4" role="alert">{error}</div>
      )}

      {loading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {!loading && policies.length === 0 && (
        <div className="text-center py-12 text-gray-400">
          <CheckCircle2 className="h-10 w-10 mx-auto mb-2 opacity-40" aria-hidden="true" />
          <p>No approval policies configured.</p>
        </div>
      )}

      {!loading && policies.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-100" role="table">
            <thead className="bg-gray-50">
              <tr>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Scope</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden md:table-cell">Threshold</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase hidden lg:table-cell">Required Permission</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {policies.map((p) => {
                const scope = p.branch ? 'BRANCH' : p.restaurant ? 'RESTAURANT' : 'COMPANY'
                const scopeLabel = p.branch?.name ?? p.restaurant?.name ?? 'Company-wide'
                return (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-gray-900">{p.policy_type}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${SCOPE_COLOR[scope]}`}>{scope}</span>
                      <p className="text-xs text-gray-500 mt-0.5">{scopeLabel}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 hidden md:table-cell">
                      {p.threshold_amount ? `₹${p.threshold_amount}` : ''}
                      {p.threshold_percentage ? `${p.threshold_percentage}%` : ''}
                      {!p.threshold_amount && !p.threshold_percentage ? 'Always' : ''}
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <code className="text-xs bg-gray-50 px-1.5 py-0.5 rounded text-gray-700">{p.required_permission}</code>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                        {p.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleToggle(p)}
                        className={`text-xs hover:underline ${p.is_active ? 'text-red-500' : 'text-green-600'}`}
                      >
                        {p.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
