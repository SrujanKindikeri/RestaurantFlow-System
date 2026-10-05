// =============================================================================
// RestaurantFlow — CRM Rewards Page
// Phase 17
// =============================================================================

import { useState, useEffect } from 'react'
import crmApi, { LoyaltyReward } from '@/services/crm'

export function CRMRewardsPage() {
  const [rewards, setRewards] = useState<LoyaltyReward[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    name: '', description: '', reward_type: 'DISCOUNT',
    points_required: '', reward_value: '', restaurant_id: '',
    is_active: true, valid_until: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const fetchRewards = async () => {
    setLoading(true)
    try {
      const res = await crmApi.listRewards()
      setRewards(res.data.results)
    } catch {
      setError('Failed to load rewards.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchRewards() }, [])

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    try {
      await crmApi.createReward({
        ...form,
        points_required: parseInt(form.points_required),
        reward_value: form.reward_value || null,
        valid_until: form.valid_until || null,
      })
      setShowCreate(false)
      fetchRewards()
    } catch {
      setError('Failed to create reward.')
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (reward: LoyaltyReward) => {
    await crmApi.updateReward(reward.id, { is_active: !reward.is_active })
    fetchRewards()
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Loyalty Rewards</h1>
          <p className="text-sm text-gray-500 mt-1">Define redeemable rewards for customers</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700"
        >
          + New Reward
        </button>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">{error}</div>}

      {loading ? (
        <div className="text-center text-gray-400 text-sm py-12">Loading…</div>
      ) : (
        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {rewards.length === 0 ? (
            <div className="col-span-3 text-center text-gray-400 text-sm py-12">No rewards defined yet.</div>
          ) : rewards.map(r => (
            <div key={r.id} className="bg-white border border-gray-200 rounded-xl p-5 space-y-3">
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-gray-900">{r.name}</h3>
                <button
                  onClick={() => toggleActive(r)}
                  className={`px-2 py-0.5 text-xs rounded-full border cursor-pointer ${
                    r.is_active
                      ? 'border-green-200 text-green-700 bg-green-50 hover:bg-green-100'
                      : 'border-gray-200 text-gray-500 bg-gray-50 hover:bg-gray-100'
                  }`}
                >
                  {r.is_active ? 'Active' : 'Inactive'}
                </button>
              </div>
              {r.description && <p className="text-sm text-gray-500">{r.description}</p>}
              <div className="flex items-center gap-3">
                <div className="bg-blue-50 text-blue-700 px-3 py-1.5 rounded-lg text-center">
                  <p className="text-xl font-bold">{r.points_required.toLocaleString()}</p>
                  <p className="text-xs">points</p>
                </div>
                <div className="text-sm text-gray-600">
                  <p className="font-medium">{r.reward_type.replace('_', ' ')}</p>
                  {r.reward_value && <p className="text-gray-400">Value: {r.reward_value}</p>}
                </div>
              </div>
              {r.valid_until && (
                <p className="text-xs text-gray-400">
                  Valid until: {new Date(r.valid_until).toLocaleDateString()}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">New Reward</h2>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="text-xs font-medium text-gray-600">Name *</label>
                  <input required value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Type</label>
                  <select value={form.reward_type} onChange={e => setForm(f => ({ ...f, reward_type: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none">
                    <option value="DISCOUNT">Discount</option>
                    <option value="FIXED_AMOUNT">Fixed Amount</option>
                    <option value="PERCENTAGE">Percentage</option>
                    <option value="FREE_ITEM">Free Item</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Points Required *</label>
                  <input required type="number" min="1" value={form.points_required}
                    onChange={e => setForm(f => ({ ...f, points_required: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Reward Value</label>
                  <input type="number" value={form.reward_value}
                    onChange={e => setForm(f => ({ ...f, reward_value: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600">Valid Until</label>
                  <input type="datetime-local" value={form.valid_until}
                    onChange={e => setForm(f => ({ ...f, valid_until: e.target.value }))}
                    className="mt-1 w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none" />
                </div>
                <div className="col-span-2">
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
                  {saving ? 'Creating…' : 'Create Reward'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
