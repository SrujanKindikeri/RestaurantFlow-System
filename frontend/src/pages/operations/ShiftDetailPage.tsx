// =============================================================================
// RestaurantFlow — Shift Detail / Handover Page
// Phase 19: Advanced POS & Restaurant Operations
// =============================================================================

import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getShiftHandover, addHandoverNote, closeShift } from '@/services/operations'
import { useAuth } from '@/contexts/AuthContext'

const PRIORITY_COLORS: Record<string, string> = {
  HIGH: 'border-red-500/40 bg-red-500/5 text-red-400',
  NORMAL: 'border-gray-700 bg-gray-900 text-gray-300',
  LOW: 'border-gray-800 bg-gray-900/50 text-gray-500',
}

const TYPE_BADGE: Record<string, string> = {
  KITCHEN: 'bg-orange-500/10 text-orange-400',
  PAYMENT: 'bg-green-500/10 text-green-400',
  EQUIPMENT: 'bg-red-500/10 text-red-400',
  CUSTOMER: 'bg-blue-500/10 text-blue-400',
  INVENTORY: 'bg-yellow-500/10 text-yellow-400',
  STAFF: 'bg-purple-500/10 text-purple-400',
  GENERAL: 'bg-gray-800 text-gray-400',
  OTHER: 'bg-gray-800 text-gray-400',
}

export function ShiftDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { hasPermission } = useAuth()
  const [summary, setSummary] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAddNote, setShowAddNote] = useState(false)
  const [noteForm, setNoteForm] = useState({ note_type: 'GENERAL', content: '', priority: 'NORMAL' })
  const [addingNote, setAddingNote] = useState(false)

  const load = () => {
    setLoading(true)
    getShiftHandover(id!)
      .then(r => setSummary(r.data))
      .catch(() => setError('Failed to load shift summary'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { if (id) load() }, [id])

  const handleAddNote = async () => {
    setAddingNote(true)
    try {
      await addHandoverNote(id!, noteForm)
      setShowAddNote(false)
      setNoteForm({ note_type: 'GENERAL', content: '', priority: 'NORMAL' })
      load()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? 'Failed to add note')
    } finally {
      setAddingNote(false)
    }
  }

  if (loading) return <div className="p-8 text-gray-400">Loading shift summary…</div>
  if (error && !summary) return (
    <div className="p-8">
      <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-4">{error}</div>
    </div>
  )

  const s = summary

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm text-gray-500">
        <Link to="/operations/shifts" className="hover:text-white">Shifts</Link>
        <span>/</span>
        <span className="text-gray-300">{s?.shift_type} Shift Handover</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">{s?.shift_type} Shift — {s?.branch}</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {s?.started_at && new Date(s.started_at).toLocaleString()}
            {s?.ended_at && ` → ${new Date(s.ended_at).toLocaleString()}`}
          </p>
        </div>
        <span className={`text-xs border rounded-full px-3 py-1 ${s?.status === 'OPEN' ? 'border-green-500/20 text-green-400' : 'border-gray-700 text-gray-500'}`}>
          {s?.status}
        </span>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg p-3 text-sm">{error}</div>
      )}

      {/* Summary grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <SummaryCard label="Total Orders" value={s?.orders?.total ?? 0} />
        <SummaryCard label="Confirmed" value={s?.orders?.confirmed ?? 0} color="green" />
        <SummaryCard label="Cancelled" value={s?.orders?.cancelled ?? 0} color="red" />
        <SummaryCard label="Still Open" value={s?.orders?.open ?? 0} color="yellow" />
        <SummaryCard label="Total Payments" value={s?.payments?.count ?? 0} />
        <SummaryCard label="Net Sales" value={`₹${s?.payments?.net_sales ?? 0}`} color="green" />
        <SummaryCard label="Cash Total" value={`₹${s?.payments?.cash_total ?? 0}`} />
        <SummaryCard label="Refunds" value={`₹${s?.payments?.refund_total ?? 0}`} color="red" />
        <SummaryCard label="Pending Bills" value={s?.bills?.pending_payment ?? 0} color="orange" />
        <SummaryCard label="Kitchen Pending" value={s?.kitchen?.pending_orders ?? 0} color="orange" />
      </div>

      {/* Handover Notes */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-white">Handover Notes</h2>
          {s?.status === 'OPEN' && (
            <button
              onClick={() => setShowAddNote(true)}
              className="text-xs bg-brand-500/10 text-brand-400 border border-brand-500/20 rounded-lg px-3 py-1.5 hover:bg-brand-500/20"
            >
              + Add Note
            </button>
          )}
        </div>

        {(!s?.handover_notes || s.handover_notes.length === 0) ? (
          <p className="text-sm text-gray-600">No handover notes yet</p>
        ) : (
          <div className="space-y-2">
            {s.handover_notes.map((note: any, i: number) => (
              <div key={i} className={`border rounded-xl p-4 ${PRIORITY_COLORS[note.priority] ?? 'border-gray-800 bg-gray-900'}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs rounded px-1.5 py-0.5 ${TYPE_BADGE[note.note_type] ?? 'bg-gray-800 text-gray-400'}`}>
                    {note.note_type}
                  </span>
                  {note.priority === 'HIGH' && (
                    <span className="text-xs text-red-400 font-semibold">⚠ HIGH PRIORITY</span>
                  )}
                  <span className="text-xs text-gray-600 ml-auto">
                    {note.created_at && new Date(note.created_at).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-sm">{note.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Add note modal */}
      {showAddNote && (
        <div className="fixed inset-0 z-50 bg-gray-950/80 flex items-center justify-center">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-96 shadow-2xl">
            <h2 className="text-lg font-semibold text-white mb-4">Add Handover Note</h2>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Type</label>
                  <select
                    value={noteForm.note_type}
                    onChange={e => setNoteForm(f => ({ ...f, note_type: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white"
                  >
                    {['GENERAL', 'KITCHEN', 'INVENTORY', 'CUSTOMER', 'PAYMENT', 'EQUIPMENT', 'STAFF', 'OTHER'].map(t => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Priority</label>
                  <select
                    value={noteForm.priority}
                    onChange={e => setNoteForm(f => ({ ...f, priority: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-2 py-1.5 text-sm text-white"
                  >
                    {['LOW', 'NORMAL', 'HIGH'].map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Content</label>
                <textarea
                  value={noteForm.content}
                  onChange={e => setNoteForm(f => ({ ...f, content: e.target.value }))}
                  rows={3}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white resize-none"
                  placeholder="Describe the issue or note for the next shift…"
                />
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleAddNote}
                disabled={addingNote || !noteForm.content.trim()}
                className="flex-1 bg-brand-500 hover:bg-brand-600 disabled:opacity-40 text-white rounded-lg py-2 text-sm font-medium"
              >
                {addingNote ? 'Adding…' : 'Add Note'}
              </button>
              <button onClick={() => setShowAddNote(false)} className="px-4 text-sm text-gray-500 hover:text-gray-300">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const SummaryCard = ({ label, value, color = 'white' }: { label: string; value: string | number; color?: string }) => (
  <div className="bg-gray-900 border border-gray-800 rounded-xl p-3">
    <p className="text-xs text-gray-500 mb-0.5">{label}</p>
    <p className={`text-xl font-bold text-${color}`}>{value}</p>
  </div>
)
