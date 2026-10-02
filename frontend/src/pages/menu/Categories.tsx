// =============================================================================
// RestaurantFlow — Categories Page
// Phase 5
// =============================================================================

import { useState } from 'react'
import {
  useCategories,
  useCreateCategory,
  useUpdateCategory,
  useDisableCategory,
  useEnableCategory,
} from '@/hooks/useMenu'
import { useAllRestaurants as useRestaurants } from '@/hooks/useRestaurants'
import { PageHeader } from '@/components/ui/PageHeader'
import { Button } from '@/components/ui/Button'
import { Modal, ConfirmDialog } from '@/components/ui/Modal'
import { useToast } from '@/components/ui/Toast'
import { useAuth } from '@/contexts/AuthContext'
import type { Category, CategoryCreatePayload, CategoryUpdatePayload } from '@/types'

// ---------------------------------------------------------------------------
// Form
// ---------------------------------------------------------------------------

function CategoryForm({
  initialValues,
  onSubmit,
  onCancel,
  loading,
  submitLabel = 'Save',
}: {
  initialValues?: Partial<Category>
  onSubmit: (data: CategoryCreatePayload | CategoryUpdatePayload) => void
  onCancel: () => void
  loading?: boolean
  submitLabel?: string
}) {
  const { data: restaurantsData } = useRestaurants()
  const [form, setForm] = useState({
    restaurant: initialValues?.restaurant ?? '',
    name: initialValues?.name ?? '',
    description: initialValues?.description ?? '',
    display_order: String(initialValues?.display_order ?? 0),
  })

  const field = (key: keyof typeof form) => ({
    value: form[key],
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [key]: e.target.value })),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      ...form,
      display_order: Number(form.display_order),
    })
  }

  const inputClass =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder-gray-600'
  const labelClass = 'block text-xs text-gray-500 mb-1.5'

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {!initialValues?.id && (
        <div>
          <label className={labelClass}>Restaurant *</label>
          <select className={inputClass} {...field('restaurant')} required>
            <option value="">Select restaurant…</option>
            {restaurantsData?.results.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>
      )}
      <div>
        <label className={labelClass}>Name *</label>
        <input className={inputClass} placeholder="e.g. Veg, Non-Veg, Beverages" required {...field('name')} />
      </div>
      <div>
        <label className={labelClass}>Description</label>
        <textarea className={inputClass} rows={2} placeholder="Optional description…" {...field('description')} />
      </div>
      <div>
        <label className={labelClass}>Display Order</label>
        <input className={inputClass} type="number" min="0" placeholder="0" {...field('display_order')} />
        <p className="mt-1 text-xs text-gray-600">Lower numbers appear first in the menu.</p>
      </div>
      <div className="flex justify-end gap-3 pt-2">
        <Button variant="ghost" type="button" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={loading}>{submitLabel}</Button>
      </div>
    </form>
  )
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function Categories() {
  const { hasPermission } = useAuth()
  const { toast } = useToast()

  const [restaurantFilter, setRestaurantFilter] = useState('')
  const [activeFilter, setActiveFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [editTarget, setEditTarget] = useState<Category | null>(null)
  const [confirmAction, setConfirmAction] = useState<{
    type: 'disable' | 'enable'
    category: Category
  } | null>(null)

  const params: Record<string, string | number> = {}
  if (restaurantFilter) params.restaurant = restaurantFilter
  if (activeFilter !== '') params.is_active = activeFilter

  const { data, isLoading, isError } = useCategories(params)
  const { data: restaurantsData } = useRestaurants()
  const createMut = useCreateCategory()
  const updateMut = useUpdateCategory(editTarget?.id ?? '')
  const disableMut = useDisableCategory()
  const enableMut = useEnableCategory()

  const canCreate = hasPermission('category.create')
  const canUpdate = hasPermission('category.update')
  const canDisable = hasPermission('category.disable')

  async function handleCreate(payload: CategoryCreatePayload | CategoryUpdatePayload) {
    try {
      await createMut.mutateAsync(payload as CategoryCreatePayload)
      setShowCreate(false)
      toast('Category created.', 'success')
    } catch {
      toast('Failed to create category.', 'error')
    }
  }

  async function handleUpdate(payload: CategoryCreatePayload | CategoryUpdatePayload) {
    if (!editTarget) return
    try {
      await updateMut.mutateAsync(payload as CategoryUpdatePayload)
      setEditTarget(null)
      toast('Category updated.', 'success')
    } catch {
      toast('Failed to update category.', 'error')
    }
  }

  async function handleConfirm() {
    if (!confirmAction) return
    try {
      if (confirmAction.type === 'disable') {
        await disableMut.mutateAsync(confirmAction.category.id)
        toast(`"${confirmAction.category.name}" disabled.`, 'warning')
      } else {
        await enableMut.mutateAsync(confirmAction.category.id)
        toast(`"${confirmAction.category.name}" enabled.`, 'success')
      }
    } catch {
      toast('Action failed.', 'error')
    } finally {
      setConfirmAction(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <PageHeader
        title="Categories"
        crumbs={[{ label: 'Home', to: '/' }, { label: 'Menu', to: '/menu' }, { label: 'Categories' }]}
        actions={
          canCreate ? (
            <Button variant="primary" size="sm" onClick={() => setShowCreate(true)}>
              + Add Category
            </Button>
          ) : undefined
        }
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <select
          aria-label="Filter by restaurant"
          className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-500"
          value={restaurantFilter}
          onChange={(e) => setRestaurantFilter(e.target.value)}
        >
          <option value="">All Restaurants</option>
          {restaurantsData?.results.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
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
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-14 bg-gray-900/60 border border-gray-800 rounded-xl animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-xl bg-red-950/40 border border-red-800/50 px-5 py-4 text-sm text-red-400" role="alert">
          Failed to load categories.
        </div>
      )}

      {!isLoading && data?.results.length === 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 px-6 py-12 text-center">
          <p className="text-gray-500 text-sm">No categories found.</p>
          {canCreate && (
            <Button variant="primary" size="sm" className="mt-4" onClick={() => setShowCreate(true)}>
              Add your first category
            </Button>
          )}
        </div>
      )}

      {!isLoading && data && data.results.length > 0 && (
        <div className="rounded-xl bg-gray-900/60 border border-gray-800 overflow-hidden">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Order</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Name</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden sm:table-cell">Restaurant</th>
                <th className="text-right px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide hidden md:table-cell">Items</th>
                <th className="text-left px-4 py-3 text-xs text-gray-600 font-medium uppercase tracking-wide">Status</th>
                <th className="px-4 py-3" aria-label="Actions" />
              </tr>
            </thead>
            <tbody>
              {data.results.map((cat) => (
                <tr key={cat.id} className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors">
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                      {cat.display_order}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-gray-200 font-medium">{cat.name}</p>
                    {cat.description && (
                      <p className="text-xs text-gray-600 mt-0.5 truncate max-w-xs">{cat.description}</p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs hidden sm:table-cell">
                    {cat.restaurant_name}
                  </td>
                  <td className="px-4 py-3 text-right hidden md:table-cell">
                    <span className="text-gray-400 text-xs font-mono">{cat.item_count}</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${
                      cat.is_active
                        ? 'bg-green-500/10 text-green-400 border-green-500/20'
                        : 'bg-gray-700/30 text-gray-500 border-gray-700/30'
                    }`}>
                      {cat.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      {canUpdate && (
                        <Button variant="ghost" size="sm" onClick={() => setEditTarget(cat)}>Edit</Button>
                      )}
                      {canDisable && cat.is_active && (
                        <Button
                          variant="danger"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'disable', category: cat })}
                        >
                          Disable
                        </Button>
                      )}
                      {canCreate && !cat.is_active && (
                        <Button
                          variant="success"
                          size="sm"
                          onClick={() => setConfirmAction({ type: 'enable', category: cat })}
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
            {data.count} categor{data.count !== 1 ? 'ies' : 'y'}
          </div>
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Add Category">
        <CategoryForm onSubmit={handleCreate} onCancel={() => setShowCreate(false)} loading={createMut.isPending} submitLabel="Create Category" />
      </Modal>

      <Modal open={!!editTarget} onClose={() => setEditTarget(null)} title="Edit Category">
        {editTarget && (
          <CategoryForm initialValues={editTarget} onSubmit={handleUpdate} onCancel={() => setEditTarget(null)} loading={updateMut.isPending} submitLabel="Save Changes" />
        )}
      </Modal>

      <ConfirmDialog
        open={!!confirmAction}
        onClose={() => setConfirmAction(null)}
        onConfirm={handleConfirm}
        title={
          confirmAction?.type === 'disable'
            ? `Disable "${confirmAction.category.name}"?`
            : `Enable "${confirmAction?.category.name}"?`
        }
        message={
          confirmAction?.type === 'disable'
            ? 'This category will be hidden from the menu catalog.'
            : 'This category will be visible in the menu catalog again.'
        }
        confirmLabel={confirmAction?.type === 'disable' ? 'Disable' : 'Enable'}
        confirmVariant={confirmAction?.type === 'disable' ? 'danger' : 'success'}
        loading={disableMut.isPending || enableMut.isPending}
      />
    </div>
  )
}
