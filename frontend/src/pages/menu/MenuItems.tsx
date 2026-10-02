// =============================================================================
// RestaurantFlow — Menu Items Page
// Phase 5
// =============================================================================

import { useState } from 'react'
import {
  useMenuItems,
  useCreateMenuItem,
  useUpdateMenuItem,
  useDisableMenuItem,
  useEnableMenuItem,
} from '@/hooks/useMenu'
import { useCategories } from '@/hooks/useMenu'
import { useAllRestaurants as useRestaurants } from '@/hooks/useRestaurants'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/contexts/AuthContext'
import { MenuItemForm } from './MenuItemForm'
import type { MenuItem, MenuItemCreatePayload, MenuItemUpdatePayload, FoodType } from '@/types'

const FOOD_TYPE_COLORS: Record<FoodType, string> = {
  VEG:     'bg-green-500/10 text-green-400 border-green-500/20',
  NON_VEG: 'bg-red-500/10 text-red-400 border-red-500/20',
  EGG:     'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  VEGAN:   'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
  OTHER:   'bg-gray-700/30 text-gray-400 border-gray-700/30',
}

const FOOD_TYPE_LABELS: Record<FoodType, string> = {
  VEG: 'Veg', NON_VEG: 'Non-Veg', EGG: 'Egg', VEGAN: 'Vegan', OTHER: 'Other',
}

export function MenuItems() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()

  const [restaurantFilter, setRestaurantFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [foodTypeFilter, setFoodTypeFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState('')
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<MenuItem | null>(null)
  const [confirmAction, setConfirmAction] = useState<{
    type: 'disable' | 'enable'
    item: MenuItem
  } | null>(null)

  const params: Record<string, string | number> = {}
  if (restaurantFilter) params.restaurant = restaurantFilter
  if (categoryFilter) params.category = categoryFilter
  if (foodTypeFilter) params.food_type = foodTypeFilter
  if (activeFilter !== '') params.is_active = activeFilter
  if (search) params.search = search

  const { data, isLoading, isError } = useMenuItems(params)
  const { data: restaurantsData } = useRestaurants()
  const { data: categoriesData } = useCategories(
    restaurantFilter ? { restaurant: restaurantFilter } : undefined
  )
  const createMut = useCreateMenuItem()
  const updateMut = useUpdateMenuItem(editTarget?.id ?? '')
  const disableMut = useDisableMenuItem()
  const enableMut = useEnableMenuItem()

  const canCreate = hasPermission('menu.create')
  const canUpdate = hasPermission('menu.update')
  const canDisable = hasPermission('menu.disable')

  async function handleCreate(payload: MenuItemCreatePayload | MenuItemUpdatePayload) {
    try {
      await createMut.mutateAsync(payload as MenuItemCreatePayload)
      setShowCreate(false)
      toast('Menu item created.', 'success')
    } catch {
      toast('Failed to create menu item.', 'error')
    }
  }

  async function handleUpdate(payload: MenuItemCreatePayload | MenuItemUpdatePayload) {
    if (!editTarget) return
    try {
      await updateMut.mutateAsync(payload as MenuItemUpdatePayload)
      setEditTarget(null)
      toast('Menu item updated.', 'success')
    } catch {
      toast('Failed to update menu item.', 'error')
    }
  }

  async function handleConfirm() {
    if (!confirmAction) return
    try {
      if (confirmAction.type === 'disable') {
        await disableMut.mutateAsync(confirmAction.item.id)
        toast(`"${confirmAction.item.name}" disabled.`, 'warning')
      } else {
        await enableMut.mutateAsync(confirmAction.item.id)
        toast(`"${confirmAction.item.name}" enabled.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmAction(null)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Menu Items"
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Menu', to: '/menu' }, { label: 'Items' }]}
        actions={
          canCreate ? (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              + Add Item
            </Button>
          ) : undefined
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="search"
          aria-label="Search menu items"
          placeholder="Search name, SKU…"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500 w-40"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Filter by restaurant"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={restaurantFilter}
          onChange={(e) => { setRestaurantFilter(e.target.value); setCategoryFilter('') }}
        >
          <option value="">All Restaurants</option>
          {restaurantsData?.results.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <select
          aria-label="Filter by category"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="">All Categories</option>
          {categoriesData?.results.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <select
          aria-label="Filter by food type"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={foodTypeFilter}
          onChange={(e) => setFoodTypeFilter(e.target.value)}
        >
          <option value="">All Types</option>
          <option value="VEG">Veg</option>
          <option value="NON_VEG">Non-Veg</option>
          <option value="EGG">Egg</option>
          <option value="VEGAN">Vegan</option>
          <option value="OTHER">Other</option>
        </select>
        <select
          aria-label="Filter by status"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load menu items.
        </div>
      )}

      {!isLoading && data?.results.length === 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-12 text-center">
          <p className="text-gray-500 text-sm">No menu items found.</p>
          {canCreate && (
            <Button variant="primary" size="sm" className="mt-4" onClick={() => setShowCreate(true)}>
              Add your first item
            </Button>
          )}
        </div>
      )}

      {!isLoading && data && data.results.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-hidden">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Item</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden sm:table-cell">SKU</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden md:table-cell">Category</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Type</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden lg:table-cell">Tax</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Status</th>
                <th className="px-4 py-3" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {data.results.map((item) => (
                <tr key={item.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-gray-200 font-medium">{item.name}</p>
                    {item.short_description && (
                      <p className="text-xs text-gray-600 mt-0.5 truncate max-w-xs">{item.short_description}</p>
                    )}
                    <p className="text-xs text-gray-700 mt-0.5">{item.restaurant_name}</p>
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    {item.sku && (
                      <span className="font-mono text-xs text-gray-400 bg-gray-800 px-2 py-0.5 rounded">
                        {item.sku}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs hidden md:table-cell">
                    {item.category_name}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${FOOD_TYPE_COLORS[item.food_type]}`}>
                      {FOOD_TYPE_LABELS[item.food_type]}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden lg:table-cell">
                    {item.tax_rate_detail ? (
                      <span className="text-xs text-gray-500 font-mono">
                        {item.tax_rate_detail.code} ({Number(item.tax_rate_detail.rate).toFixed(1)}%)
                      </span>
                    ) : (
                      <span className="text-xs text-gray-700">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      <span className={`text-xs px-2 py-0.5 rounded-full border w-fit ${
                        item.is_active
                          ? 'bg-green-500/10 text-green-400 border-green-500/20'
                          : 'bg-gray-700/30 text-gray-500 border-gray-700/30'
                      }`}>
                        {item.is_active ? 'Active' : 'Inactive'}
                      </span>
                      {item.is_active && (
                        <span className={`text-xs px-2 py-0.5 rounded-full border w-fit ${
                          item.is_available
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                            : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                        }`}>
                          {item.is_available ? 'Available' : 'Unavailable'}
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {canUpdate && (
                        <Button variant="ghost" size="sm" onClick={() => setEditTarget(item)}>Edit</Button>
                      )}
                      {canDisable && item.is_active && (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'disable', item })}
                        >
                          Disable
                        </Button>
                      )}
                      {canCreate && !item.is_active && (
                        <Button
                          variant="success"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'enable', item })}
                        >
                          Enable
                        </Button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-gray-800 text-xs text-gray-700">
            {data.count} item{data.count !== 1 ? 's' : ''}
          </div>
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Menu Item" size="lg">
        <MenuItemForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          loading={createMut.isPending}
          submitLabel="Create Item"
        />
      </Modal>

      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Edit Menu Item" size="lg">
        {editTarget && (
          <MenuItemForm
            initialValues={editTarget}
            onSubmit={handleUpdate}
            onCancel={() => setEditTarget(null)}
            loading={updateMut.isPending}
            submitLabel="Save Changes"
          />
        )}
      </Modal>

      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirm}
        title={
          confirmAction?.type === 'disable'
            ? `Disable "${confirmAction.item.name}"?`
            : `Enable "${confirmAction?.item.name}"?`
        }
        message={
          confirmAction?.type === 'disable'
            ? 'This item will be removed from all branch catalogs. Existing order history is preserved.'
            : 'This item will be restored to the catalog.'
        }
        confirmLabel={confirmAction?.type === 'disable' ? 'Disable' : 'Enable'}
        confirmVariant={confirmAction?.type === 'disable' ? 'danger' : 'success'}
        loading={disableMut.isPending || enableMut.isPending}
      />
    </div>
  )
}
