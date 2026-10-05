// =============================================================================
// RestaurantFlow — CRM Segments Page
// Phase 17
// =============================================================================

import { useState, useEffect } from 'react'
import crmApi, { CustomerSegment } from '@/services/crm'

export function CRMSegmentsPage() {
  const [segments, setSegments] = useState<CustomerSegment[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ name: '', code: '', description: '', criteria: '{}', restaurant_id: '' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    crmApi.listSegments()
      .then(r => setSegments(r.data))
      .catch(() => setError('Failed to load segments.'))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      let criteria = {}
      try { criteria = JSON.parse(form.criteria) } catch { setError('Invalid JSON in criteria.'); setSaving(false); return }
      const res = await crmApi.createSegment({ ...form, criteria })
      setSegments(s => [res.data, ...s])
      setShowCreate(false)
      setForm({ name: '', code: '', description: '', criteria: '{}', restaurant_id: '' })
    } catch {
      setError('Failed to create segment.')
    } finally {
      setSaving(false)
    }
  }

  const CRITERIA_EXAMPLES = [
    { label: 'High Value (spend ≥ 50,000)', value: '{"min_lifetime_spend": 50000}' },
    { label: 'Frequent (10+ orders)', value: '{"min_orders": 10}' },
    { label: 'At Risk (no order 60+ days)', value: '{"days_since_last_order": 60}' },
    { label: 'Inactive (no order 90+ days)', value: '{"days_since_last_order": 90}' },
    { label: 'New (1–2 orders)', value: '{"min_orders": 1, "max_orders": 2}' },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Customer Segments</h1>
          <p className="text-sm text-gray-500 mt-1">Criteria-based customer groups</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          + New Segment
        </button>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>}

      {loading ? (
        <div className="text-center text-gray-400 text-sm py-12">Loading…</div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {segments.length === 0 ? (
            <div className="col-span-3 text-center text-gray-400 text-sm py-12">No segments defined yet.</div>
          ) : segments.map(seg => (
            <div key={seg.id} className="bg-white border border-gray-200 rounded-xl p-5 space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">{seg.name}</h3>
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  seg.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  {seg.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
              <p className="text-xs text-gray-400 font-mono bg-gray-50 px-2 py-1 rounded">{seg.code}</p>
              {seg.description && <p className="text-sm text-gray-600">{seg.description}</p>}
              <div className="mt-2">
                <p className="text-xs text-gray-400 mb-1">Criteria</p>
                <pre className="text-xs text-gray-600 bg-gray-50 rounded-lg p-2 overflow-x-auto">
                  {JSON.stringify(seg.criteria, null, 2)}
                </pre>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">New Customer Segment</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-600">Name *</label>
                  <input
                    required
                    value={form.name}
                    onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Code *</label>
                  <input
                    required
                    value={form.code}
                    onChange={e => setForm(f => ({ ...f, code: e.target.value.toUpperCase() }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono focus:outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Description</label>
                <input
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none"
                />
              </div>
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-medium text-gray-600">Criteria (JSON)</label>
                  <select
                    onChange={e => { if (e.target.value) setForm(f => ({ ...f, criteria: e.target.value })) }}
                    className="text-xs border border-gray-200 rounded px-2 py-1"
                  >
                    <option value="">Load example…</option>
                    {CRITERIA_EXAMPLES.map(ex => (
                      <option key={ex.label} value={ex.value}>{ex.label}</option>
                    ))}
                  </select>
                </div>
                <textarea
                  value={form.criteria}
                  onChange={e => setForm(f => ({ ...f, criteria: e.target.value }))}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono focus:outline-none"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Restaurant ID</label>
                <input
                  required
                  value={form.restaurant_id}
                  onChange={e => setForm(f => ({ ...f, restaurant_id: e.target.value }))}
                  placeholder="UUID of the restaurant"
                  className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono focus:outline-none"
                />
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {saving ? 'Creating…' : 'Create Segment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
