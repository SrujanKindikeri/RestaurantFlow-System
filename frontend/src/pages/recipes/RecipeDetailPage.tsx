// =============================================================================
// RestaurantFlow — Recipe Detail Page
// Phase 11
//
// Shows full recipe with ingredient builder, cost estimate, and version history.
// =============================================================================

import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  useRecipe,
  useRecipeCost,
  useActivateRecipe,
  useArchiveRecipe,
  useAddRecipeIngredient,
  useUpdateRecipeIngredient,
  useRemoveRecipeIngredient,
  useRecipesByMenuItem,
} from '@/hooks/useRecipes'
import type { AddRecipeItemPayload, RecipeItem, UnitOfMeasurement } from '@/types'
import { useAuth } from '@/contexts/AuthContext'
import { listInventoryItems } from '@/services/inventory'
import { useEffect } from 'react'
import type { InventoryItem } from '@/types'

const UNITS: UnitOfMeasurement[] = ['KG', 'GRAM', 'LITRE', 'MILLILITRE', 'PIECE', 'PACK', 'BOX', 'BOTTLE', 'DOZEN']

const STATUS_BADGE: Record<string, string> = {
  DRAFT:    'bg-gray-500/10 text-gray-400 border-gray-500/20',
  ACTIVE:   'bg-green-500/10 text-green-400 border-green-500/20',
  INACTIVE: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  ARCHIVED: 'bg-red-500/10 text-red-400 border-red-500/20',
}

export function RecipeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { hasPermission, user } = useAuth()
  const navigate = useNavigate()

  const { data: recipe, isLoading, error } = useRecipe(id!)
  const { data: cost } = useRecipeCost(id!, recipe?.status !== 'ARCHIVED')
  const { data: versions = [] } = useRecipesByMenuItem(recipe?.menu_item ?? '')

  const activate = useActivateRecipe()
  const archive = useArchiveRecipe()
  const addIngredient = useAddRecipeIngredient(id!)
  const removeIngredient = useRemoveRecipeIngredient(id!)

  const [actionError, setActionError] = useState<string | null>(null)
  const [showAddIngredient, setShowAddIngredient] = useState(false)
  const [inventoryItems, setInventoryItems] = useState<InventoryItem[]>([])
  const [addForm, setAddForm] = useState<Partial<AddRecipeItemPayload>>({
    quantity: '0',
    unit: 'GRAM',
    preparation_loss_percentage: '0',
    notes: '',
    display_order: 0,
  })
  const [addError, setAddError] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  useEffect(() => {
    if (!restaurantId) return
    listInventoryItems({ restaurant: restaurantId, is_active: 'true' })
      .then(r => setInventoryItems(r.data))
      .catch(() => {})
  }, [restaurantId])

  const handleActivate = async () => {
    setActionError(null)
    try { await activate.mutateAsync(id!) }
    catch (e: any) { setActionError(e?.response?.data?.message ?? 'Failed to activate') }
  }

  const handleArchive = async () => {
    if (!confirm('Archive this recipe?')) return
    setActionError(null)
    try { await archive.mutateAsync(id!) }
    catch (e: any) { setActionError(e?.response?.data?.message ?? 'Failed to archive') }
  }

  const handleRemoveIngredient = async (itemId: string) => {
    if (!confirm('Remove this ingredient?')) return
    try { await removeIngredient.mutateAsync(itemId) }
    catch (e: any) { setActionError(e?.response?.data?.message ?? 'Failed to remove ingredient') }
  }

  const handleAddIngredient = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!addForm.inventory_item_id) { setAddError('Select an ingredient'); return }
    setAdding(true)
    setAddError(null)
    try {
      await addIngredient.mutateAsync(addForm as AddRecipeItemPayload)
      setShowAddIngredient(false)
      setAddForm({ quantity: '0', unit: 'GRAM', preparation_loss_percentage: '0', notes: '', display_order: 0 })
    } catch (e: any) {
      setAddError(e?.response?.data?.message ?? 'Failed to add ingredient')
    } finally { setAdding(false) }
  }

  if (isLoading) return <div className="p-6 text-gray-400">Loading…</div>
  if (error || !recipe) return <div className="p-6 text-red-400">Recipe not found.</div>

  const isDraft = recipe.status === 'DRAFT'
  const canEdit = isDraft && hasPermission('recipe.update')

  return (
    <div className="p-6 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-400">
        <Link to="/recipes" className="hover:text-white">Recipes</Link>
        <span>/</span>
        <span className="text-white">{recipe.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-white">{recipe.name}</h1>
            <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-medium ${STATUS_BADGE[recipe.status]}`}>
              {recipe.status}
            </span>
            <span className="text-gray-500 text-sm">v{recipe.version}</span>
          </div>
          <p className="text-gray-400 mt-1">
            {recipe.menu_item_name} · Yield: {recipe.yield_quantity} {recipe.yield_unit}
          </p>
        </div>
        <div className="flex gap-2">
          {isDraft && hasPermission('recipe.activate') && (
            <button
              onClick={handleActivate}
              className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium"
            >
              Activate Recipe
            </button>
          )}
          {recipe.status !== 'ARCHIVED' && hasPermission('recipe.archive') && (
            <button
              onClick={handleArchive}
              className="bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/20 px-4 py-2 rounded-lg text-sm font-medium"
            >
              Archive
            </button>
          )}
          {isDraft && hasPermission('recipe.update') && (
            <Link
              to={`/recipes/${id}/edit`}
              className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-medium"
            >
              Edit Draft
            </Link>
          )}
        </div>
      </div>

      {actionError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm">{actionError}</div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Ingredients */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700">
              <h2 className="text-white font-medium">Ingredients</h2>
              {canEdit && (
                <button
                  onClick={() => setShowAddIngredient(v => !v)}
                  className="text-brand-400 hover:text-brand-300 text-sm"
                >
                  + Add Ingredient
                </button>
              )}
            </div>

            {/* Add Ingredient Form */}
            {showAddIngredient && (
              <form onSubmit={handleAddIngredient} className="p-4 border-b border-gray-700 bg-gray-750 space-y-3">
                {addError && <div className="text-red-400 text-xs">{addError}</div>}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Ingredient *</label>
                    <select
                      value={addForm.inventory_item_id ?? ''}
                      onChange={e => setAddForm(f => ({ ...f, inventory_item_id: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1.5 text-sm"
                      required
                    >
                      <option value="">Select ingredient…</option>
                      {inventoryItems.map(item => (
                        <option key={item.id} value={item.id}>
                          {item.name} ({item.sku}) — {item.default_unit}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Quantity *</label>
                      <input
                        type="number" step="0.001" min="0.001"
                        value={addForm.quantity ?? ''}
                        onChange={e => setAddForm(f => ({ ...f, quantity: e.target.value }))}
                        className="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1.5 text-sm"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Unit *</label>
                      <select
                        value={addForm.unit ?? 'GRAM'}
                        onChange={e => setAddForm(f => ({ ...f, unit: e.target.value as UnitOfMeasurement }))}
                        className="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1.5 text-sm"
                      >
                        {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
                      </select>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Preparation Loss %</label>
                    <input
                      type="number" step="0.001" min="0" max="99.999"
                      value={addForm.preparation_loss_percentage ?? '0'}
                      onChange={e => setAddForm(f => ({ ...f, preparation_loss_percentage: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1.5 text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">Notes</label>
                    <input
                      type="text"
                      value={addForm.notes ?? ''}
                      onChange={e => setAddForm(f => ({ ...f, notes: e.target.value }))}
                      className="w-full bg-gray-700 border border-gray-600 text-white rounded px-2 py-1.5 text-sm"
                      placeholder="Optional preparation note"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button type="submit" disabled={adding}
                    className="bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded text-sm disabled:opacity-50">
                    {adding ? 'Adding…' : 'Add Ingredient'}
                  </button>
                  <button type="button" onClick={() => setShowAddIngredient(false)}
                    className="text-gray-400 hover:text-white text-sm px-3 py-1.5">
                    Cancel
                  </button>
                </div>
              </form>
            )}

            {/* Ingredients Table */}
            {recipe.ingredients.length === 0 ? (
              <div className="p-6 text-center text-gray-400 text-sm">
                No ingredients yet.
                {canEdit && <span className="ml-1">Use <strong>+ Add Ingredient</strong> to build this recipe.</span>}
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 text-xs uppercase tracking-wider border-b border-gray-700">
                    <th className="text-left px-4 py-2">Ingredient</th>
                    <th className="text-right px-4 py-2">Quantity</th>
                    <th className="text-center px-4 py-2">Unit</th>
                    <th className="text-center px-4 py-2">Loss %</th>
                    <th className="text-right px-4 py-2">Effective Qty</th>
                    {canEdit && <th className="px-4 py-2" />}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {recipe.ingredients.map((item: RecipeItem) => (
                    <tr key={item.id} className="hover:bg-gray-700/20">
                      <td className="px-4 py-2.5 text-white">
                        {item.inventory_item_name}
                        <span className="ml-1 text-gray-500 text-xs">({item.inventory_item_sku})</span>
                      </td>
                      <td className="px-4 py-2.5 text-right text-gray-300">{item.quantity}</td>
                      <td className="px-4 py-2.5 text-center text-gray-400">{item.unit}</td>
                      <td className="px-4 py-2.5 text-center text-gray-400">{item.preparation_loss_percentage}%</td>
                      <td className="px-4 py-2.5 text-right text-gray-300">{item.effective_quantity} {item.unit}</td>
                      {canEdit && (
                        <td className="px-4 py-2.5 text-right">
                          <button
                            onClick={() => handleRemoveIngredient(item.id)}
                            className="text-red-400 hover:text-red-300 text-xs"
                          >
                            Remove
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Preparation Notes */}
          {recipe.preparation_notes && (
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <h3 className="text-white font-medium mb-2 text-sm">Preparation Notes</h3>
              <p className="text-gray-400 text-sm whitespace-pre-wrap">{recipe.preparation_notes}</p>
            </div>
          )}
        </div>

        {/* Right column: Cost + Version History */}
        <div className="space-y-4">
          {/* Estimated Cost */}
          {cost && hasPermission('recipe.cost.view') && (
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
              <h3 className="text-white font-medium mb-3 text-sm">Estimated Cost</h3>
              <div className="space-y-1.5">
                {cost.ingredients.map(ing => (
                  <div key={ing.inventory_item_id} className="flex justify-between text-xs text-gray-400">
                    <span>{ing.inventory_item_name}</span>
                    <span>₹{ing.line_cost}</span>
                  </div>
                ))}
              </div>
              <div className="border-t border-gray-700 mt-3 pt-3 flex justify-between">
                <span className="text-white text-sm font-medium">Total</span>
                <span className="text-brand-400 font-bold">₹{cost.total_cost}</span>
              </div>
            </div>
          )}

          {/* Version History */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4">
            <h3 className="text-white font-medium mb-3 text-sm">Version History</h3>
            <div className="space-y-2">
              {versions.map(v => (
                <Link
                  key={v.id}
                  to={`/recipes/${v.id}`}
                  className={`flex items-center justify-between p-2 rounded-lg text-xs transition-colors ${
                    v.id === id
                      ? 'bg-brand-600/10 border border-brand-500/20'
                      : 'hover:bg-gray-700/50'
                  }`}
                >
                  <span className="text-gray-300">v{v.version} — {v.name}</span>
                  <span className={`px-1.5 py-0.5 rounded border text-xs ${STATUS_BADGE[v.status]}`}>
                    {v.status}
                  </span>
                </Link>
              ))}
            </div>
          </div>

          {/* Recipe Metadata */}
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-2 text-xs text-gray-400">
            <div className="flex justify-between">
              <span>Created by</span>
              <span className="text-gray-300">{recipe.created_by_email ?? '—'}</span>
            </div>
            {recipe.approved_by_email && (
              <div className="flex justify-between">
                <span>Approved by</span>
                <span className="text-gray-300">{recipe.approved_by_email}</span>
              </div>
            )}
            {recipe.approved_at && (
              <div className="flex justify-between">
                <span>Approved at</span>
                <span className="text-gray-300">{new Date(recipe.approved_at).toLocaleString()}</span>
              </div>
            )}
            {recipe.effective_from && (
              <div className="flex justify-between">
                <span>Effective from</span>
                <span className="text-gray-300">{new Date(recipe.effective_from).toLocaleDateString()}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
