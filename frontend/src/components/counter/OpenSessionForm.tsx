// =============================================================================
// RestaurantFlow — Open Counter Session Form
// Phase 4
// =============================================================================

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { isValidCash } from '@/utils/money'
import type { Counter, Shift } from '@/types'

interface OpenSessionFormProps {
  counter: Counter
  shifts?: Shift[]
  onSubmit: (data: { opening_cash: string; shift?: string | null }) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export function OpenSessionForm({
  counter,
  shifts = [],
  onSubmit,
  onCancel,
  loading = false,
}: OpenSessionFormProps) {
  const [openingCash, setOpeningCash] = useState('')
  const [selectedShift, setSelectedShift] = useState<string>('')
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!isValidCash(openingCash)) {
      setError('Enter a valid opening cash amount (must be ≥ 0).')
      return
    }

    try {
      await onSubmit({
        opening_cash: parseFloat(openingCash).toFixed(2),
        shift: selectedShift || null,
      })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string }; message?: string } } }
      setError(
        e?.response?.data?.error?.message ??
        e?.response?.data?.message ??
        'Failed to open counter session.',
      )
    }
  }

  const inputCls =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500'

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {/* Counter info — read-only */}
      <div className="rounded-lg bg-gray-800/50 border border-gray-700 px-4 py-3 space-y-1">
        <p className="text-xs text-gray-600 uppercase tracking-wide">Counter</p>
        <p className="text-sm text-gray-200 font-medium">
          {counter.code} — {counter.name}
        </p>
        <p className="text-xs text-gray-500">{counter.branch_name}</p>
      </div>

      {error && (
        <p className="rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-2 text-xs text-red-400" role="alert">
          {error}
        </p>
      )}

      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="opening-cash">
          Opening Cash (₹) <span className="text-red-400">*</span>
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">₹</span>
          <input
            id="opening-cash"
            type="number"
            min="0"
            step="0.01"
            className={`${inputCls} pl-7`}
            value={openingCash}
            onChange={(e) => setOpeningCash(e.target.value)}
            placeholder="5000.00"
            required
            autoFocus
          />
        </div>
        <p className="text-xs text-gray-700 mt-0.5">
          Enter the physical cash count at session start.
        </p>
      </div>

      {shifts.length > 0 && (
        <div>
          <label className="block text-xs text-gray-500 mb-1" htmlFor="shift-select">
            Shift (optional)
          </label>
          <select
            id="shift-select"
            className={inputCls}
            value={selectedShift}
            onChange={(e) => setSelectedShift(e.target.value)}
          >
            <option value="">— No shift —</option>
            {shifts.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.start_time} – {s.end_time})
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={loading}>
          Open Counter
        </Button>
      </div>
    </form>
  )
}
