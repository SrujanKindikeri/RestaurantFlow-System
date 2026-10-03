// =============================================================================
// RestaurantFlow — Stock Adjustments Page
// Phase 10
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { listAdjustments, createAdjustment, listInventoryItems, listStorageLocations, listStockBalances } from '@/services/inventory'
import type { StockAdjustment, InventoryItem, StorageLocation, StockBalance, UnitOfMeasurement, CreateStockAdjustmentPayload } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const UNITS: UnitOfMeasurement[] = ['KG', 'GRAM', 'LITRE', 'MILLILITRE', 'PIECE', 'PACK', 'BOX', 'BOTTLE', 'DOZEN']

export function AdjustmentsPage() {
  const { hasPermission } = useAuth()
  const [adjustments, setAdjustments] = useState<StockAdjustment[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [invItems, setInvItems] = useState<InventoryItem[]>([])
  const [locations, setLocations] = useState<StorageLocation[]>([])
  const [currentBalance, setCurrentBalance] = useState<string | null>(null)
  const [form, setForm] = useState<Partial<CreateStockAdjustmentPayload>>({ unit: 'KG', reason: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    listAdjustments()
      .then(r => setAdjustments(r.data))
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const openForm = async () => {
    const [items, locs] = await Promise.all([listInventoryItems(), listStorageLocations()])
    setInvItems(items.data)
    setLocations(locs.data)
    setShowForm(true)
  }

  // When item + location are both selected, fetch current balance
  const fetchBalance = useCallback(async (itemId: string, locationId: string) => {
    if (!itemId || !locationId) { setCurrentBalance(null); return }
    try {
      const r = await listStockBalances({ item: itemId, location: locationId })
      const bal = r.data[0]
      if (bal) {
        setCurrentBalance(bal.quantity)
        setForm(f => ({ ...f, unit: bal.item_unit }))
      } else {
        setCurrentBalance('0.000')
      }
    } catch { setCurrentBalance(null) }
  }, [])

  const handleItemChange = (itemId: string) => {
    setForm(f => ({ ...f, inventory_item_id: itemId }))
    if (form.storage_location_id) fetchBalance(itemId, form.storage_location_id)
  }

  const handleLocationChange = (locId: string) => {
    setForm(f => ({ ...f, storage_location_id: locId }))
    if (form.inventory_item_id) fetchBalance(form.inventory_item_id, locId)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await createAdjustment(form as CreateStockAdjustmentPayload)
      setShowForm(false)
      setCurrentBalance(null)
      setForm({ unit: 'KG', reason: '' })
      load()
    } catch (e: any) {
      setFormError(e?.response?.data?.message ?? 'Failed to create adjustment')
    } finally { setSaving(false) }
  }

  const difference = (() => {
    if (currentBalance === null || !form.quantity_physical) return null
    const diff = parseFloat(form.quantity_physical) - parseFloat(currentBalance)
    return isNaN(diff) ? null : diff
  })()

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Stock Adjustments</h1>
          <p className="text-sm text-gray-500 mt-0.5">{adjustments.length} adjustments</p>
        </div>
        {hasPermission('inventory.adjust') && (
          <button onClick={openForm} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm hover:bg-brand-600 transition-colors">+ New Adjustment</button>
        )}
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">Physical Count Reconciliation</h3>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Item *</label>
              <select required value={form.inventory_item_id ?? ''} onChange={e => handleItemChange(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                <option value="">Select item</option>
                {invItems.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Location *</label>
              <select required value={form.storage_location_id ?? ''} onChange={e => handleLocationChange(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                <option value="">Select location</option>
                {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
          </div>

          {/* Show current vs physical */}
          <div className="bg-gray-900 rounded-lg p-4 space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Current Stock (System)</span>
              <span className="text-white font-mono">{currentBalance ?? '—'} {form.unit}</span>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Physical Count *</label>
              <div className="flex gap-2">
                <input type="number" step="0.001" min="0" required placeholder="0.000"
                  value={form.quantity_physical ?? ''}
                  onChange={e => setForm(f => ({ ...f, quantity_physical: e.target.value }))}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
                <select value={form.unit} onChange={e => setForm(f => ({ ...f, unit: e.target.value as UnitOfMeasurement }))}
                  className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                  {UNITS.map(u => <option key={u}>{u}</option>)}
                </select>
              </div>
            </div>
            {difference !== null && (
              <div className="flex justify-between text-sm font-semibold">
                <span className="text-gray-400">Difference</span>
                <span className={difference > 0 ? 'text-green-400' : difference < 0 ? 'text-red-400' : 'text-gray-400'}>
                  {difference > 0 ? '+' : ''}{difference.toFixed(3)} {form.unit}
                  {' '}({difference > 0 ? 'ADJUSTMENT_IN' : difference < 0 ? 'ADJUSTMENT_OUT' : 'NO CHANGE'})
                </span>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs text-gray-400 mb-1">Reason *</label>
            <textarea required minLength={5} value={form.reason ?? ''} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} rows={2}
              placeholder="Physical count on DD/MM/YYYY…"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500 resize-none" />
          </div>

          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm disabled:opacity-50 hover:bg-brand-600">
              {saving ? 'Saving…' : 'Submit Adjustment'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {['Item', 'Location', 'Before', 'Physical', 'Difference', 'Unit', 'Adjusted By', 'Date'].map(h => (
                  <th key={h} className="text-left text-xs text-gray-500 font-medium px-3 py-2">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {adjustments.map(a => (
                <tr key={a.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 py-3 text-gray-200">{a.item_name}</td>
                  <td className="px-3 py-3 text-gray-400">{a.location_name}</td>
                  <td className="px-3 py-3 text-gray-400">{a.quantity_before}</td>
                  <td className="px-3 py-3 text-gray-400">{a.quantity_physical}</td>
                  <td className={`px-3 py-3 font-medium ${parseFloat(a.quantity_difference) > 0 ? 'text-green-400' : parseFloat(a.quantity_difference) < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                    {parseFloat(a.quantity_difference) > 0 ? '+' : ''}{a.quantity_difference}
                  </td>
                  <td className="px-3 py-3 text-gray-400">{a.unit}</td>
                  <td className="px-3 py-3 text-gray-400">{a.adjusted_by_email}</td>
                  <td className="px-3 py-3 text-gray-500 text-xs">{new Date(a.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
              {adjustments.length === 0 && (
                <tr><td colSpan={8} className="px-3 py-8 text-center text-gray-600 text-sm">No adjustments found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
