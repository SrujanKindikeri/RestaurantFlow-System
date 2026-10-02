// =============================================================================
// RestaurantFlow — Assign Cashier to Counter Form
// Phase 4
// =============================================================================

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import type { Counter } from '@/types'

interface AssignCounterFormProps {
  counter: Counter
  onSubmit: (data: { counter: string; user: number; expires_at?: string | null }) => Promise<void>
  onCancel: () => void
  loading?: boolean
}

export function AssignCounterForm({
  counter,
  onSubmit,
  onCancel,
  loading = false,
}: AssignCounterFormProps) {
  const [userId, setUserId]     = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [error, setError]       = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    const uid = parseInt(userId, 10)
    if (!userId || isNaN(uid)) {
      setError('Enter a valid User ID.')
      return
    }

    try {
      await onSubmit({
        counter: counter.id,
        user: uid,
        expires_at: expiresAt || null,
      })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { message?: string; details?: Record<string, string[]> } } }
      const details = e?.response?.data?.details
      if (details && typeof details === 'object') {
        const first = Object.values(details)[0]
        setError(Array.isArray(first) ? first[0] : String(first))
      } else {
        setError(e?.response?.data?.message ?? 'Failed to assign counter.')
      }
    }
  }

  const inputCls =
    'w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500'

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      <div className="rounded-lg bg-gray-800/50 border border-gray-700 px-4 py-3 space-y-1">
        <p className="text-xs text-gray-600">Counter</p>
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
        <label className="block text-xs text-gray-500 mb-1" htmlFor="assign-user-id">
          User ID <span className="text-red-400">*</span>
        </label>
        <input
          id="assign-user-id"
          type="number"
          className={inputCls}
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          placeholder="Enter numeric user ID"
          required
          autoFocus
        />
        <p className="text-xs text-gray-700 mt-0.5">
          Find the user's ID from the Users page.
        </p>
      </div>

      <div>
        <label className="block text-xs text-gray-500 mb-1" htmlFor="assign-expires">
          Expires At (optional)
        </label>
        <input
          id="assign-expires"
          type="datetime-local"
          className={inputCls}
          value={expiresAt}
          onChange={(e) => setExpiresAt(e.target.value)}
        />
        <p className="text-xs text-gray-700 mt-0.5">
          Leave blank for an open-ended assignment.
        </p>
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={loading}>
          Assign
        </Button>
      </div>
    </form>
  )
}
