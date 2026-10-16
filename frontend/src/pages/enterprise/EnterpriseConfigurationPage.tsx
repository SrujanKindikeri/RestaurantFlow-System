// =============================================================================
// RestaurantFlow — Enterprise Configuration Page
// Phase 20
// =============================================================================

import { useEffect, useState } from 'react'
import { Settings, RefreshCw, Check, ChevronDown } from 'lucide-react'
import { enterpriseApi, EffectiveConfig } from '@/services/enterprise'

const SOURCE_COLOR: Record<string, string> = {
  BRANCH:         'bg-purple-100 text-purple-700',
  RESTAURANT:     'bg-blue-100 text-blue-700',
  COMPANY:        'bg-gray-100 text-gray-700',
  SYSTEM_DEFAULT: 'bg-green-50 text-green-600',
}

function SourceBadge({ source }: { source: string }) {
  return (
    <span className={`inline-block px-2 py-0.5 text-xs rounded font-medium ${SOURCE_COLOR[source] ?? 'bg-gray-100 text-gray-600'}`}>
      {source.replace(/_/g, ' ')}
    </span>
  )
}

// Group keys by category prefix
function groupByCategory(configs: EffectiveConfig[]): Record<string, EffectiveConfig[]> {
  const groups: Record<string, EffectiveConfig[]> = {}
  configs.forEach((c) => {
    const [cat] = c.key.split('.')
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(c)
  })
  return groups
}

export function EnterpriseConfigurationPage() {
  const [configs, setConfigs] = useState<EffectiveConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editKey, setEditKey] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [editReason, setEditReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)
  const [branchId, setBranchId] = useState('')
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({})

  function showToast(msg: string, type: 'success' | 'error') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3500)
  }

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string> = {}
      if (branchId) params.branch_id = branchId
      const res = await enterpriseApi.getEffectiveConfiguration(params)
      setConfigs(Array.isArray(res) ? res : [])
    } catch {
      setError('Failed to load configuration.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(key: string) {
    setSaving(true)
    try {
      const params: Record<string, string> = {
        configuration_key: key,
        configuration_value: editValue,
        reason: editReason,
      }
      if (branchId) params.branch_id = branchId
      await enterpriseApi.setConfiguration(params)
      showToast(`${key} updated.`, 'success')
      setEditKey(null)
      setEditReason('')
      load()
    } catch (e: any) {
      showToast(e?.response?.data?.message ?? 'Failed to save.', 'error')
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => { load() }, [branchId])

  const grouped = groupByCategory(configs)

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm text-white ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`} role="alert">
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Settings className="h-6 w-6 text-blue-600" aria-hidden="true" />
            Enterprise Configuration
          </h1>
          <p className="text-sm text-gray-500 mt-1">Effective values with source tracking</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50"
          aria-label="Refresh configuration"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      {/* Scope filter */}
      <div className="mb-5">
        <label htmlFor="branch-filter" className="block text-xs font-medium text-gray-600 mb-1">
          Filter by Branch ID (optional)
        </label>
        <div className="flex gap-2">
          <input
            id="branch-filter"
            type="text"
            value={branchId}
            onChange={(e) => setBranchId(e.target.value)}
            placeholder="Branch UUID…"
            className="flex-1 text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
          />
          {branchId && (
            <button onClick={() => setBranchId('')} className="text-sm text-gray-500 hover:text-gray-700">Clear</button>
          )}
        </div>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700 mb-4" role="alert">{error}</div>
      )}

      {loading && (
        <div className="space-y-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {/* Config groups */}
      {!loading && Object.entries(grouped).map(([category, items]) => (
        <div key={category} className="bg-white rounded-xl border border-gray-200 mb-4 overflow-hidden">
          <button
            onClick={() => setCollapsed((prev) => ({ ...prev, [category]: !prev[category] }))}
            className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 text-left hover:bg-gray-100 transition"
            aria-expanded={!collapsed[category]}
          >
            <h2 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">{category}</h2>
            <ChevronDown className={`h-4 w-4 text-gray-500 transition-transform ${collapsed[category] ? '' : 'rotate-180'}`} aria-hidden="true" />
          </button>

          {!collapsed[category] && (
            <div className="divide-y divide-gray-50">
              {items.map((cfg) => (
                <div key={cfg.key} className="px-4 py-3">
                  {editKey === cfg.key ? (
                    <div className="space-y-2">
                      <p className="text-xs font-mono text-gray-500">{cfg.key}</p>
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="w-full text-sm border border-blue-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
                        aria-label={`Edit value for ${cfg.key}`}
                      />
                      <input
                        type="text"
                        value={editReason}
                        onChange={(e) => setEditReason(e.target.value)}
                        placeholder="Reason for change (optional)"
                        className="w-full text-sm border border-gray-300 rounded-lg px-3 py-1.5 focus:ring-2 focus:ring-blue-500 outline-none"
                        aria-label="Change reason"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleSave(cfg.key)}
                          disabled={saving}
                          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1"
                        >
                          <Check className="h-3.5 w-3.5" aria-hidden="true" />
                          {saving ? 'Saving…' : 'Save'}
                        </button>
                        <button
                          onClick={() => { setEditKey(null); setEditReason('') }}
                          className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="text-xs font-mono text-gray-500">{cfg.key}</p>
                        <p className="text-sm font-medium text-gray-900 mt-0.5">
                          {String(cfg.value)}
                          {cfg.is_overridden && (
                            <span className="ml-2 text-xs text-purple-600">overridden</span>
                          )}
                        </p>
                        <p className="text-xs text-gray-400 mt-0.5">{cfg.description}</p>
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <SourceBadge source={cfg.source} />
                        <button
                          onClick={() => { setEditKey(cfg.key); setEditValue(cfg.raw_value) }}
                          className="text-xs text-blue-600 hover:underline focus:outline-none focus:ring-1 focus:ring-blue-500 rounded"
                        >
                          Edit
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {!loading && configs.length === 0 && (
        <p className="text-center py-12 text-gray-400 text-sm">No configuration values found.</p>
      )}
    </div>
  )
}
