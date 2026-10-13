// =============================================================================
// RestaurantFlow — Operational Shifts Page
// Phase 19: Advanced POS & Restaurant Operations
// =============================================================================

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listShifts, createShift, closeShift } from '@/services/operations'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_BADGE: Record<string, string> = {
  OPEN: 'bg-green-500/10 text-green-400 border-green-500/20',
  CLOSED: 'bg-gray-500/10 text-gray-400 border-gray-700',
}

const SHIFT_TYPE_EMOJI: Record<string, string> = {
  MORNING: '🌅',
  AFTERNOON: '☀️',
  EVENING: '🌆',
  NIGHT: '🌙',
  CUSTOM: '⚙️',
}

export function ShiftsPage() {
  const { user, hasPermission } = useAuth()
  const [shifts, setShifts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ shift_type: 'MORNING', notes: '' })

  const load = () => {
    setLoading(true)
    listShifts()
      .then(r => setShifts(r.data))
      .catch(() => setError('Failed to load shifts'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    setCreating(true)
    try {
      await createShift({ branch_id: '', ...form })
      setShowCreate(false)
      load()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to create shift')
    } finally {
      setCreating(false)
    }
  }

  const handleClose = async (shiftId: string) => {
    if (!window.confirm('Close this shift?')) return
    try {
      await closeShift(shiftId)
      load()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to close shift')
    }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Operational Shifts</h1>
          <p className="text-sm text-gray-500 mt-0.5">Branch shift management and handover</p>
        </div>
        {hasPermission('shift.create') && (
          <button
            onClick={() => setShowCreate(true)}
            className="bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium rounded-lg px-4 py-2"
          >
            + Open Shift
          </button>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg px-4 py-3 text-sm flex justify-between">
          {error}
          <button onClick={() => setError('')} className="underline text-xs">Dismiss</button>
        </div>
      )}

      {loading ? (
        <p className="text-gray-500 text-sm py-10 text-center">Loading shifts…</p>
      ) : shifts.length === 0 ? (
        <p className="text-gray-600 text-sm py-10 text-center">No shifts found</p>
      ) : (
        <div className="space-y-3">
          {shifts.map(shift => (
            <div key={shift.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{SHIFT_TYPE_EMOJI[shift.shift_type] ?? '⏱'}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-semibold text-white">{shift.shift_type}</p>
                      <span className={`text-xs border rounded-full px-2 py-0.5 ${STATUS_BADGE[shift.status] ?? ''}`}>
                        {shift.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {shift.branch_name} · Opened by {shift.opened_by_email}
                    </p>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {new Date(shift.started_at).toLocaleString()}
                      {shift.ended_at && ` → ${new Date(shift.ended_at).toLocaleString()}`}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  <Link
                    to={`/operations/shifts/${shift.id}`}
                    className="text-xs bg-gray-800 border border-gray-700 text-gray-300 hover:text-white rounded-lg px-3 py-1.5"
                  >
                    Handover
                  </Link>
                  {shift.status === 'OPEN' && hasPermission('shift.close') && (
                    <button
                      onClick={() => handleClose(shift.id)}
                      className="text-xs bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 rounded-lg px-3 py-1.5"
                    >
                      Close
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create shift modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 bg-gray-950/80 flex items-center justify-center">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-80 shadow-2xl">
            <h2 className="text-lg font-semibold text-white mb-4">Open New Shift</h2>

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Shift Type</label>
                <select
                  value={form.shift_type}
                  onChange={e => setForm(f => ({ ...f, shift_type: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white"
                >
                  {['MORNING', 'AFTERNOON', 'EVENING', 'NIGHT', 'CUSTOM'].map(t => (
                    <option key={t} value={t}>{SHIFT_TYPE_EMOJI[t]} {t}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Notes (optional)</label>
                <textarea
                  value={form.notes}
                  onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
                  rows={2}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white resize-none"
                />
              </div>
            </div>

            <div className="flex gap-2 mt-4">
              <button
                onClick={handleCreate}
                disabled={creating}
                className="flex-1 bg-brand-500 hover:bg-brand-600 text-white rounded-lg py-2 text-sm font-medium disabled:opacity-40"
              >
                {creating ? 'Opening…' : 'Open Shift'}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 text-sm text-gray-500 hover:text-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
