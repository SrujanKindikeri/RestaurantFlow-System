// =============================================================================
// RestaurantFlow — Create Expense Page
// Phase 12
// =============================================================================

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createExpense, listExpenseCategories } from '@/services/financials'
import type { ExpenseCategory, CreateExpensePayload } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

export function CreateExpensePage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const [categories, setCategories] = useState<ExpenseCategory[]>([])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const [form, setForm] = useState<Partial<CreateExpensePayload>>({
    restaurant: restaurantId,
    amount: '',
    tax_amount: '0.00',
    expense_date: new Date().toISOString().slice(0, 10),
    title: '',
    vendor_name: '',
    vendor_reference: '',
    description: '',
    notes: '',
  })

  useEffect(() => {
    if (!restaurantId) return
    listExpenseCategories({ restaurant: restaurantId, is_active: 'true' })
      .then(setCategories)
      .catch(() => {})
  }, [restaurantId])

  const set = (field: string, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }))

  const total = (Number(form.amount ?? 0) + Number(form.tax_amount ?? 0)).toFixed(2)

  const handleSubmit = async (action: 'draft' | 'submit') => {
    setError(null)
    setFieldErrors({})

    if (!form.category) { setFieldErrors({ category: 'Required' }); return }
    if (!form.title?.trim()) { setFieldErrors({ title: 'Required' }); return }
    if (!form.amount || Number(form.amount) < 0) { setFieldErrors({ amount: 'Must be >= 0' }); return }

    setSaving(true)
    try {
      const payload: CreateExpensePayload = {
        restaurant: restaurantId,
        category: form.category!,
        title: form.title!,
        amount: form.amount!,
        tax_amount: form.tax_amount ?? '0.00',
        expense_date: form.expense_date!,
        due_date: form.due_date || null,
        vendor_name: form.vendor_name ?? '',
        vendor_reference: form.vendor_reference ?? '',
        description: form.description ?? '',
        notes: form.notes ?? '',
      }
      const expense = await createExpense(payload)

      if (action === 'submit') {
        const { submitExpense } = await import('@/services/financials')
        await submitExpense(expense.id)
      }

      navigate(`/financials/expenses/${expense.id}`)
    } catch (e: any) {
      const msg = e?.response?.data?.message
      const details = e?.response?.data
      if (typeof details === 'object' && !details.message) {
        const errs: Record<string, string> = {}
        for (const [k, v] of Object.entries(details)) {
          errs[k] = Array.isArray(v) ? String(v[0]) : String(v)
        }
        setFieldErrors(errs)
      } else {
        setError(msg ?? 'Failed to create expense')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <button onClick={() => navigate(-1)} className="text-sm text-gray-400 hover:text-white mb-4 flex items-center gap-1">
          ← Back
        </button>
        <h1 className="text-2xl font-semibold text-white">New Expense</h1>
        <p className="text-sm text-gray-500 mt-1">Fill in the details and save as draft or submit for approval.</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm mb-6">{error}</div>
      )}

      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 space-y-5">
        {/* Category */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Category <span className="text-red-400">*</span></label>
          <select
            value={form.category ?? ''}
            onChange={(e) => set('category', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
          >
            <option value="">Select a category…</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{c.name} ({c.code})</option>
            ))}
          </select>
          {fieldErrors.category && <p className="text-xs text-red-400 mt-1">{fieldErrors.category}</p>}
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Title <span className="text-red-400">*</span></label>
          <input
            type="text"
            value={form.title ?? ''}
            onChange={(e) => set('title', e.target.value)}
            placeholder="e.g. Office rent – October 2026"
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500"
          />
          {fieldErrors.title && <p className="text-xs text-red-400 mt-1">{fieldErrors.title}</p>}
        </div>

        {/* Amount + Tax */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Amount (₹) <span className="text-red-400">*</span></label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.amount ?? ''}
              onChange={(e) => set('amount', e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
            />
            {fieldErrors.amount && <p className="text-xs text-red-400 mt-1">{fieldErrors.amount}</p>}
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Tax (₹)</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={form.tax_amount ?? ''}
              onChange={(e) => set('tax_amount', e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        {/* Total display */}
        <div className="bg-gray-900/60 rounded-lg px-4 py-3 flex items-center justify-between">
          <span className="text-sm text-gray-400">Total Amount</span>
          <span className="text-lg font-bold text-white">₹{Number(total).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>

        {/* Dates */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Expense Date <span className="text-red-400">*</span></label>
            <input
              type="date"
              value={form.expense_date ?? ''}
              onChange={(e) => set('expense_date', e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Due Date</label>
            <input
              type="date"
              value={form.due_date ?? ''}
              onChange={(e) => set('due_date', e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        {/* Vendor */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Vendor Name</label>
            <input
              type="text"
              value={form.vendor_name ?? ''}
              onChange={(e) => set('vendor_name', e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1.5">Vendor Reference</label>
            <input
              type="text"
              value={form.vendor_reference ?? ''}
              onChange={(e) => set('vendor_reference', e.target.value)}
              placeholder="Invoice / receipt number"
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Description</label>
          <textarea
            rows={2}
            value={form.description ?? ''}
            onChange={(e) => set('description', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Notes */}
        <div>
          <label className="block text-sm text-gray-400 mb-1.5">Notes</label>
          <textarea
            rows={2}
            value={form.notes ?? ''}
            onChange={(e) => set('notes', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Actions */}
        <div className="flex gap-3 pt-2">
          <button
            onClick={() => handleSubmit('draft')}
            disabled={saving}
            className="flex-1 py-2.5 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-lg border border-gray-600 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save Draft'}
          </button>
          <button
            onClick={() => handleSubmit('submit')}
            disabled={saving}
            className="flex-1 py-2.5 bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save & Submit'}
          </button>
        </div>
      </div>
    </div>
  )
}
