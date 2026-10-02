// =============================================================================
// RestaurantFlow — Menu Item Form Component
// Phase 5
// =============================================================================

import { useState, useEffect } from 'react'
import { useCategories, useTaxRates } from '@/hooks/useMenu'
import { useAllRestaurants as useRestaurants } from '@/hooks/useRestaurants'
import { Button } from '@/components/ui/Button'
import type { MenuItem, MenuItemCreatePayload, MenuItemUpdatePayload, FoodType } from '@/types'

const FOOD_TYPE_OPTIONS: { value: FoodType; label: string; dot: string }[] = [
  { value: 'VEG',     label: 'Vegetarian',     dot: 'bg-green-500' },
  { value: 'NON_VEG', label: 'Non-Vegetarian', dot: 'bg-red-500' },
  { value: 'EGG',     label: 'Egg',            dot: 'bg-yellow-500' },
  { value: 'VEGAN',   label: 'Vegan',          dot: 'bg-emerald-500' },
  { value: 'OTHER',   label: 'Other',          dot: 'bg-gray-500' },
]

interface MenuItemFormProps {
  initialValues?: Partial<MenuItem>
  onSubmit: (data: MenuItemCreatePayload | MenuItemUpdatePayload) => void
  onCancel: () => void
  loading?: boolean
  submitLabel?: string
}

export function MenuItemForm({
  initialValues,
  onSubmit,
  onCancel,
  loading,
  submitLabel = 'Save',
}: MenuItemFormProps) {
  const [form, setForm] = useState({
    restaurant: initialValues?.restaurant ?? '',
    category: initialValues?.category ?? '',
    name: initialValues?.name ?? '',
    sku: initialValues?.sku ?? '',
    short_description: initialValues?.short_description ?? '',
    description: initialValues?.description ?? '',
    food_type: (initialValues?.food_type ?? 'VEG') as FoodType,
    tax_rate: initialValues?.tax_rate ?? '',
    display_order: String(initialValues?.display_order ?? 0),
    preparation_time_minutes: String(initialValues?.preparation_time_minutes ?? 0),
  })

  const { data: restaurantsData } = useRestaurants()
  const { data: categoriesData } = useCategories(
    form.restaurant ? { restaurant: form.restaurant } : undefined
  )
  const { data: taxRatesData } = useTaxRates(
    form.restaurant ? { restaurant: form.restaurant, is_active: 'true' } : undefined
  )

  // Reset category when restaurant changes
  useEffect(() => {
    if (!initialValues) {
      setForm((p) => ({ ...p, category: '', tax_rate: '' }))
    }
  }, [form.restaurant]) // eslint-disable-line react-hooks/exhaustive-deps

  const setField = (key: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
      setForm((p) => ({ ...p, [key]: e.target.value }))

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    onSubmit({
      ...form,
      display_order: Number(form.display_order),
      preparation_time_minutes: Number(form.preparation_time_minutes),
      tax_rate: form.tax_rate || null,
    })
  }

  const inputClass =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder-gray-600'
  const labelClass = 'block text-xs text-gray-500 mb-1.5'
  const isEditing = !!initialValues?.id

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Restaurant — only for new items */}
      {!isEditing && (
        <div>
          <label className={labelClass}>Restaurant *</label>
          <select className={inputClass} value={form.restaurant} onChange={setField('restaurant')} required>
            <option value="">Select restaurant…</option>
            {restaurantsData?.results.map((r) => (
              <option key={r.id} value={r.id}>{r.name}</option>
            ))}
          </select>
        </div>
      )}

      {/* Name + SKU */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Item Name *</label>
          <input className={inputClass} placeholder="Chicken Biryani" required value={form.name} onChange={setField('name')} />
        </div>
        <div>
          <label className={labelClass}>SKU</label>
          <input className={inputClass} placeholder="SG-CB-001" value={form.sku} onChange={setField('sku')} />
        </div>
      </div>

      {/* Category */}
      <div>
        <label className={labelClass}>Category *</label>
        <select className={inputClass} value={form.category} onChange={setField('category')} required>
          <option value="">Select category…</option>
          {categoriesData?.results.filter((c) => c.is_active).map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        {!form.restaurant && (
          <p className="mt-1 text-xs text-gray-600">Select a restaurant first.</p>
        )}
      </div>

      {/* Food type */}
      <div>
        <label className={labelClass}>Food Type *</label>
        <div className="flex flex-wrap gap-2">
          {FOOD_TYPE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => setForm((p) => ({ ...p, food_type: opt.value }))}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                form.food_type === opt.value
                  ? 'bg-brand-500/20 border-brand-500/40 text-brand-300'
                  : 'bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${opt.dot}`} />
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Short description */}
      <div>
        <label className={labelClass}>Short Description</label>
        <input
          className={inputClass}
          placeholder="Brief description shown in the catalog (max 300 chars)"
          maxLength={300}
          value={form.short_description}
          onChange={setField('short_description')}
        />
      </div>

      {/* Description */}
      <div>
        <label className={labelClass}>Full Description</label>
        <textarea className={inputClass} rows={3} placeholder="Detailed description…" value={form.description} onChange={setField('description')} />
      </div>

      {/* Tax rate + Prep time + Order */}
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className={labelClass}>Tax Rate</label>
          <select className={inputClass} value={form.tax_rate} onChange={setField('tax_rate')}>
            <option value="">None</option>
            {taxRatesData?.results.filter((t) => t.is_active).map((t) => (
              <option key={t.id} value={t.id}>
                {t.code} ({Number(t.rate).toFixed(1)}%)
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClass}>Prep Time (min)</label>
          <input
            className={inputClass}
            type="number"
            min="0"
            placeholder="0"
            value={form.preparation_time_minutes}
            onChange={setField('preparation_time_minutes')}
          />
        </div>
        <div>
          <label className={labelClass}>Display Order</label>
          <input
            className={inputClass}
            type="number"
            min="0"
            placeholder="0"
            value={form.display_order}
            onChange={setField('display_order')}
          />
        </div>
      </div>

      <div className="flex justify-end gap-3 pt-2">
        <Button variant="ghost" type="button" onClick={onCancel}>Cancel</Button>
        <Button variant="primary" type="submit" loading={loading}>{submitLabel}</Button>
      </div>
    </form>
  )
}
