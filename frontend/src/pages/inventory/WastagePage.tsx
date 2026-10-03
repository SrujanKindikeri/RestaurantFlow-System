// =============================================================================
// RestaurantFlow — Wastage Page
// Phase 10
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { listWastages, createWastage, approveWastage, rejectWastage, listInventoryItems, listStorageLocations } from '@/services/inventory'
import type { StockWastage, InventoryItem, StorageLocation, UnitOfMeasurement, WastageType, CreateStockWastagePayload } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_BADGE: Record<string, string> = {
  PENDING:  'bg-amber-500/10 text-amber-400 border-amber-500/20',
  APPROVED: 'bg-brand-500/10 text-brand-400 border-brand-500/20',
  REJECTED: 'bg-red-500/10 text-red-400 border-red-500/20',
  RECORDED: 'bg-green-500/10 text-green-400 border-green-500/20',
}

const WASTAGE_TYPES: WastageType[] = ['SPOILED', 'DAMAGED', 'EXPIRED', 'PREPARATION_LOSS', 'OTHER']
const UNITS: UnitOfMeasurement[] = ['KG', 'GRAM', 'LITRE', 'MILLILITRE', 'PIECE', 'PACK', 'BOX', 'BOTTLE', 'DOZEN']

export function WastagePage() {
  const { hasPermission } = useAuth()
  const [wastages, setWastages] = useState<StockWastage[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [invItems, setInvItems] = useState<InventoryItem[]>([])
  const [locations, setLocations] = useState<StorageLocation[]>([])
  const [form, setForm] = useState<Partial<CreateStockWastagePayload>>({ quantity: '1', unit: 'KG', wastage_type: 'SPOILED', reason: '' })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [rejectingId, setRejectingId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filterStatus) params.status = filterStatus
    listWastages(params)
      .then(r => setWastages(r.data))
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load'))
      .finally(() => setLoading(false))
  }, [filterStatus])

  useEffect(() => { load() }, [load])

  const openForm = async () => {
    const [items, locs] = await Promise.all([listInventoryItems(), listStorageLocations()])
    setInvItems(items.data)
    setLocations(locs.data)
    setShowForm(true)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await createWastage(form as CreateStockWastagePayload)
      setShowForm(false)
      load()
    } catch (e: any) {
      setFormError(e?.response?.data?.message ?? 'Failed to record wastage')
    } finally { setSaving(false) }
  }

  const doApprove = async (id: string) => {
    try { await approveWastage(id); load() } catch (e: any) { alert(e?.response?.data?.message ?? 'Failed') }
  }

  const doReject = async (id: string) => {
    if (!rejectReason.trim()) { alert('Please enter a rejection reason'); return }
    try { await rejectWastage(id, rejectReason); setRejectingId(null); setRejectReason(''); load() } catch (e: any) { alert(e?.response?.data?.message ?? 'Failed') }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Stock Wastage</h1>
          <p className="text-sm text-gray-500 mt-0.5">{wastages.length} records</p>
        </div>
        {hasPermission('inventory.wastage.create') && (
          <button onClick={openForm} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm hover:bg-brand-600 transition-colors">+ Record Wastage</button>
        )}
      </div>

      <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
        <option value="">All Statuses</option>
        {['PENDING','APPROVED','REJECTED','RECORDED'].map(s => <option key={s} value={s}>{s}</option>)}
      </select>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">Record Wastage</h3>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Item *</label>
              <select required value={form.inventory_item_id ?? ''} onChange={e => setForm(f => ({ ...f, inventory_item_id: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                <option value="">Select item</option>
                {invItems.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Location *</label>
              <select required value={form.storage_location_id ?? ''} onChange={e => setForm(f => ({ ...f, storage_location_id: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                <option value="">Select location</option>
                {locations.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Quantity *</label>
              <input type="number" step="0.001" min="0.001" required value={form.quantity ?? ''}
                onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Unit *</label>
              <select value={form.unit} onChange={e => setForm(f => ({ ...f, unit: e.target.value as UnitOfMeasurement }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                {UNITS.map(u => <option key={u}>{u}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Type *</label>
              <select value={form.wastage_type} onChange={e => setForm(f => ({ ...f, wastage_type: e.target.value as WastageType }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                {WASTAGE_TYPES.map(t => <option key={t}>{t.replace('_', ' ')}</option>)}
              </select>
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Reason *</label>
            <textarea required minLength={5} value={form.reason ?? ''} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} rows={2}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500 resize-none" />
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm disabled:opacity-50 hover:bg-brand-600">
              {saving ? 'Saving…' : 'Record'}
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="space-y-3">
          {wastages.map(w => (
            <div key={w.id} className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-2">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm font-medium text-white">{w.item_name} <span className="text-gray-500 text-xs font-mono ml-1">{w.item_sku}</span></p>
                  <p className="text-xs text-gray-400">{w.quantity} {w.unit} · {w.wastage_type} · {w.location_name}</p>
                  <p className="text-xs text-gray-500 mt-1">{w.reason}</p>
                </div>
                <div className="text-right space-y-1">
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_BADGE[w.status]}`}>{w.status}</span>
                  <p className="text-xs text-gray-500">Est. ₹{w.estimated_cost}</p>
                </div>
              </div>
              {w.status === 'PENDING' && (
                <div className="flex gap-2 pt-1">
                  {hasPermission('inventory.wastage.approve') && (
                    <>
                      <button onClick={() => doApprove(w.id)} className="px-3 py-1 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg text-xs hover:bg-green-500/30">Approve</button>
                      {rejectingId === w.id ? (
                        <div className="flex gap-2 items-center flex-1">
                          <input value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="Rejection reason…"
                            className="flex-1 bg-gray-900 border border-gray-700 rounded px-2 py-1 text-xs text-white focus:outline-none" />
                          <button onClick={() => doReject(w.id)} className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs">Confirm</button>
                          <button onClick={() => setRejectingId(null)} className="px-2 py-1 bg-gray-700 text-gray-400 rounded text-xs">Cancel</button>
                        </div>
                      ) : (
                        <button onClick={() => setRejectingId(w.id)} className="px-3 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-xs hover:bg-red-500/20">Reject</button>
                      )}
                    </>
                  )}
                </div>
              )}
              {w.status === 'REJECTED' && w.rejection_reason && (
                <p className="text-xs text-red-400">Rejection: {w.rejection_reason}</p>
              )}
            </div>
          ))}
          {wastages.length === 0 && (
            <div className="text-center py-8 text-gray-600 text-sm">No wastage records found.</div>
          )}
        </div>
      )}
    </div>
  )
}
