// =============================================================================
// RestaurantFlow — Counter Create / Edit Form
// Phase 4
// =============================================================================

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import type { Counter, CounterCreatePayload, CounterUpdatePayload } from '@/types'

interface CounterFormProps {
  initial?: Counter
  branchId?: string          // Required for create; read-only for edit
  onSubmit: (data: CounterCreatePayload | CounterUpdatePayload) => Promise<void>
  onCancel: () => void
  submitLabel?: string
  loading?: boolean
}

const COUNTER_TYPES = [
  { value: 'MAIN_BILLING',  label: 'Main Billing' },
  { value: 'TAKEAWAY',      label: 'Takeaway' },
  { value: 'SNACKS',        label: 'Snacks' },
  { value: 'DRIVE_THROUGH', label: 'Drive Through' },
  { value: 'OTHER',         label: 'Other' },
]

export function CounterForm({
  initial,
  branchId,
  onSubmit,
  onCancel,
  submitLabel = 'Save',
  loading = false,
}: CounterFormProps) {
  const [name, setName]               = useState(initial?.name ?? '')
  const [code, setCode]               = useState(initial?.code ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [counterType, setCounterType] = useState(initial?.counter_type ?? 'MAIN_BILLING')
  const [location, setLocation]       = useState(initial?.location ?? '')
  const [error, setError]             = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!name.trim()) { setError('Name is required.'); return }
    if (!code.trim()) { setError('Code is required.'); return }

    const payload: CounterCreatePayload | CounterUpdatePayload = {
      name: name.trim(),
      code: code.trim().toUpperCase(),
      description: description.trim(),
      counter_type: counterType as CounterCreatePayload['counter_type'],
      location: location.trim(),
    }
    if (branchId && !initial) {
      (payload as CounterCreatePayload).branch = branchId
    }

    try {
      await onSubmit(payload)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string; details?: Record<string, string[]> } } }
      const details = e?.response?.data?.details
      if (details && typeof details === 'object') {
        const first = Object.values(details)[0]
        setError(Array.isArray(first) ? first[0] : String(first))
      } else {
        setError(e?.response?.data?.message ?? 'An error occurred.')
      }
    }
  }

  const inputCls =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500'

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {error && (
        <p className="rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-2 text-xs text-red-400" role="alert">
          {error}
        </p>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1" htmlFor="counter-name">
            Name <span className="text-red-400">*</span>
          </label>
          <input
            id="counter-name"
            type="text"
            className={inputCls}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Main Billing"
            required
          />
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1" htmlFor="counter-code">
            Code <span className="text-red-400">*</span>
          </label>
          <input
            id="counter-code"
            type="text"
            className={inputCls}
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="C01"
            maxLength={20}
            required
          />
          <p className="text-xs text-gray-700 mt-0.5">Unique within branch. Auto-uppercased.</p>
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1" htmlFor="counter-type">
            Counter Type
          </label>
          <select
            id="counter-type"
            className={inputCls}
            value={counterType}
            onChange={(e) => setCounterType(e.target.value as 'MAIN_BILLING' | 'TAKEAWAY' | 'SNACKS' | 'DRIVE_THROUGH' | 'OTHER')}
          >
            {COUNTER_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-500 mb-1" htmlFor="counter-location">
            Location
          </label>
          <input
            id="counter-location"
            type="text"
            className={inputCls}
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="Near entrance, Floor 1…"
          />
        </div>

        <div className="sm:col-span-2">
          <label className="block text-xs text-gray-500 mb-1" htmlFor="counter-desc">
            Description
          </label>
          <textarea
            id="counter-desc"
            className={inputCls}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Optional description…"
          />
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={loading}>
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}
