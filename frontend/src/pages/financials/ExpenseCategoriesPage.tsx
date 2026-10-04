// =============================================================================
// RestaurantFlow — Expense Categories Page
// Phase 12
// =============================================================================

import { useEffect, useState } from 'react'
import { listExpenseCategories, createExpenseCategory, updateExpenseCategory } from '@/services/financials'
import type { ExpenseCategory, CreateExpenseCategoryPayload } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

export function ExpenseCategoriesPage() {
  const { user, hasPermission } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [categories, setCategories] = useState<ExpenseCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<ExpenseCategory | null>(null)
  const [form, setForm] = useState<Partial<CreateExpenseCategoryPayload>>({})
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const load = () => {
    if (!restaurantId) return
    setLoading(true)
    listExpenseCategories({ restaurant: restaurantId })
      .then(setCategories)
      .catch((e) => setError(e?.response?.data?.message ?? 'Failed to load categories'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [restaurantId])

  const openCreate = () => {
    setEditing(null)
    setForm({ restaurant: restaurantId, is_active: true })
    setFormError(null)
    setShowForm(true)
  }

  const openEdit = (cat: ExpenseCategory) => {
    setEditing(cat)
    setForm({ name: cat.name, description: cat.description, is_active: cat.is_active })
    setFormError(null)
    setShowForm(true)
  }

  const handleSave = async () => {
    if (!form.name?.trim()) { setFormError('Name is required.'); return }
    setSaving(true)
    setFormError(null)
    try {
      if (editing) {
        await updateExpenseCategory(editing.id, { name: form.name, description: form.description, is_active: form.is_active })
      } else {
        if (!form.code?.trim()) { setFormError('Code is required.'); setSaving(false); return }
        await createExpenseCategory(form as CreateExpenseCategoryPayload)
      }
      setShowForm(false)
      load()
    } catch (e: any) {
      setFormError(e?.response?.data?.message ?? 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const canCreate = hasPermission('expense.category.create')
  const canUpdate = hasPermission('expense.category.update')

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Expense Categories</h1>
          <p className="text-sm text-gray-500 mt-1">Manage category codes for your restaurant</p>
        </div>
        {canCreate && (
          <button onClick={openCreate}
            className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium rounded-lg">
            + New Category
          </button>
        )}
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="bg-gray-800 border border-gray-700 rounded-xl h-14 animate-pulse" />)}</div>
      ) : categories.length === 0 ? (
        <div className="text-center py-12 text-gray-600">No categories yet.</div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-xl divide-y divide-gray-700">
          {categories.map((cat) => (
            <div key={cat.id} className="flex items-center justify-between px-5 py-4">
              <div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">{cat.code}</span>
                  <span className="text-sm font-medium text-white">{cat.name}</span>
                  {!cat.is_active && (
                    <span className="text-xs text-gray-500 bg-gray-700 px-2 py-0.5 rounded">Inactive</span>
                  )}
                </div>
                {cat.description && <p className="text-xs text-gray-500 mt-0.5">{cat.description}</p>}
              </div>
              {canUpdate && (
                <button onClick={() => openEdit(cat)}
                  className="text-xs text-gray-400 hover:text-white border border-gray-700 rounded px-2 py-1">
                  Edit
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/80">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 w-full max-w-md">
            <h3 className="text-lg font-semibold text-white mb-4">
              {editing ? 'Edit Category' : 'New Category'}
            </h3>

            <div className="space-y-4">
              {!editing && (
                <div>
                  <label className="block text-sm text-gray-400 mb-1.5">Code <span className="text-red-400">*</span></label>
                  <input
                    type="text"
                    value={form.code ?? ''}
                    onChange={(e) => setForm((p) => ({ ...p, code: e.target.value.toUpperCase() }))}
                    placeholder="e.g. RENT"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500 uppercase"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Name <span className="text-red-400">*</span></label>
                <input
                  type="text"
                  value={form.name ?? ''}
                  onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1.5">Description</label>
                <textarea
                  rows={2}
                  value={form.description ?? ''}
                  onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
                />
              </div>
              {editing && (
                <label className="flex items-center gap-2 cursor-pointer">
                  <input type="checkbox" checked={form.is_active ?? true}
                    onChange={(e) => setForm((p) => ({ ...p, is_active: e.target.checked }))}
                    className="rounded" />
                  <span className="text-sm text-gray-400">Active</span>
                </label>
              )}
            </div>

            {formError && <p className="text-xs text-red-400 mt-3">{formError}</p>}

            <div className="flex gap-3 mt-5">
              <button onClick={handleSave} disabled={saving}
                className="flex-1 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium rounded-lg disabled:opacity-50">
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button onClick={() => setShowForm(false)}
                className="flex-1 py-2 bg-gray-800 border border-gray-700 text-gray-300 text-sm rounded-lg">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
