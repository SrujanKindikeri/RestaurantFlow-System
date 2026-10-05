// =============================================================================
// RestaurantFlow — CRM Loyalty Program Page
// Phase 17
// =============================================================================

import { useState, useEffect } from 'react'
import crmApi from '@/services/crm'

export function CRMLoyaltyPage() {
  const [programs, setPrograms] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    name: '', description: '',
    points_per_currency_unit: '1.0000',
    minimum_redemption_points: '100',
    point_expiry_days: '',
    restaurant_id: '',
    is_active: true,
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    crmApi.getLoyaltyPrograms()
      .then(r => setPrograms(r.data as any[]))
      .catch(() => setError('Failed to load loyalty programs.'))
      .finally(() => setLoading(false))
  }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await crmApi.createLoyaltyProgram({
        ...form,
        minimum_redemption_points: parseInt(form.minimum_redemption_points),
        point_expiry_days: form.point_expiry_days ? parseInt(form.point_expiry_days) : null,
      })
      setShowCreate(false)
      crmApi.getLoyaltyPrograms().then(r => setPrograms(r.data as any[]))
    } catch {
      setError('Failed to create loyalty program.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Loyalty Programs</h1>
          <p className="text-sm text-gray-500 mt-1">Configure points earning and redemption rules</p>
        </div>
        <button onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700">
          + New Program
        </button>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>}

      {loading ? (
        <div className="text-center text-gray-400 text-sm py-12">Loading…</div>
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {programs.length === 0 ? (
            <div className="col-span-2 text-center text-gray-400 text-sm py-12">No loyalty programs defined yet.</div>
          ) : programs.map((p: any) => (
            <div key={p.id} className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">{p.name}</h3>
                <span className={`px-2 py-0.5 text-xs rounded-full ${
                  p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>{p.is_active ? 'Active' : 'Inactive'}</span>
              </div>
              {p.description && <p className="text-sm text-gray-500">{p.description}</p>}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-blue-50 rounded-lg p-3">
                  <p className="text-lg font-bold text-blue-700">{p.points_per_currency_unit}</p>
                  <p className="text-xs text-blue-500">pts / ₹</p>
                </div>
                <div className="bg-purple-50 rounded-lg p-3">
                  <p className="text-lg font-bold text-purple-700">{p.minimum_redemption_points}</p>
                  <p className="text-xs text-purple-500">min redeem</p>
                </div>
                <div className="bg-orange-50 rounded-lg p-3">
                  <p className="text-lg font-bold text-orange-700">
                    {p.point_expiry_days ?? '∞'}
                  </p>
                  <p className="text-xs text-orange-500">days expiry</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">New Loyalty Program</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-600">Name *</label>
                <input required value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-medium text-gray-600">Points per ₹</label>
                  <input type="number" step="0.0001" min="0.0001"
                    value={form.points_per_currency_unit}
                    onChange={e => setForm(f => ({ ...f, points_per_currency_unit: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Min Redemption Points</label>
                  <input type="number" min="1"
                    value={form.minimum_redemption_points}
                    onChange={e => setForm(f => ({ ...f, minimum_redemption_points: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Expiry Days (blank = never)</label>
                  <input type="number" min="1"
                    value={form.point_expiry_days}
                    onChange={e => setForm(f => ({ ...f, point_expiry_days: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Restaurant ID *</label>
                  <input required value={form.restaurant_id}
                    onChange={e => setForm(f => ({ ...f, restaurant_id: e.target.value }))}
                    placeholder="UUID"
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm font-mono focus:outline-none" />
                </div>
              </div>
              <div className="flex gap-3 justify-end pt-2">
                <button type="button" onClick={() => setShowCreate(false)}
                  className="px-4 py-2 text-sm text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={saving}
                  className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                  {saving ? 'Creating…' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
