// =============================================================================
// RestaurantFlow — Inventory Items Page
// Phase 10
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { listInventoryItems, listCategories, createInventoryItem, updateInventoryItem } from '@/services/inventory'
import type { InventoryItem, InventoryCategory, UnitOfMeasurement, CreateInventoryItemPayload } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const UNITS: UnitOfMeasurement[] = ['KG', 'GRAM', 'LITRE', 'MILLILITRE', 'PIECE', 'PACK', 'BOX', 'BOTTLE', 'DOZEN']

const STATUS_BADGE: Record<string, string> = {
  IN_STOCK:    'bg-green-500/10 text-green-400 border-green-500/20',
  LOW_STOCK:   'bg-amber-500/10 text-amber-400 border-amber-500/20',
  OUT_OF_STOCK:'bg-red-500/10 text-red-400 border-red-500/20',
}

export function InventoryItemsPage() {
  const { user, hasPermission } = useAuth()
  const [items, setItems] = useState<InventoryItem[]>([])
  const [categories, setCategories] = useState<InventoryCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Infer restaurant from user scope (first restaurant in scope)
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [form, setForm] = useState<Partial<CreateInventoryItemPayload>>({
    restaurant_id: restaurantId,
    default_unit: 'KG',
    minimum_stock: '0.000',
    reorder_level: '0.000',
    maximum_stock: '0.000',
  })

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (search) params.search = search
    if (filterCategory) params.category = filterCategory
    Promise.all([
      listInventoryItems(params),
      listCategories(restaurantId ? { restaurant: restaurantId } : {}),
    ])
      .then(([itemsRes, catsRes]) => {
        setItems(itemsRes.data)
        setCategories(catsRes.data)
      })
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load items'))
      .finally(() => setLoading(false))
  }, [search, filterCategory, restaurantId])

  useEffect(() => { load() }, [load])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await createInventoryItem({ ...form, restaurant_id: restaurantId } as CreateInventoryItemPayload)
      setShowForm(false)
      setForm({ restaurant_id: restaurantId, default_unit: 'KG', minimum_stock: '0.000', reorder_level: '0.000', maximum_stock: '0.000' })
      load()
    } catch (e: any) {
      const detail = e?.response?.data
      setFormError(detail?.message ?? detail?.details?.sku?.[0] ?? 'Failed to create item')
    } finally {
      setSaving(false)
    }
  }

  const handleToggleActive = async (item: InventoryItem) => {
    try {
      await updateInventoryItem(item.id, { is_active: !item.is_active })
      load()
    } catch { /* ignore */ }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Inventory Items</h1>
          <p className="text-sm text-gray-500 mt-0.5">{items.length} items</p>
        </div>
        {hasPermission('inventory.create') && (
          <button
            onClick={() => setShowForm(v => !v)}
            className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm hover:bg-brand-600 transition-colors"
          >
            + Add Item
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search name or SKU…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-500 w-56"
        />
        <select
          value={filterCategory}
          onChange={e => setFilterCategory(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
        >
          <option value="">All Categories</option>
          {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      {/* Add Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">New Inventory Item</h3>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Name *</label>
              <input
                required
                value={form.name ?? ''}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">SKU *</label>
              <input
                required
                value={form.sku ?? ''}
                onChange={e => setForm(f => ({ ...f, sku: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Default Unit *</label>
              <select
                value={form.default_unit}
                onChange={e => setForm(f => ({ ...f, default_unit: e.target.value as UnitOfMeasurement }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              >
                {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Category</label>
              <select
                value={form.category_id ?? ''}
                onChange={e => setForm(f => ({ ...f, category_id: e.target.value || undefined }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              >
                <option value="">None</option>
                {categories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Reorder Level</label>
              <input
                type="number" step="0.001" min="0"
                value={form.reorder_level ?? '0.000'}
                onChange={e => setForm(f => ({ ...f, reorder_level: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Min Stock</label>
              <input
                type="number" step="0.001" min="0"
                value={form.minimum_stock ?? '0.000'}
                onChange={e => setForm(f => ({ ...f, minimum_stock: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>
          <div className="flex gap-2 pt-1">
            <button type="submit" disabled={saving} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm disabled:opacity-50 hover:bg-brand-600">
              {saving ? 'Saving…' : 'Create Item'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600">
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Error / Loading */}
      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800">
                {['Name', 'SKU', 'Category', 'Unit', 'Reorder Level', 'Avg Cost', 'Status'].map(h => (
                  <th key={h} className="text-left text-xs text-gray-500 font-medium px-3 py-2">{h}</th>
                ))}
                {hasPermission('inventory.update') && <th className="px-3 py-2" />}
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 py-3 text-gray-200 font-medium">{item.name}</td>
                  <td className="px-3 py-3 text-gray-400 font-mono text-xs">{item.sku}</td>
                  <td className="px-3 py-3 text-gray-400">{item.category_name ?? '—'}</td>
                  <td className="px-3 py-3 text-gray-400">{item.default_unit}</td>
                  <td className="px-3 py-3 text-gray-400">{item.reorder_level}</td>
                  <td className="px-3 py-3 text-gray-300">₹{item.average_cost}</td>
                  <td className="px-3 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${item.is_active ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-gray-700 text-gray-500 border-gray-600'}`}>
                      {item.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  {hasPermission('inventory.update') && (
                    <td className="px-3 py-3">
                      <button
                        onClick={() => handleToggleActive(item)}
                        className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
                      >
                        {item.is_active ? 'Disable' : 'Enable'}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-gray-600 text-sm">No items found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
