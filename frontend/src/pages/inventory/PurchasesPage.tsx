// =============================================================================
// RestaurantFlow — Purchase Orders Page
// Phase 10
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import {
  listPurchaseOrders, getPurchaseOrder, createPurchaseOrder,
  submitPurchaseOrder, approvePurchaseOrder, cancelPurchaseOrder, receivePurchaseOrder,
  listSuppliers, listInventoryItems, listStorageLocations,
} from '@/services/inventory'
import type {
  PurchaseOrder, PurchaseOrderSummary, Supplier,
  InventoryItem, StorageLocation, UnitOfMeasurement,
  CreatePurchaseOrderPayload, ReceivePurchaseOrderPayload,
} from '@/types'
import { useAuth } from '@/contexts/AuthContext'

const STATUS_BADGE: Record<string, string> = {
  DRAFT:              'bg-gray-700 text-gray-400 border-gray-600',
  SUBMITTED:          'bg-blue-500/10 text-blue-400 border-blue-500/20',
  APPROVED:           'bg-brand-500/10 text-brand-400 border-brand-500/20',
  PARTIALLY_RECEIVED: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  RECEIVED:           'bg-green-500/10 text-green-400 border-green-500/20',
  CANCELLED:          'bg-red-500/10 text-red-400 border-red-500/20',
}

const UNITS: UnitOfMeasurement[] = ['KG', 'GRAM', 'LITRE', 'MILLILITRE', 'PIECE', 'PACK', 'BOX', 'BOTTLE', 'DOZEN']

export function PurchasesPage() {
  const { user, hasPermission } = useAuth()
  const [orders, setOrders] = useState<PurchaseOrderSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState('')
  const [selected, setSelected] = useState<PurchaseOrder | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Create form state
  const [showCreate, setShowCreate] = useState(false)
  const [suppliers, setSuppliers] = useState<Supplier[]>([])
  const [invItems, setInvItems] = useState<InventoryItem[]>([])
  const [locations, setLocations] = useState<StorageLocation[]>([])
  const [createForm, setCreateForm] = useState<Partial<CreatePurchaseOrderPayload>>({ items: [] })
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Receive form state
  const [showReceive, setShowReceive] = useState(false)
  const [receiveForm, setReceiveForm] = useState<ReceivePurchaseOrderPayload>({ storage_location_id: '', items: [] })
  const [receiveError, setReceiveError] = useState<string | null>(null)
  const [receiveSaving, setReceiveSaving] = useState(false)

  const branchId = user?.scope?.roles?.[0]?.branch?.id ?? ''
  const restaurantId = user?.scope?.roles?.[0]?.restaurant?.id ?? ''

  const load = useCallback(() => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (filterStatus) params.status = filterStatus
    listPurchaseOrders(params)
      .then(r => setOrders(r.data))
      .catch(e => setError(e?.response?.data?.message ?? 'Failed to load purchases'))
      .finally(() => setLoading(false))
  }, [filterStatus])

  useEffect(() => { load() }, [load])

  const loadAuxData = useCallback(async () => {
    const params: Record<string, string> = {}
    if (restaurantId) params.restaurant = restaurantId
    const [sup, items, locs] = await Promise.all([
      listSuppliers(params),
      listInventoryItems(params),
      listStorageLocations(branchId ? { branch: branchId } : {}),
    ])
    setSuppliers(sup.data)
    setInvItems(items.data)
    setLocations(locs.data)
  }, [restaurantId, branchId])

  const openCreate = async () => {
    await loadAuxData()
    setCreateForm({ restaurant_id: restaurantId, branch_id: branchId, items: [{ inventory_item_id: '', quantity: '1', unit: 'KG', unit_cost: '0', tax_rate: '0', discount_amount: '0' }] })
    setShowCreate(true)
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setFormError(null)
    try {
      await createPurchaseOrder(createForm as CreatePurchaseOrderPayload)
      setShowCreate(false)
      load()
    } catch (e: any) {
      setFormError(e?.response?.data?.message ?? 'Failed to create purchase order')
    } finally { setSaving(false) }
  }

  const selectOrder = async (id: string) => {
    setLoadingDetail(true)
    try {
      const r = await getPurchaseOrder(id)
      setSelected(r.data)
    } catch { /* ignore */ }
    setLoadingDetail(false)
  }

  const doAction = async (action: 'submit' | 'approve' | 'cancel', id: string) => {
    try {
      if (action === 'submit') await submitPurchaseOrder(id)
      else if (action === 'approve') await approvePurchaseOrder(id)
      else if (action === 'cancel') await cancelPurchaseOrder(id, 'Cancelled via UI')
      load()
      if (selected?.id === id) selectOrder(id)
    } catch (e: any) {
      alert(e?.response?.data?.message ?? 'Action failed')
    }
  }

  const openReceive = async (po: PurchaseOrder) => {
    await loadAuxData()
    setReceiveForm({
      storage_location_id: locations[0]?.id ?? '',
      items: po.items
        .filter(i => parseFloat(i.remaining_quantity) > 0)
        .map(i => ({ purchase_order_item_id: i.id, quantity_received: i.remaining_quantity })),
    })
    setShowReceive(true)
  }

  const handleReceive = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected) return
    setReceiveSaving(true)
    setReceiveError(null)
    try {
      await receivePurchaseOrder(selected.id, receiveForm)
      setShowReceive(false)
      load()
      selectOrder(selected.id)
    } catch (e: any) {
      setReceiveError(e?.response?.data?.message ?? 'Receive failed')
    } finally { setReceiveSaving(false) }
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Purchase Orders</h1>
          <p className="text-sm text-gray-500 mt-0.5">{orders.length} orders</p>
        </div>
        {hasPermission('purchase.create') && (
          <button onClick={openCreate} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm hover:bg-brand-600 transition-colors">
            + New PO
          </button>
        )}
      </div>

      {/* Filters */}
      <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
        className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
        <option value="">All Statuses</option>
        {['DRAFT','SUBMITTED','APPROVED','PARTIALLY_RECEIVED','RECEIVED','CANCELLED'].map(s => (
          <option key={s} value={s}>{s.replace('_',' ')}</option>
        ))}
      </select>

      {error && <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 text-sm">{error}</div>}

      {/* Create Form */}
      {showCreate && (
        <form onSubmit={handleCreate} className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-white">New Purchase Order</h3>
          {formError && <p className="text-xs text-red-400">{formError}</p>}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Supplier *</label>
              <select required value={createForm.supplier_id ?? ''} onChange={e => setCreateForm(f => ({ ...f, supplier_id: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500">
                <option value="">Select supplier</option>
                {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Expected Date</label>
              <input type="date" value={createForm.expected_date ?? ''} onChange={e => setCreateForm(f => ({ ...f, expected_date: e.target.value }))}
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-brand-500" />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-gray-400 font-medium">Items</label>
              <button type="button" onClick={() => setCreateForm(f => ({ ...f, items: [...(f.items ?? []), { inventory_item_id: '', quantity: '1', unit: 'KG', unit_cost: '0', tax_rate: '0', discount_amount: '0' }] }))}
                className="text-xs text-brand-400 hover:text-brand-300">+ Add Row</button>
            </div>
            {(createForm.items ?? []).map((item, idx) => (
              <div key={idx} className="grid grid-cols-5 gap-2 mb-2">
                <select required value={item.inventory_item_id} onChange={e => setCreateForm(f => { const items = [...(f.items ?? [])]; items[idx] = { ...items[idx], inventory_item_id: e.target.value }; return { ...f, items } })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white col-span-2 focus:outline-none focus:border-brand-500">
                  <option value="">Item</option>
                  {invItems.map(i => <option key={i.id} value={i.id}>{i.name}</option>)}
                </select>
                <input type="number" step="0.001" min="0.001" required placeholder="Qty" value={item.quantity}
                  onChange={e => setCreateForm(f => { const items = [...(f.items ?? [])]; items[idx] = { ...items[idx], quantity: e.target.value }; return { ...f, items } })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500" />
                <input type="number" step="0.01" min="0" required placeholder="Unit Cost" value={item.unit_cost}
                  onChange={e => setCreateForm(f => { const items = [...(f.items ?? [])]; items[idx] = { ...items[idx], unit_cost: e.target.value }; return { ...f, items } })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500" />
                <select value={item.unit} onChange={e => setCreateForm(f => { const items = [...(f.items ?? [])]; items[idx] = { ...items[idx], unit: e.target.value as UnitOfMeasurement }; return { ...f, items } })}
                  className="bg-gray-900 border border-gray-700 rounded-lg px-2 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500">
                  {UNITS.map(u => <option key={u}>{u}</option>)}
                </select>
              </div>
            ))}
          </div>

          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="px-4 py-2 bg-brand-500 text-white rounded-lg text-sm disabled:opacity-50 hover:bg-brand-600">
              {saving ? 'Creating…' : 'Create PO'}
            </button>
            <button type="button" onClick={() => setShowCreate(false)} className="px-4 py-2 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600">Cancel</button>
          </div>
        </form>
      )}

      {/* Table */}
      {loading ? (
        <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-12 bg-gray-800 rounded-lg animate-pulse" />)}</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
          {/* List */}
          <div className="lg:col-span-2 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-800">
                  {['PO #', 'Supplier', 'Status', 'Total'].map(h => (
                    <th key={h} className="text-left text-xs text-gray-500 font-medium px-3 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orders.map(o => (
                  <tr key={o.id} onClick={() => selectOrder(o.id)}
                    className={`border-b border-gray-800/50 cursor-pointer transition-colors ${selected?.id === o.id ? 'bg-gray-800' : 'hover:bg-gray-800/30'}`}>
                    <td className="px-3 py-3 text-brand-400 font-mono text-xs">{o.purchase_number}</td>
                    <td className="px-3 py-3 text-gray-200">{o.supplier_name}</td>
                    <td className="px-3 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_BADGE[o.status]}`}>
                        {o.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-3 py-3 text-gray-300">₹{o.total_amount}</td>
                  </tr>
                ))}
                {orders.length === 0 && (
                  <tr><td colSpan={4} className="px-3 py-8 text-center text-gray-600 text-sm">No purchase orders found.</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Detail panel */}
          <div className="lg:col-span-3">
            {loadingDetail && <div className="h-40 bg-gray-800 rounded-xl animate-pulse" />}
            {selected && !loadingDetail && (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-mono text-brand-400">{selected.purchase_number}</p>
                    <p className="text-lg font-semibold text-white mt-0.5">{selected.supplier_name}</p>
                    <span className={`text-xs px-2 py-0.5 rounded-full border ${STATUS_BADGE[selected.status]}`}>
                      {selected.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">Total</p>
                    <p className="text-xl font-bold text-white">₹{selected.total_amount}</p>
                  </div>
                </div>

                {/* Items */}
                <div>
                  <p className="text-xs text-gray-500 font-medium uppercase mb-2">Items</p>
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-gray-700">
                        {['Item','Ordered','Received','Remaining','Unit Cost'].map(h => (
                          <th key={h} className="text-left text-gray-500 font-medium px-2 py-1.5">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {selected.items.map(i => (
                        <tr key={i.id} className="border-b border-gray-700/50">
                          <td className="px-2 py-2 text-gray-200">{i.item_name}</td>
                          <td className="px-2 py-2 text-gray-400">{i.quantity} {i.unit}</td>
                          <td className="px-2 py-2 text-gray-400">{i.received_quantity}</td>
                          <td className="px-2 py-2 text-gray-400">{i.remaining_quantity}</td>
                          <td className="px-2 py-2 text-gray-300">₹{i.unit_cost}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Actions */}
                <div className="flex flex-wrap gap-2 pt-1">
                  {selected.status === 'DRAFT' && hasPermission('purchase.submit') && (
                    <button onClick={() => doAction('submit', selected.id)} className="px-3 py-1.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded-lg text-xs hover:bg-blue-500/30">
                      Submit
                    </button>
                  )}
                  {selected.status === 'SUBMITTED' && hasPermission('purchase.approve') && (
                    <button onClick={() => doAction('approve', selected.id)} className="px-3 py-1.5 bg-brand-500/20 text-brand-400 border border-brand-500/30 rounded-lg text-xs hover:bg-brand-500/30">
                      Approve
                    </button>
                  )}
                  {['APPROVED','PARTIALLY_RECEIVED'].includes(selected.status) && hasPermission('purchase.receive') && (
                    <button onClick={() => openReceive(selected)} className="px-3 py-1.5 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg text-xs hover:bg-green-500/30">
                      Receive Stock
                    </button>
                  )}
                  {!['RECEIVED','CANCELLED'].includes(selected.status) && hasPermission('purchase.cancel') && (
                    <button onClick={() => doAction('cancel', selected.id)} className="px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-xs hover:bg-red-500/20">
                      Cancel
                    </button>
                  )}
                </div>

                {/* Receive stock panel */}
                {showReceive && (
                  <form onSubmit={handleReceive} className="border border-gray-700 rounded-lg p-4 space-y-3 bg-gray-900">
                    <p className="text-xs font-semibold text-white">Receive Stock</p>
                    {receiveError && <p className="text-xs text-red-400">{receiveError}</p>}
                    <div>
                      <label className="block text-xs text-gray-400 mb-1">Storage Location *</label>
                      <select required value={receiveForm.storage_location_id}
                        onChange={e => setReceiveForm(f => ({ ...f, storage_location_id: e.target.value }))}
                        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-brand-500">
                        <option value="">Select location</option>
                        {locations.map(l => <option key={l.id} value={l.id}>{l.name} [{l.code}]</option>)}
                      </select>
                    </div>
                    {receiveForm.items.map((ri, idx) => {
                      const poItem = selected.items.find(i => i.id === ri.purchase_order_item_id)
                      return (
                        <div key={idx} className="flex items-center gap-2">
                          <span className="text-xs text-gray-400 flex-1">{poItem?.item_name}</span>
                          <input type="number" step="0.001" min="0.001" max={poItem?.remaining_quantity}
                            value={ri.quantity_received}
                            onChange={e => setReceiveForm(f => { const items = [...f.items]; items[idx] = { ...items[idx], quantity_received: e.target.value }; return { ...f, items } })}
                            className="w-24 bg-gray-800 border border-gray-700 rounded-lg px-2 py-1 text-xs text-white focus:outline-none focus:border-brand-500" />
                          <span className="text-xs text-gray-500">{poItem?.unit}</span>
                        </div>
                      )
                    })}
                    <div className="flex gap-2">
                      <button type="submit" disabled={receiveSaving} className="px-3 py-1.5 bg-green-500/20 text-green-400 border border-green-500/30 rounded-lg text-xs disabled:opacity-50 hover:bg-green-500/30">
                        {receiveSaving ? 'Saving…' : 'Confirm Receipt'}
                      </button>
                      <button type="button" onClick={() => setShowReceive(false)} className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-xs">Cancel</button>
                    </div>
                  </form>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
