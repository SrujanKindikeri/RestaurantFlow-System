// =============================================================================
// RestaurantFlow — Stock Transfers Page
// Phase 10
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import {
  listStockTransfers, getStockTransfer, createStockTransfer,
  requestStockTransfer, approveStockTransfer, completeStockTransfer, cancelStockTransfer,
  listStorageLocations, listInventoryItems,
} from '@/services/inventory'
import type { StockTransfer, StockTransferSummary, StorageLocation, InventoryItem, UnitOfMeasurement, CreateStockTransferPayload } from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_BADGE: Record<string, string> = {
  DRAFT:     'bg-gray-700 text-gray-400 border-gray-600',
  REQUESTED: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  APPROVED:  'bg-brand-500/10 text-brand-400 border-brand-500/20',
  COMPLETED: 'bg-green-500/10 text-green-400 border-green-500/20',
  CANCELLED: 'bg-red-500/10 text-red-400 border-red-500/20',
}

const UNITS: UnitOfMeasurement[] = ['KG', 'GRAM', 'LITRE', 'MILLILITRE', 'PIECE', 'PACK', 'BOX', 'BOTTLE', 'DOZEN']

export function TransfersPage() {
  const { user, hasPermission } = useAuth()
  const [transfers, setTransfers] = useState<StockTransferSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState('')
  const [selected, setSelected] = useState<StockTransfer | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  const [showCreate, setShowCreate] = useState(false)
  const [locations, setLocations] = useState<StorageLocation[]>([])
  const [invItems, setInvItems] = useState<InventoryItem[]>([])
  const [createForm, setCreateForm] = useState<Partial<CreateStockTransferPayload>>({ items: [] })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filterStatus) params.status = filterStatus
    listStockTransfers(params)
      .then(r => setTransfers(r.data))
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load transfers'))
      .finally(() => setLoading(false))
  }, [filterStatus])

  useEffect(() => { load() }, [load])

  const loadAuxData = useCallback(async () => {
    const [locs, items] = await Promise.all([
      listStorageLocations(restaurantId ? {} : {}),
      listInventoryItems(restaurantId ? { restaurant: restaurantId } : {}),
    ])
    setLocations(locs.data)
    setInvItems(items.data)
  }, [restaurantId])

  const openCreate = async () => {
    await loadAuxData()
    setCreateForm({ restaurant_id: restaurantId, items: [{ inventory_item_id: '', quantity: '1', unit: 'KG' }] })
    setShowCreate(true)
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await createStockTransfer(createForm as CreateStockTransferPayload)
      setShowCreate(false)
      load()
    } catch (e: any) {
      setFormError(e?.response?.data?.message ?? 'Failed to create transfer')
    } finally { setSaving(false) }
  }

  const selectTransfer = async (id: string) => {
    setLoadingDetail(true)
    try { const r = await getStockTransfer(id); setSelected(r.data) } catch { /* ignore */ }
    setLoadingDetail(false)
  }

  const doAction = async (action: string, id: string) => {
    try {
      if (action === 'request') await requestStockTransfer(id)
      else if (action === 'approve') await approveStockTransfer(id)
      else if (action === 'complete') await completeStockTransfer(id)
      else if (action === 'cancel') await cancelStockTransfer(id)
      load()
      if (selected?.id === id) selectTransfer(id)
    } catch (e: any) { alert(e?.response?.data?.message ?? 'Action failed') }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Stock Transfers</h1>
          <p className="text-sm text-gray-500 mt-0.5">{transfers.length} transfers</p>
        </div>
        {hasPermission('inventory.transfer') && (
          <button onClick={openCreate} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm hover:bg-brand-600 transition-colors">+ New Transfer</button>
        )}
      </div>

      <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
        <option value="">All Statuses</option>
        {['DRAFT','REQUESTED','APPROVED','COMPLETED','CANCELLED'].map(s => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {showCreate && (
        <form onSubmit={handleCreate} className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">New Stock Transfer</h3>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Source Location *</label>
              <select required value={createForm.source_location_id ?? ''} onChange={e => setCreateForm(f => ({ ...f, source_location_id: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                <option value="">Select location</option>
                {locations.map(l => <option key={l.id} value={l.id}>{l.name} [{l.branch_name}]</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Destination Location *</label>
              <select required value={createForm.destination_location_id ?? ''} onChange={e => setCreateForm(f => ({ ...f, destination_location_id: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                <option value="">Select location</option>
                {locations.filter(l => l.id !== createForm.source_location_id).map(l => <option key={l.id} value={l.id}>{l.name} [{l.branch_name}]</option>)}
              </select>
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-gray-400 font-medium">Items</label>
              <button type="button" onClick={() => setCreateForm(f => ({ ...f, items: [...(f.items ?? []), { inventory_item_id: '', quantity: '1', unit: 'KG' }] }))}
                className="text-xs text-brand-400 hover:text-brand-300">+ Add Row</button>
            </div>
            {(createForm.items ?? []).map((item, idx) => (
              <div key={idx} className="grid grid-cols-4 gap-2 mb-2">
                <select required value={item.inventory_item_id} onChange={e => setCreateForm(f => { const items = [...(f.items ?? [])]; items[idx] = { ...items[idx], inventory_item_id: e.target.value }; return { ...f, items } })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white col-span-2 focus:outline-none focus:border-brand-500">
                  <option value="">Select item</option>
                  {invItems.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
                </select>
                <input type="number" step="0.001" min="0.001" required placeholder="Qty" value={item.quantity}
                  onChange={e => setCreateForm(f => { const items = [...(f.items ?? [])]; items[idx] = { ...items[idx], quantity: e.target.value }; return { ...f, items } })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500" />
                <select value={item.unit} onChange={e => setCreateForm(f => { const items = [...(f.items ?? [])]; items[idx] = { ...items[idx], unit: e.target.value as UnitOfMeasurement }; return { ...f, items } })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500">
                  {UNITS.map(u => <option key={u}>{u}</option>)}
                </select>
              </div>
            ))}
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Notes</label>
            <input value={createForm.notes ?? ''} onChange={e => setCreateForm(f => ({ ...f, notes: e.target.value }))}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
          </div>
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm disabled:opacity-50 hover:bg-brand-600">
              {saving ? 'Creating…' : 'Create Transfer'}
            </button>
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600">Cancel</button>
          </div>
        </form>
      )}

      {loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          <div className="lg:col-span-2 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  {['Transfer #', 'From', 'To', 'Status'].map(h => <th key={h} className="text-left text-xs text-gray-500 font-medium px-3 py-2">{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {transfers.map(t => (
                  <tr key={t.id} onClick={() => selectTransfer(t.id)} className={`border-b border-gray-800/50 cursor-pointer transition-colors ${selected?.id === t.id ? 'bg-gray-800' : 'hover:bg-gray-800/30'}`}>
                    <td className="px-3 py-3 text-brand-400 font-mono text-xs">{t.transfer_number}</td>
                    <td className="px-3 py-3 text-gray-400 text-xs">{t.source_location_name}</td>
                    <td className="px-3 py-3 text-gray-400 text-xs">{t.destination_location_name}</td>
                    <td className="px-3 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_BADGE[t.status]}`}>{t.status}</span>
                    </td>
                  </tr>
                ))}
                {transfers.length === 0 && <tr><td colSpan={4} className="px-3 py-8 text-center text-gray-600 text-sm">No transfers found.</td></tr>}
              </tbody>
            </table>
          </div>

          <div className="lg:col-span-3">
            {loadingDetail && <div className="h-40 bg-gray-800 rounded-xl animate-pulse" />}
            {selected && !loadingDetail && (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-4">
                <div>
                  <p className="text-sm font-mono text-brand-400">{selected.transfer_number}</p>
                  <p className="text-xs text-gray-400 mt-1">{selected.source_location_name} → {selected.destination_location_name}</p>
                  <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_BADGE[selected.status]}`}>{selected.status}</span>
                </div>
                <div>
                  <p className="text-xs text-gray-500 font-medium uppercase mb-2">Items</p>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-700">
                        {['Item','Quantity','Unit'].map(h => <th key={h} className="text-left text-gray-500 px-2 py-1.5">{h}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {selected.items.map(i => (
                        <tr key={i.id} className="border-b border-gray-700/50">
                          <td className="px-2 py-2 text-gray-200">{i.item_name}</td>
                          <td className="px-2 py-2 text-gray-400">{i.quantity}</td>
                          <td className="px-2 py-2 text-gray-400">{i.unit}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="flex flex-wrap gap-2">
                  {selected.status === 'DRAFT' && hasPermission('inventory.transfer') && (
                    <button onClick={() => doAction('request', selected.id)} className="px-3 py-1.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg text-xs hover:bg-blue-500/30">Request</button>
                  )}
                  {selected.status === 'REQUESTED' && hasPermission('inventory.transfer.approve') && (
                    <button onClick={() => doAction('approve', selected.id)} className="px-3 py-1.5 bg-brand-500/20 text-brand-400 border border-brand-500/30 rounded-lg text-xs hover:bg-brand-500/30">Approve</button>
                  )}
                  {selected.status === 'APPROVED' && hasPermission('inventory.transfer.approve') && (
                    <button onClick={() => doAction('complete', selected.id)} className="px-3 py-1.5 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg text-xs hover:bg-green-500/30">Complete</button>
                  )}
                  {!['COMPLETED','CANCELLED'].includes(selected.status) && hasPermission('inventory.transfer') && (
                    <button onClick={() => doAction('cancel', selected.id)} className="px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-xs hover:bg-red-500/20">Cancel</button>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
