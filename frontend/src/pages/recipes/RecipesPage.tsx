// =============================================================================
// RestaurantFlow — Recipes Management Page
// Phase 11
//
// Lists all recipes with search/filter by status.
// Actions: Create, View, Activate, Archive.
// =============================================================================

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useRecipes, useActivateRecipe, useArchiveRecipe } from '@/hooks/useRecipes'
import type { RecipeListParams, RecipeStatus } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_BADGE: Record<RecipeStatus, string> = {
  DRAFT:    'bg-gray-500/10 text-gray-400 border-gray-500/20',
  ACTIVE:   'bg-green-500/10 text-green-400 border-green-500/20',
  INACTIVE: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  ARCHIVED: 'bg-red-500/10 text-red-400 border-red-500/20',
}

const STATUS_LABELS: Record<RecipeStatus, string> = {
  DRAFT: 'Draft', ACTIVE: 'Active', INACTIVE: 'Inactive', ARCHIVED: 'Archived',
}

export function RecipesPage() {
  const { user, hasPermission } = useAuth()
  const [params, setParams] = useState<RecipeListParams>({})
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<RecipeStatus | ''>('')

  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  useEffect(() => {
    const p: RecipeListParams = {}
    if (restaurantId) p.restaurant = restaurantId
    if (search) p.search = search
    if (statusFilter) p.status = statusFilter
    setParams(p)
  }, [restaurantId, search, statusFilter])

  const { data: recipes = [], isLoading, error, refetch } = useRecipes(params)
  const activate = useActivateRecipe()
  const archive = useArchiveRecipe()

  const [actionError, setActionError] = useState<string | null>(null)

  const handleActivate = async (id: string) => {
    setActionError(null)
    try {
      await activate.mutateAsync(id)
    } catch (e: any) {
      setActionError(e?.response?.data?.message ?? 'Failed to activate recipe')
    }
  }

  const handleArchive = async (id: string) => {
    if (!confirm('Archive this recipe? This action cannot be undone easily.')) return
    setActionError(null)
    try {
      await archive.mutateAsync(id)
    } catch (e: any) {
      setActionError(e?.response?.data?.message ?? 'Failed to archive recipe')
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Recipes</h1>
          <p className="text-sm text-gray-400 mt-1">
            Manage ingredient recipes for menu items
          </p>
        </div>
        {hasPermission('recipe.create') && (
          <Link
            to="/recipes/new"
            className="bg-brand-600 hover:bg-brand-700 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            + New Recipe
          </Link>
        )}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <input
          type="text"
          placeholder="Search by name or menu item…"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm w-64 focus:outline-none focus:border-brand-500"
        />
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value as RecipeStatus | '')}
          className="bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-500"
        >
          <option value="">All statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="ACTIVE">Active</option>
          <option value="INACTIVE">Inactive</option>
          <option value="ARCHIVED">Archived</option>
        </select>
      </div>

      {/* Error */}
      {actionError && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm">
          {actionError}
        </div>
      )}

      {/* Table */}
      {isLoading ? (
        <div className="text-gray-400 text-sm">Loading recipes…</div>
      ) : error ? (
        <div className="text-red-400 text-sm">Failed to load recipes.</div>
      ) : recipes.length === 0 ? (
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-8 text-center">
          <p className="text-gray-400">No recipes found.</p>
          {hasPermission('recipe.create') && (
            <Link to="/recipes/new" className="text-brand-400 hover:text-brand-300 text-sm mt-2 inline-block">
              Create your first recipe →
            </Link>
          )}
        </div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-gray-400 text-xs uppercase tracking-wider">
                <th className="text-left px-4 py-3">Menu Item</th>
                <th className="text-left px-4 py-3">Recipe Name</th>
                <th className="text-center px-4 py-3">Version</th>
                <th className="text-center px-4 py-3">Status</th>
                <th className="text-center px-4 py-3">Ingredients</th>
                <th className="text-left px-4 py-3">Effective From</th>
                <th className="text-left px-4 py-3">Created By</th>
                <th className="text-right px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {recipes.map(recipe => (
                <tr key={recipe.id} className="hover:bg-gray-700/30 transition-colors">
                  <td className="px-4 py-3 text-white font-medium">{recipe.menu_item_name}</td>
                  <td className="px-4 py-3 text-gray-300">{recipe.name}</td>
                  <td className="px-4 py-3 text-center text-gray-400">v{recipe.version}</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex px-2 py-0.5 rounded border text-xs font-medium ${STATUS_BADGE[recipe.status]}`}>
                      {STATUS_LABELS[recipe.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-400">{recipe.ingredient_count}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {recipe.effective_from
                      ? new Date(recipe.effective_from).toLocaleDateString()
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {recipe.created_by_email ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right space-x-2">
                    <Link
                      to={`/recipes/${recipe.id}`}
                      className="text-brand-400 hover:text-brand-300 text-xs"
                    >
                      View
                    </Link>
                    {recipe.status === 'DRAFT' && hasPermission('recipe.activate') && (
                      <button
                        onClick={() => handleActivate(recipe.id)}
                        className="text-green-400 hover:text-green-300 text-xs ml-2"
                      >
                        Activate
                      </button>
                    )}
                    {recipe.status !== 'ARCHIVED' && hasPermission('recipe.archive') && (
                      <button
                        onClick={() => handleArchive(recipe.id)}
                        className="text-red-400 hover:text-red-300 text-xs ml-2"
                      >
                        Archive
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
