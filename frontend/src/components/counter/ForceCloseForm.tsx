// =============================================================================
// RestaurantFlow — Force-Close Counter Session Form
// Phase 4
// =============================================================================

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { isValidCash } from '@/utils/money'
import type { CounterSession } from '@/types'

interface ForceCloseFormProps {
  session: CounterSession
  onSubmit: (data: { reason: string; actual_cash?: string | null }) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export function ForceCloseForm({
  session,
  onSubmit,
  onCancel,
  loading = false,
}: ForceCloseFormProps) {
  const [reason, setReason]         = useState('')
  const [actualCash, setActualCash] = useState('')
  const [error, setError]           = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    if (!reason.trim()) {
      setError('A reason is required for force-close.')
      return
    }
    if (actualCash && !isValidCash(actualCash)) {
      setError('Actual cash must be a valid non-negative number.')
      return
    }

    try {
      await onSubmit({
        reason: reason.trim(),
        actual_cash: actualCash ? parseFloat(actualCash).toFixed(2) : null,
      })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { error?: { message?: string }; message?: string } } }
      setError(
        e?.response?.data?.error?.message ??
        e?.response?.data?.message ??
        'Failed to force-close session.',
      )
    }
  }

  const inputCls =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500'

  return (
    <form onSubmit={handleSubmit} className="space-y-5" noValidate>
      {/* Warning banner */}
      <div className="rounded-lg bg-red-950/30 border border-red-800/50 px-4 py-3 text-xs text-red-400">
        <strong>Force Close</strong> — Use only when the normal closing flow cannot be completed
        (e.g. cashier left, system outage, emergency). This action is logged.
      </div>

      <div className="rounded-lg bg-gray-800/50 border border-gray-700 px-4 py-3 space-y-1">
        <p className="text-xs text-gray-600">Counter</p>
        <p className="text-sm text-gray-200 font-medium">
          {session.counter_code} — {session.counter_name}
        </p>
        <p className="text-xs text-gray-500">Opened by {session.opened_by_name}</p>
      </div>

      {error && (
        <p className="rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-2 text-xs text-red-400" role="alert">
          {error}
        </p>
      )}

      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="force-reason">
          Reason <span className="text-red-400">*</span>
        </label>
        <textarea
          id="force-reason"
          className={inputCls}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          rows={2}
          placeholder="Cashier left unexpectedly…"
          required
          autoFocus
        />
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="force-actual-cash">
          Actual Cash (₹) — optional
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 text-sm">₹</span>
          <input
            id="force-actual-cash"
            type="number"
            min="0"
            step="0.01"
            className={`${inputCls} pl-7`}
            value={actualCash}
            onChange={(e) => setActualCash(e.target.value)}
            placeholder="Leave blank if unknown"
          />
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="danger" loading={loading}>
          Force Close
        </Button>
      </div>
    </form>
  )
}
