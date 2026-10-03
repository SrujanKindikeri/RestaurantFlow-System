// =============================================================================
// RestaurantFlow — Create Recipe Page
// Phase 11
// =============================================================================

import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useCreateRecipe } from '@/hooks/useRecipes'
import { listMenuItems } from '@/services/menu'
import type { MenuItem, CreateRecipePayload, UnitOfMeasurement } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const UNITS: UnitOfMeasurement[] = ['KG', 'GRAM', 'LITRE', 'MILLILITRE', 'PIECE', 'PACK', 'BOX', 'BOTTLE', 'DOZEN']

export function CreateRecipePage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const createRecipe = useCreateRecipe()

  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [menuItems, setMenuItems] = useState<MenuItem[]>([])
  const [form, setForm] = useState<Partial<CreateRecipePayload>>({
    restaurant_id: restaurantId,
    yield_quantity: '1.000',
    yield_unit: 'PIECE',
    preparation_notes: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!restaurantId) return
    listMenuItems({ restaurant: restaurantId, is_active: 'true' })
      .then(r => setMenuItems(r.data?.results ?? r.data ?? []))
      .catch(() => {})
  }, [restaurantId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.menu_item_id) { setError('Select a menu item'); return }
    if (!form.name?.trim()) { setError('Recipe name is required'); return }
    setSaving(true)
    setError(null)
    try {
      const created = await createRecipe.mutateAsync({
        ...form,
        restaurant_id: restaurantId,
      } as CreateRecipePayload)
      navigate(`/recipes/${created.id}`)
    } catch (e: any) {
      const detail = e?.response?.data
      setError(detail?.message ?? 'Failed to create recipe')
    } finally { setSaving(false) }
  }

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <Link to="/recipes" className="hover:text-white">Recipes</Link>
        <span>/</span>
        <span className="text-white">New Recipe</span>
      </div>

      <h1 className="text-2xl font-bold text-white">Create Recipe</h1>

      <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-5">
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm">{error}</div>
        )}

        {/* Menu Item */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Menu Item *</label>
          <select
            value={form.menu_item_id ?? ''}
            onChange={e => setForm(f => ({ ...f, menu_item_id: e.target.value }))}
            className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
            required
          >
            <option value="">Select a menu item…</option>
            {menuItems.map(item => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">Only active menu items can have recipes.</p>
        </div>

        {/* Name */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Recipe Name *</label>
          <input
            type="text"
            value={form.name ?? ''}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            placeholder="e.g. Chicken Biryani Standard"
            className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
            required
          />
        </div>

        {/* Yield */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Yield Quantity *</label>
            <input
              type="number" step="0.001" min="0.001"
              value={form.yield_quantity ?? '1.000'}
              onChange={e => setForm(f => ({ ...f, yield_quantity: e.target.value }))}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Yield Unit *</label>
            <select
              value={form.yield_unit ?? 'PIECE'}
              onChange={e => setForm(f => ({ ...f, yield_unit: e.target.value as UnitOfMeasurement }))}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
            >
              {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>

        {/* Preparation Notes */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Preparation Notes</label>
          <textarea
            value={form.preparation_notes ?? ''}
            onChange={e => setForm(f => ({ ...f, preparation_notes: e.target.value }))}
            rows={3}
            placeholder="Optional cooking instructions visible to kitchen…"
            className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500 resize-none"
          />
        </div>

        {/* Effective dates */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Effective From</label>
            <input
              type="datetime-local"
              value={form.effective_from ?? ''}
              onChange={e => setForm(f => ({ ...f, effective_from: e.target.value || null }))}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Effective To</label>
            <input
              type="datetime-local"
              value={form.effective_to ?? ''}
              onChange={e => setForm(f => ({ ...f, effective_to: e.target.value || null }))}
              className="w-full bg-gray-700 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="submit"
            disabled={saving}
            className="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {saving ? 'Creating…' : 'Save Draft'}
          </button>
          <Link to="/recipes" className="text-gray-400 hover:text-white text-sm px-4 py-2">
            Cancel
          </Link>
        </div>
      </form>

      <div className="bg-gray-800/50 border border-gray-700/50 rounded-xl p-4 text-xs text-gray-500">
        <strong className="text-gray-400">Next step:</strong> After saving the draft, open it to add ingredients using the Recipe Builder, then activate it.
      </div>
    </div>
  )
}
