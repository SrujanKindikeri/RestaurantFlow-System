// =============================================================================
// RestaurantFlow — Close Counter Session Form
// Phase 4
// =============================================================================

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/Button'
import { formatCurrency, formatDifference, isValidCash } from '@/utils/money'
import type { CounterSession } from '@/types'

interface CloseSessionFormProps {
  session: CounterSession
  onSubmit: (data: { actual_cash: string; closing_note: string }) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export function CloseSessionForm({
  session,
  onSubmit,
  onCancel,
  loading = false,
}: CloseSessionFormProps) {
  const [actualCash, setActualCash]   = useState('')
  const [closingNote, setClosingNote] = useState('')
  const [error, setError]             = useState('')
  const [difference, setDifference]   = useState<string | null>(null)

  // Live difference preview
  useEffect(() => {
    if (isValidCash(actualCash)) {
      const diff = (parseFloat(actualCash) - parseFloat(session.expected_cash)).toFixed(2)
      setDifference(diff)
    } else {
      setDifference(null)
    }
  }, [actualCash, session.expected_cash])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!isValidCash(actualCash)) {
      setError('Enter a valid actual cash amount (must be ≥ 0).')
      return
    }

    try {
      await onSubmit({
        actual_cash: parseFloat(actualCash).toFixed(2),
        closing_note: closingNote.trim(),
      })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string }; message?: string } } }
      setError(
        e?.response?.data?.error?.message ??
        e?.response?.data?.message ??
        'Failed to close session.',
      )
    }
  }

  const inputCls =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500'

  const diff = difference !== null ? formatDifference(difference) : null

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {/* Summary */}
      <div className="rounded-lg bg-gray-800/50 border border-gray-700 px-4 py-3 space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Counter</span>
          <span className="text-gray-300 font-medium">
            {session.counter_code} — {session.counter_name}
          </span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Opening Cash</span>
          <span className="text-gray-300">{formatCurrency(session.opening_cash)}</span>
        </div>
        <div className="flex justify-between text-sm">
          <span className="text-gray-500">Expected Cash</span>
          <span className="text-gray-300 font-medium">{formatCurrency(session.expected_cash)}</span>
        </div>
      </div>

      {error && (
        <p className="rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-2 text-xs text-red-400" role="alert">
          {error}
        </p>
      )}

      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="actual-cash">
          Actual Cash Count (₹) <span className="text-red-400">*</span>
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">₹</span>
          <input
            id="actual-cash"
            type="number"
            min="0"
            step="0.01"
            className={`${inputCls} pl-7`}
            value={actualCash}
            onChange={(e) => setActualCash(e.target.value)}
            placeholder="0.00"
            required
            autoFocus
          />
        </div>
      </div>

      {/* Live difference */}
      {diff && (
        <div className="rounded-lg bg-gray-800/50 border border-gray-700 px-4 py-3">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Difference</span>
            <span className={`font-semibold ${diff.colorClass}`}>{diff.label}</span>
          </div>
          <p className="text-xs text-gray-700 mt-1">
            Actual − Expected. Backend recalculates before saving.
          </p>
        </div>
      )}

      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="closing-note">
          Closing Note
        </label>
        <textarea
          id="closing-note"
          className={inputCls}
          value={closingNote}
          onChange={(e) => setClosingNote(e.target.value)}
          rows={2}
          placeholder="Normal closing, all clear…"
        />
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="danger" loading={loading}>
          Close Counter
        </Button>
      </div>
    </form>
  )
}
